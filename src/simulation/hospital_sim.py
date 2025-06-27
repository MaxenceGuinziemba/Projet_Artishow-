"""
Hospital simulation core module.

This module provides the main HospitalSim class that handles the simulation logic.
"""

import simpy
import sqlite3
import json
import random
import numpy as np
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from src.config import (
    SIM_START_DATE, DISEASES, DISEASE_WEIGHTS, SPECIALTIES,
    SPECIALTY_PROPORTIONS, SPECIAL_DATES, DB_PATH,
    HOUR_FACTORS, DAY_FACTORS, MONTH_FACTORS,
    DEFAULT_NUM_DOCTORS, DEFAULT_ARRIVAL_RATE
)
from src.simulation.models import Doctor, Patient

class HospitalSim:
    """Hospital simulation model with various specialties and diseases.

    This class handles the main simulation logic including patient arrivals,
    doctor assignments, treatment, and data collection.

    Attributes:
        env (simpy.Environment): SimPy simulation environment
        num_doctors (int): Total number of doctors in the simulation
        arrival_rate (float): Avg number of patient arrivals per hour
        db_path (str): Path to SQLite database file
        resume (bool): Whether to resume from saved state
        patients_total (int): Total patients generated
        patients_treated (int): Total patients treated
        start_date (datetime): Simulation start date
        doctors (List[Doctor]): List of doctors in the hospital
        active_events (Dict[str, Dict]): Dictionary of active special events affecting the simulation
        parameter_changes (List[Dict]): List of parameter changes that occurred during simulation
    """

    def __init__(self, env: simpy.Environment, num_doctors: int = DEFAULT_NUM_DOCTORS,
                 arrival_rate: float = DEFAULT_ARRIVAL_RATE, db_path: str = DB_PATH,
                 resume: bool = False, resume_sim_id: Optional[int] = None):
        """Initialize the hospital simulation.

        Args:
            env: SimPy environment
            num_doctors: Number of doctors in the hospital
            arrival_rate: Average patient arrivals per hour
            db_path: Path to SQLite database
            resume: Whether to resume from a previously saved state
            resume_sim_id: Specific simulation ID to resume (if None, uses latest)
        """
        self.env = env
        self.num_doctors = num_doctors
        self.arrival_rate = arrival_rate
        self.db_path = db_path
        self.resume = resume

        print(f"HospitalSim initializing with {num_doctors} doctors, {arrival_rate}/hr arrival rate")

        # Apply performance optimizations for Linux
        if os.name == 'posix':  # Linux/Unix systems
            os.environ['PYTHONUNBUFFERED'] = '1'
            from src.data.db import optimize_database_performance
            optimize_database_performance()

        # Performance optimization - reduce logging frequency
        self.log_interval = 1  # Log every minute for granular data
        self.batch_size = 50  # Batch database operations

        # Default start values
        self.patients_total = 0
        self.patients_treated = 0
        self.start_date = SIM_START_DATE

        # Initialize events and parameter changes tracking
        self.active_events = {}
        self.parameter_changes = []

        # Create or get simulation ID
        from src.data.db import create_new_simulation, get_latest_simulation_id, get_simulation_by_id
        if resume:
            # Get the specified simulation ID or the latest one if resuming
            if resume_sim_id is not None:
                # Check if the specified simulation exists
                sim_info = get_simulation_by_id(resume_sim_id)
                if sim_info is not None:
                    self.sim_id = resume_sim_id
                    # Load immutable parameters from database
                    self.num_doctors = sim_info.get('num_doctors')
                    self.arrival_rate = sim_info.get('arrival_rate')
                    print(f"Resuming simulation {resume_sim_id} with database parameters:")
                    print(f"  {self.num_doctors} doctors, {self.arrival_rate}/hr arrival rate")
                    if num_doctors != self.num_doctors or abs(arrival_rate - self.arrival_rate) > 0.01:
                        print(f"  Command line parameters ignored (immutable per simulation)")
                else:
                    print(f"Simulation {resume_sim_id} not found. Starting a new simulation.")
                    self.sim_id = create_new_simulation(num_doctors, arrival_rate, f"New simulation (failed to resume {resume_sim_id})")
                    self.resume = False
            else:
                # Get the latest simulation ID if no specific ID provided
                latest_sim_id = get_latest_simulation_id()
                if latest_sim_id is not None:
                    sim_info = get_simulation_by_id(latest_sim_id)
                    self.sim_id = latest_sim_id
                    # Load immutable parameters from database
                    self.num_doctors = sim_info.get('num_doctors')
                    self.arrival_rate = sim_info.get('arrival_rate')
                    print(f"Resuming latest simulation {latest_sim_id} with database parameters:")
                    print(f"  {self.num_doctors} doctors, {self.arrival_rate}/hr arrival rate")
                    if num_doctors != self.num_doctors or abs(arrival_rate - self.arrival_rate) > 0.01:
                        print(f"  Command line parameters ignored (immutable per simulation)")
                else:
                    print("No previous simulation found. Starting a new simulation.")
                    self.sim_id = create_new_simulation(num_doctors, arrival_rate, "New simulation (no previous found)")
                    self.resume = False
        else:
            # Create a new simulation record
            self.sim_id = create_new_simulation(num_doctors, arrival_rate, "New simulation")

        # If resuming, try to load state
        if self.resume:
            success = self._load_simulation_state()
            if not success:
                print("Failed to load simulation state. Starting fresh with same ID.")
                self.resume = False

        # Initialize doctors (will use loaded state if resuming)
        self.doctors = self._init_doctors()

        # Final verification
        print(f"✓ HospitalSim ready: {len(self.doctors)} doctors initialized for simulation {self.sim_id}")

    def _load_simulation_state(self) -> bool:
        """Load the previous simulation state from the database.

        Returns:
            bool: True if state was successfully loaded, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Use dictionary-like rows
            cursor = conn.cursor()

            # Get the latest simulation state for this simulation ID
            state = cursor.execute(
                'SELECT * FROM sim_metadata WHERE sim_id = ? ORDER BY id DESC LIMIT 1',
                (self.sim_id,)
            ).fetchone()

            if state:
                # Extract and set basic properties
                self.start_date = datetime.fromisoformat(state['start_date'])
                last_sim_time = float(state['last_sim_time'])
                self.patients_total = int(state['patients_total'])
                self.patients_treated = int(state['patients_treated'])

                # Restore doctor state (will be used in _init_doctors)
                self.doctor_state = json.loads(state['active_doctors'])

                # Load active events that are still valid
                self._load_active_events(last_sim_time)

                # Set the environment's now time to continue from where we left off
                # We need to advance the environment time to the saved point
                if last_sim_time > 0:
                    # Directly set the environment's internal time
                    self.env._now = int(last_sim_time)

                print(f"Resumed simulation {self.sim_id} from {self.start_date.isoformat()}, time: {int(last_sim_time)} minutes")
                print(f"State: {self.patients_total} total patients, {self.patients_treated} treated")

                conn.close()
                return True
            else:
                print(f"No previous simulation state found for simulation ID {self.sim_id}. Starting fresh.")
                conn.close()
                return False
        except Exception as e:
            print(f"Error loading simulation state: {e}")
            return False

    def _set_env_time(self, target_time: float):
        """Helper process to advance the environment time to the saved point.

        Args:
            target_time: Target simulation time in minutes

        Yields:
            simpy.Timeout: SimPy timeout event to advance simulation time
        """
        yield self.env.timeout(target_time)

    def _load_active_events(self, current_sim_time: float) -> None:
        """Load active events from the database that are still valid.

        Args:
            current_sim_time: Current simulation time in minutes
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get all events for this simulation that haven't expired yet
            events = cursor.execute('''
                SELECT * FROM simulation_events
                WHERE sim_id = ? AND end_sim_minutes > ?
                ORDER BY start_sim_minutes
            ''', (self.sim_id, current_sim_time)).fetchall()

            for event_row in events:
                event_id = event_row['event_id']
                self.active_events[event_id] = {
                    'type': event_row['event_type'],
                    'params': json.loads(event_row['params']),
                    'start_time': event_row['start_sim_minutes'],
                    'expiration_time': event_row['end_sim_minutes'],
                    'start_date': event_row['start_time'],
                    'end_date': event_row['end_time']
                }
                print(f"Restored active event: {event_id} of type {event_row['event_type']}")

            conn.close()
        except Exception as e:
            print(f"Error loading active events: {e}")

    def _init_doctors(self) -> List[Doctor]:
        """Initialize doctors, potentially using loaded state.

        Returns:
            List[Doctor]: List of initialized doctors
        """
        doctors = []
        id_counter = 1

        # If we have a saved doctor state and we're resuming, use it
        if hasattr(self, 'doctor_state') and self.resume:
            for doc_data in self.doctor_state:
                doctor = Doctor(doc_data['id'], doc_data['specialty'], self.env)
                doctor.patients_treated = doc_data['patients_treated']
                doctors.append(doctor)
                id_counter = max(id_counter, doc_data['id'] + 1)
        else:
            # Regular initialization - ensure we get exactly num_doctors
            print(f"Initializing exactly {self.num_doctors} doctors...")

            # Calculate specialty distribution more precisely
            spec_counts = {}
            total_proportion = sum(SPECIALTY_PROPORTIONS.values())

            # First pass: distribute based on proportions
            for spec in SPECIALTIES:
                proportion = SPECIALTY_PROPORTIONS[spec] / total_proportion
                spec_counts[spec] = int(self.num_doctors * proportion)

            # Second pass: handle rounding to ensure exact total
            assigned_total = sum(spec_counts.values())
            remaining = self.num_doctors - assigned_total

            # Add remaining doctors to specialties with highest fractional parts
            if remaining > 0:
                # Calculate fractional parts for each specialty
                fractional_parts = []
                for spec in SPECIALTIES:
                    proportion = SPECIALTY_PROPORTIONS[spec] / total_proportion
                    expected = self.num_doctors * proportion
                    fractional = expected - int(expected)
                    fractional_parts.append((fractional, spec))

                # Sort by fractional part (highest first) and add doctors
                fractional_parts.sort(reverse=True)
                for i in range(remaining):
                    spec = fractional_parts[i % len(fractional_parts)][1]
                    spec_counts[spec] += 1

            # Third pass: remove excess if we somehow went over
            assigned_total = sum(spec_counts.values())
            if assigned_total > self.num_doctors:
                excess = assigned_total - self.num_doctors
                # Remove from least critical specialties first
                removal_order = ["pulmonologist", "neurologist", "gynecologist", "cardiologist", "emergency", "generalist"]
                for spec in removal_order:
                    if excess > 0 and spec_counts.get(spec, 0) > 1:
                        reduction = min(excess, spec_counts[spec] - 1)
                        spec_counts[spec] -= reduction
                        excess -= reduction

            # Create doctors according to calculated counts
            for spec, count in spec_counts.items():
                for _ in range(count):
                    doctors.append(Doctor(id_counter, spec, self.env))
                    id_counter += 1

            print(f"Created exactly {len(doctors)} doctors with distribution: {spec_counts}")

            # Final verification
            if len(doctors) != self.num_doctors:
                print(f"ERROR: Expected {self.num_doctors} doctors, but created {len(doctors)}")
                # Force correct the count as a fallback
                while len(doctors) < self.num_doctors:
                    doctors.append(Doctor(id_counter, "generalist", self.env))
                    id_counter += 1
                while len(doctors) > self.num_doctors:
                    doctors.pop()
                print(f"Corrected to {len(doctors)} doctors")

        return doctors

    def get_seasonal_weights(self, sim_time: float) -> List[int]:
        """Calculate disease weights based on seasonal patterns.

        Modifies the base disease weights according to the current month to simulate
        seasonal variations in disease prevalence.

        Args:
            sim_time: Current simulation time in minutes

        Returns:
            List of weights for disease selection, higher values = higher probability
        """
        # Calculate current date from simulation time
        current_date = self.start_date + timedelta(minutes=sim_time)
        month = current_date.month - 1  # 0-based index

        # Base weights
        weights = DISEASE_WEIGHTS.copy()

        # Winter (Dec, Jan, Feb): more viral_infection, less asthma
        if month in [11, 0, 1]:
            weights[0] = int(DISEASE_WEIGHTS[0] * 1.7)  # viral_infection
            weights[3] = int(DISEASE_WEIGHTS[3] * 0.5)  # asthma_attack
        # Spring (Mar, Apr, May): more asthma, less viral
        elif month in [2, 3, 4]:
            weights[3] = int(DISEASE_WEIGHTS[3] * 2.0)  # asthma_attack
            weights[0] = int(DISEASE_WEIGHTS[0] * 0.7)  # viral_infection
        # Summer (Jun, Jul, Aug): more fractures, less viral
        elif month in [5, 6, 7]:
            weights[1] = int(DISEASE_WEIGHTS[1] * 1.5)  # minor_fracture
            weights[0] = int(DISEASE_WEIGHTS[0] * 0.5)  # viral_infection
        # Autumn (Sep, Oct, Nov): more gastroenteritis
        elif month in [8, 9, 10]:
            weights[8] = int(DISEASE_WEIGHTS[8] * 2.0)  # gastroenteritis

        # Apply the month factor to adjust overall disease probability
        month_factor = MONTH_FACTORS[month]
        if month_factor != 1.0:
            weights = [int(w * month_factor) for w in weights]

        # Normalize to avoid all zeros
        if sum(weights) == 0:
            weights = DISEASE_WEIGHTS.copy()

        return weights

    def get_time_of_day_factor(self, sim_time: float) -> float:
        """Returns a multiplier for patient arrival rate based on time of day.

        Provides hourly adjustment factors that make the simulation more realistic
        by having lower patient volumes at night and higher volumes during peak hours.

        Args:
            sim_time: Simulation time in minutes

        Returns:
            float: Multiplier for the base arrival rate
        """
        # Convert sim_time to hour of day (0-23)
        minutes_in_day = 24 * 60
        day_minute = sim_time % minutes_in_day
        hour = int(day_minute // 60)

        # Use the hour factors from config
        return HOUR_FACTORS[hour]

    def run(self, sim_minutes: int = 525600, additional_minutes: Optional[int] = None) -> None:
        """Run the hospital simulation for the specified duration.

        Args:
            sim_minutes: Total duration for new simulations or default target (1 year = 525600 minutes)
            additional_minutes: Additional minutes to run from current position (for resumed simulations)
        """
        # Calculate the target time based on whether we're resuming or starting fresh
        if self.resume and additional_minutes is not None:
            # When resuming with --minutes specified: add those minutes to current time
            target_time = self.env.now + additional_minutes
            print(f"Resuming simulation {self.sim_id}: running {additional_minutes} additional minutes")
            print(f"Current time: {int(self.env.now)} minutes -> Target: {int(target_time)} minutes")
        elif self.resume:
            # When resuming without --minutes: continue until 1 year total
            target_time = 525600  # 1 year default
            remaining_time = max(0, target_time - self.env.now)
            print(f"Resuming simulation {self.sim_id}: running until 1 year mark")
            print(f"Current time: {int(self.env.now)} minutes -> Target: {int(target_time)} minutes")
            print(f"Remaining time to simulate: {int(remaining_time)} minutes")

            if remaining_time <= 0:
                print("Simulation has already reached or exceeded 1 year. No additional time to simulate.")
                return
        else:
            # New simulation: run for the specified duration
            target_time = sim_minutes
            print(f"Starting new simulation {self.sim_id}: running for {sim_minutes} minutes")

        self.env.process(self.patient_arrivals())
        self.env.process(self.data_collector())
        self.env.run(until=int(target_time))

    def patient_arrivals(self):
        """Generate patient arrivals and assign them to appropriate doctors.

        This process runs continuously, generating patients according to
        time-of-day patterns, weekday/weekend patterns, and seasonal variations.

        Yields:
            simpy.Timeout: Time until next patient arrival
        """
        while True:
            # Apply time-of-day factor from config
            time_factor = self.get_time_of_day_factor(self.env.now)

            # Apply day-of-week factor from config (0=Monday, 6=Sunday)
            day_of_week = int((self.env.now // (24 * 60)) % 7)
            day_factor = DAY_FACTORS[day_of_week]

            # Apply month factor from config (1=January, 12=December)
            current_date = self.start_date + timedelta(minutes=self.env.now)
            month_factor = MONTH_FACTORS[current_date.month - 1]  # Adjust for 0-based index

            # Check for special dates
            special_factor = 1.0
            for special_date in SPECIAL_DATES:
                if current_date.month == special_date["month"] and current_date.day == special_date["day"]:
                    special_factor = special_date["factor"]
                    break

            # Check and apply effects from active events (epidemics, disasters, etc.)
            event_factors = self.check_and_apply_events()
            event_arrival_factor = event_factors['arrival_rate']

            # Calculate effective arrival rate with all factors
            effective_rate = self.arrival_rate * time_factor * day_factor * month_factor * special_factor * event_arrival_factor

            # Hospital might be on diversion if extremely busy (over 90% capacity)
            busy_doctors = sum(1 for d in self.doctors if d.resource.count > 0)
            busy_factor = 1.0
            if busy_doctors > 0.9 * len(self.doctors):
                busy_factor = 0.7  # Reduced arrivals during high occupancy

            # Adjust arrival time based on all factors
            adjusted_rate = max(1, effective_rate * busy_factor)  # Ensure at least 1/hour
            interarrival = np.random.exponential(60 / adjusted_rate)

            yield self.env.timeout(interarrival)

            # Get seasonal disease distribution
            seasonal_weights = self.get_seasonal_weights(self.env.now)

            # Apply event-specific disease weight modifications
            event_disease_weights = event_factors['disease_weights']
            if event_disease_weights:
                # Make a copy of the weights to modify
                modified_weights = seasonal_weights.copy()

                # Apply multipliers for specific diseases
                for i, disease_info in enumerate(DISEASES):
                    disease_name = disease_info[0]
                    if disease_name in event_disease_weights:
                        modified_weights[i] = int(modified_weights[i] * event_disease_weights[disease_name])

                # Use the modified weights
                seasonal_weights = modified_weights

            disease, mean_time, specialty = random.choices(DISEASES, weights=seasonal_weights, k=1)[0]

            # Modify treatment time based on events (e.g., more complex cases during epidemics)
            treatment_time_factor = event_factors.get('treatment_time', 1.0)
            treatment_time = max(1, int(np.random.exponential(mean_time * treatment_time_factor)))

            patient = Patient(
                id=f"P{self.patients_total}",
                disease=disease,
                treatment_time=treatment_time,
                specialty=specialty,
                arrival_time=self.env.now,
            )
            self.patients_total += 1
            self.env.process(self.handle_patient(patient))

    def handle_patient(self, patient: Patient):
        """Process a patient through the hospital system.

        This includes finding an appropriate doctor, waiting in queue if needed,
        treatment, and recording the outcome.

        Args:
            patient: Patient object to be treated

        Yields:
            simpy.events: SimPy event sequence for patient handling
        """
        # Log patient arrival
        self.log_detailed_event("patient_arrival", patient.id, None, {
            "disease": patient.disease,
            "specialty_required": patient.specialty,
            "treatment_time": patient.treatment_time
        })

        # Find available doctor of required specialty
        candidates = [d for d in self.doctors if d.specialty == patient.specialty]
        if not candidates:
            candidates = [d for d in self.doctors if d.specialty == "generalist"]
        # Prefer free doctor, else shortest queue
        free_doctors = [d for d in candidates if d.resource.count == 0]
        if free_doctors:
            doctor = random.choice(free_doctors)
        else:
            doctor = min(candidates, key=lambda d: len(d.queue))

        # Log doctor assignment
        self.log_detailed_event("doctor_assigned", patient.id, doctor.id, {
            "doctor_specialty": doctor.specialty,
            "queue_length": len(doctor.queue)
        })

        doctor.queue.append(patient)
        with doctor.resource.request() as req:
            yield req
            doctor.queue.remove(patient)
            patient.start_treatment = self.env.now

            # Log treatment start
            self.log_detailed_event("treatment_start", patient.id, doctor.id, {
                "wait_time": patient.start_treatment - patient.arrival_time
            })

            yield self.env.timeout(patient.treatment_time)
            patient.end_treatment = self.env.now
            doctor.patients_treated += 1
            self.patients_treated += 1

            # Log treatment end
            self.log_detailed_event("treatment_end", patient.id, doctor.id, {
                "treatment_duration": patient.treatment_time,
                "total_time": patient.end_treatment - patient.arrival_time
            })

            self.save_patient_event(patient, doctor)

    def data_collector(self):
        """Periodically save simulation state and hospital metrics every minute.

        This process runs every minute in simulation time to provide granular data
        for minute-level analytics, updating the database with current hospital status.

        Yields:
            simpy.Timeout: One minute timeout between data collection points
        """
        while True:
            self.save_hospital_state()

            # Save simulation state every 24 hours for resuming capability
            if int(self.env.now) % (24 * 60) == 0 and self.env.now > 0:
                self.save_simulation_state()

            # Log every minute for granular analytics data
            yield self.env.timeout(self.log_interval)

    def save_patient_event(self, patient: Patient, doctor: Doctor) -> None:
        """Save a patient treatment event to the database.

        Args:
            patient: Patient object that was treated
            doctor: Doctor object that performed the treatment
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Convert simulation minutes to actual dates
            arrival_date = self.start_date + timedelta(minutes=patient.arrival_time)
            start_treatment_date = self.start_date + timedelta(minutes=patient.start_treatment)
            end_treatment_date = self.start_date + timedelta(minutes=patient.end_treatment)

            cursor.execute('''
            INSERT INTO patient_treated
            (sim_id, doctor_id, doctor_specialty, disease, treatment_time, wait_time,
            arrival_time, start_treatment, end_treatment, sim_minutes, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.sim_id,
                doctor.id,
                doctor.specialty,
                patient.disease,
                patient.treatment_time,
                patient.start_treatment - patient.arrival_time,
                arrival_date.isoformat(),
                start_treatment_date.isoformat(),
                end_treatment_date.isoformat(),
                int(patient.end_treatment),  # Store original sim minutes too
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving patient data: {e}")

    def save_hospital_state(self) -> None:
        """Save the current hospital state to the database.

        Records metrics including patient counts, busy doctors, and waiting patients.
        Also stores the current simulation date and time.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            busy_doctors = sum(1 for d in self.doctors if d.resource.count > 0)
            waiting_patients = sum(len(d.queue) for d in self.doctors)

            # Convert simulation time to actual date
            current_sim_date = self.start_date + timedelta(minutes=self.env.now)

            cursor.execute('''
            INSERT INTO hospital_state
            (sim_id, patients_total, patients_treated, busy_doctors, waiting_patients, sim_time, sim_minutes, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.sim_id,
                self.patients_total,
                self.patients_treated,
                busy_doctors,
                waiting_patients,
                current_sim_date.isoformat(),
                float(self.env.now),  # Store as float to preserve decimal precision
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving hospital state: {e}")

    def save_simulation_state(self) -> None:
        """Save the current simulation state for later resuming.

        Stores essential information about the simulation including all doctor states,
        patient counts, and timing information to allow resuming the simulation later.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Prepare serialized doctor state
            doctor_state = []
            for doctor in self.doctors:
                doctor_state.append({
                    'id': doctor.id,
                    'specialty': doctor.specialty,
                    'patients_treated': doctor.patients_treated,
                    'queue_length': len(doctor.queue),
                    'is_busy': doctor.resource.count > 0
                })

            # Save current state for this simulation ID
            cursor.execute('''
            INSERT INTO sim_metadata
            (sim_id, start_date, last_sim_time, patients_total, patients_treated, active_doctors, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.sim_id,
                self.start_date.isoformat(),
                int(self.env.now),
                self.patients_total,
                self.patients_treated,
                json.dumps(doctor_state),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            print(f"Simulation state saved at minute {self.env.now}")
        except Exception as e:
            print(f"Error saving simulation state: {e}")

    def add_event(self, event_type: str, params: Dict[str, Any], duration_minutes: int = 1440) -> bool:
        """Add a special event to the simulation (e.g., epidemic, disaster).

        Args:
            event_type: Type of event (e.g., 'epidemic', 'disaster', 'weather')
            params: Parameters specific to the event type
            duration_minutes: How long the event should last, in simulation minutes

        Returns:
            bool: True if the event was successfully added
        """
        try:
            event_id = f"{event_type}_{len(self.active_events) + 1}"

            # Set expiration time
            expiration_time = self.env.now + duration_minutes

            # Store event details
            self.active_events[event_id] = {
                'type': event_type,
                'params': params,
                'start_time': self.env.now,
                'expiration_time': expiration_time,
                'start_date': (self.start_date + timedelta(minutes=self.env.now)).isoformat(),
                'end_date': (self.start_date + timedelta(minutes=expiration_time)).isoformat()
            }

            # Log the event to database
            self._log_event(event_id, event_type, params, duration_minutes)

            print(f"Event {event_id} of type {event_type} added, duration: {duration_minutes} minutes")
            return True
        except Exception as e:
            print(f"Error adding event: {e}")
            return False

    def update_parameters(self, params: Dict[str, Any]) -> bool:
        """Update simulation parameters during the run.

        Args:
            params: Dictionary of parameters to update
                - 'arrival_rate': New patient arrival rate (only for new simulations)
                - 'disease_factor': Dictionary mapping disease names to multipliers

        Note: num_doctors and arrival_rate are immutable once a simulation is created

        Returns:
            bool: True if parameters were successfully updated
        """
        try:
            # Record the change
            change = {
                'timestamp': self.env.now,
                'sim_date': (self.start_date + timedelta(minutes=self.env.now)).isoformat(),
                'old_values': {},
                'new_values': {}
            }

            # Check for immutable parameters
            if 'arrival_rate' in params:
                print(f"WARNING: arrival_rate is immutable per simulation. Ignoring update.")

            if 'num_doctors' in params:
                print(f"WARNING: num_doctors is immutable per simulation. Ignoring update.")

            # Only allow non-structural parameter changes
            valid_updates = False
            if 'disease_factor' in params:
                change['old_values']['disease_factor'] = {}  # Could track current factors
                change['new_values']['disease_factor'] = params['disease_factor']
                valid_updates = True

            if not valid_updates:
                print("No valid parameter updates provided.")
                return False

            # Store the parameter change
            self.parameter_changes.append(change)

            # Log the parameter change to database
            self._log_parameter_change(change)

            print(f"Parameters updated at time {self.env.now}: {params}")
            return True
        except Exception as e:
            print(f"Error updating parameters: {e}")
            return False


    def _log_event(self, event_id: str, event_type: str, params: Dict[str, Any], duration_minutes: int) -> None:
        """Log an event to the database.

        Args:
            event_id: Unique identifier for the event
            event_type: Type of event
            params: Event parameters
            duration_minutes: Duration of the event in minutes
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Convert simulation time to actual date
            current_sim_date = self.start_date + timedelta(minutes=self.env.now)
            end_sim_date = current_sim_date + timedelta(minutes=duration_minutes)

            cursor.execute('''
            INSERT INTO simulation_events
            (sim_id, event_id, event_type, params, start_time, end_time, start_sim_minutes, end_sim_minutes, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.sim_id,
                event_id,
                event_type,
                json.dumps(params),
                current_sim_date.isoformat(),
                end_sim_date.isoformat(),
                int(self.env.now),
                int(self.env.now + duration_minutes),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error logging event: {e}")

    def _log_parameter_change(self, change: Dict[str, Any]) -> None:
        """Log a parameter change to the database.

        Args:
            change: Dictionary with change details
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
            INSERT INTO parameter_changes
            (sim_id, sim_time, sim_minutes, old_values, new_values, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                self.sim_id,
                change['sim_date'],
                change['timestamp'],
                json.dumps(change['old_values']),
                json.dumps(change['new_values']),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error logging parameter change: {e}")

    def check_and_apply_events(self) -> None:
        """Check for active events and apply their effects.

        This method is called during patient arrivals to modify
        parameters based on active events.

        Returns:
            Dict[str, float]: Factors to apply to the simulation
        """
        # Initialize default factors
        factors = {
            'arrival_rate': 1.0,
            'disease_weights': {},
            'treatment_time': 1.0
        }

        # Check for expired events
        expired_events = []
        for event_id, event in self.active_events.items():
            if self.env.now >= event['expiration_time']:
                expired_events.append(event_id)
                print(f"Event {event_id} of type {event['type']} has expired")

        # Remove expired events
        for event_id in expired_events:
            del self.active_events[event_id]

        # Apply effects of active events
        for event_id, event in self.active_events.items():
            if event['type'] == 'epidemic':
                # Epidemic increases arrivals and specific disease prevalence
                factors['arrival_rate'] *= event['params'].get('arrival_factor', 1.5)

                # Increase specific disease weights
                target_disease = event['params'].get('disease', 'viral_infection')
                factors['disease_weights'][target_disease] = event['params'].get('disease_factor', 3.0)

                # Potentially increase treatment time
                factors['treatment_time'] *= event['params'].get('treatment_time_factor', 1.2)

            elif event['type'] == 'disaster':
                # Disaster causes a spike in emergency cases
                factors['arrival_rate'] *= event['params'].get('arrival_factor', 2.0)

                # Increase trauma cases
                factors['disease_weights']['minor_fracture'] = event['params'].get('fracture_factor', 4.0)
                factors['disease_weights']['major_trauma'] = event['params'].get('trauma_factor', 5.0)

            elif event['type'] == 'weather':
                # Weather affects specific conditions
                weather_type = event['params'].get('weather_type', 'storm')

                if weather_type == 'cold':
                    factors['disease_weights']['viral_infection'] = 2.0
                    factors['disease_weights']['pneumonia'] = 1.8
                elif weather_type == 'heat':
                    factors['disease_weights']['dehydration'] = 2.5
                    factors['arrival_rate'] *= 1.2
                elif weather_type == 'storm':
                    factors['arrival_rate'] *= 0.8  # Fewer people come to hospital during storms

        return factors

    def log_detailed_event(self, event_type: str, patient_id: str, doctor_id: Optional[int], details: Dict[str, Any]) -> None:
        """Log a detailed simulation event to the database.

        Args:
            event_type: Type of event (e.g., 'patient_arrival', 'doctor_assigned', 'treatment_start')
            patient_id: ID of the patient involved
            doctor_id: ID of the doctor involved (if any)
            details: Additional event details as a dictionary
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Convert simulation time to actual date
            current_sim_date = self.start_date + timedelta(minutes=self.env.now)

            cursor.execute('''
            INSERT INTO detailed_events
            (sim_id, event_type, patient_id, doctor_id, event_time, sim_minutes, details, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.sim_id,
                event_type,
                patient_id,
                doctor_id,
                current_sim_date.isoformat(),
                self.env.now,
                json.dumps(details),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error logging detailed event: {e}")
