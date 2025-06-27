# filepath: /Users/arsnm/Programming/repos/gitlab/telecom-paris/ia-medical/src/simulation/trajectory_generator.py
"""
Trajectory generator for hospital simulation.

This module generates multiple trajectory scenarios based on historical simulation data.
"""

import simpy
import numpy as np
import random
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from src.config import DISEASES, DISEASE_WEIGHTS, SPECIALTIES
from src.data.db import (
    get_simulation_statistics, get_simulation_duration, 
    save_trajectory, save_trajectory_result
)
from src.simulation.models import Doctor, Patient

class TrajectorySimulation:
    """A lightweight simulation for generating trajectory scenarios."""
    
    def __init__(self, env: simpy.Environment, base_stats: Dict[str, Any], 
                 trajectory_params: Dict[str, Any], trajectory_id: int):
        """Initialize trajectory simulation.
        
        Args:
            env: SimPy environment
            base_stats: Historical statistics from base simulation
            trajectory_params: Modified parameters for this trajectory
            trajectory_id: Unique identifier for this trajectory
        """
        self.env = env
        self.base_stats = base_stats
        self.params = trajectory_params
        self.trajectory_id = trajectory_id
        
        # Initialize from base simulation parameters
        self.num_doctors = base_stats['num_doctors']
        self.arrival_rate = trajectory_params.get('arrival_rate', base_stats['arrival_rate'])
        
        # Trajectory-specific modifications
        self.arrival_variance = trajectory_params.get('arrival_variance', 1.0)
        self.disease_weights_modifier = trajectory_params.get('disease_weights_modifier', {})
        self.treatment_time_modifier = trajectory_params.get('treatment_time_modifier', 1.0)
        
        # Initialize doctors
        self.doctors = self._init_doctors()
        
        # Counters
        self.patients_total = 0
        self.patients_treated = 0
        
        # Results storage
        self.trajectory_db_id = None
        
    def _init_doctors(self) -> List[Doctor]:
        """Initialize doctors based on base simulation configuration."""
        doctors = []
        
        # Use the same distribution as the base simulation
        from src.config import SPECIALTY_PROPORTIONS
        
        spec_counts = {}
        total_proportion = sum(SPECIALTY_PROPORTIONS.values())
        
        for spec in SPECIALTIES:
            proportion = SPECIALTY_PROPORTIONS[spec] / total_proportion
            spec_counts[spec] = int(self.num_doctors * proportion)
        
        # Ensure exact number
        assigned_total = sum(spec_counts.values())
        remaining = self.num_doctors - assigned_total
        
        if remaining > 0:
            # Add to generalists first
            spec_counts['generalist'] = spec_counts.get('generalist', 0) + remaining
        
        # Create doctors
        id_counter = 1
        for spec, count in spec_counts.items():
            for _ in range(count):
                doctors.append(Doctor(id_counter, spec, self.env))
                id_counter += 1
                
        return doctors
    
    def get_modified_disease_weights(self) -> List[int]:
        """Get disease weights modified by trajectory parameters."""
        weights = DISEASE_WEIGHTS.copy()
        
        # Apply base historical patterns
        if 'disease_statistics' in self.base_stats:
            for disease_stat in self.base_stats['disease_statistics']:
                disease_name = disease_stat['disease']
                # Find disease index
                for i, (name, _, _) in enumerate(DISEASES):
                    if name == disease_name:
                        # Adjust weight based on historical frequency
                        historical_frequency = disease_stat['count']
                        # Normalize to a reasonable multiplier
                        multiplier = min(3.0, max(0.3, historical_frequency / 100))
                        weights[i] = int(weights[i] * multiplier)
                        break
        
        # Apply trajectory-specific modifications
        for disease_name, modifier in self.disease_weights_modifier.items():
            for i, (name, _, _) in enumerate(DISEASES):
                if name == disease_name:
                    weights[i] = int(weights[i] * modifier)
                    break
        
        return weights
    
    def get_arrival_rate_with_variance(self) -> float:
        """Get arrival rate with trajectory-specific variance."""
        base_rate = self.arrival_rate
        
        # Apply historical hourly patterns if available
        if 'hourly_patterns' in self.base_stats:
            current_hour = int((self.env.now / 60) % 24)
            hourly_data = self.base_stats['hourly_patterns']
            
            if hourly_data and current_hour in hourly_data:
                # Normalize hourly pattern to get a multiplier
                avg_hourly = sum(hourly_data.values()) / len(hourly_data) if hourly_data else 1
                hourly_multiplier = hourly_data[current_hour] / avg_hourly if avg_hourly > 0 else 1
                base_rate *= hourly_multiplier
        
        # Apply trajectory variance
        variance_factor = np.random.normal(1.0, self.arrival_variance * 0.2)
        variance_factor = max(0.1, min(3.0, variance_factor))  # Clamp to reasonable range
        
        return base_rate * variance_factor
    
    def run_trajectory(self, duration_minutes: int, db_base_sim_id: int) -> None:
        """Run the trajectory simulation.
        
        Args:
            duration_minutes: How long to run the trajectory
            db_base_sim_id: Database ID of the base simulation
        """
        # Save trajectory metadata
        self.trajectory_db_id = save_trajectory(
            db_base_sim_id, 
            self.trajectory_id,
            self.env.now,
            self.env.now + duration_minutes,
            self.params,
            f"Trajectory {self.trajectory_id} - {duration_minutes}min"
        )
        
        # Start processes
        self.env.process(self.patient_arrivals())
        self.env.process(self.data_collector())
        
        # Run simulation
        target_time = self.env.now + duration_minutes
        self.env.run(until=target_time)
    
    def patient_arrivals(self):
        """Generate patient arrivals for the trajectory."""
        while True:
            # Get dynamic arrival rate
            effective_rate = self.get_arrival_rate_with_variance()
            effective_rate = max(1, effective_rate)  # Ensure at least 1/hour
            
            # Calculate inter-arrival time
            interarrival = np.random.exponential(60 / effective_rate)
            yield self.env.timeout(interarrival)
            
            # Get modified disease weights
            disease_weights = self.get_modified_disease_weights()
            
            # Select disease
            disease, mean_time, specialty = random.choices(DISEASES, weights=disease_weights, k=1)[0]
            
            # Apply treatment time modifier
            modified_mean_time = mean_time * self.treatment_time_modifier
            treatment_time = max(1, int(np.random.exponential(modified_mean_time)))
            
            # Create patient
            patient = Patient(
                id=f"T{self.trajectory_id}_P{self.patients_total}",
                disease=disease,
                treatment_time=treatment_time,
                specialty=specialty,
                arrival_time=self.env.now,
            )
            self.patients_total += 1
            self.env.process(self.handle_patient(patient))
    
    def handle_patient(self, patient: Patient):
        """Handle patient through the system."""
        # Find appropriate doctor
        candidates = [d for d in self.doctors if d.specialty == patient.specialty]
        if not candidates:
            candidates = [d for d in self.doctors if d.specialty == "generalist"]
        
        # Choose doctor (prefer free, else shortest queue)
        free_doctors = [d for d in candidates if d.resource.count == 0]
        if free_doctors:
            doctor = random.choice(free_doctors)
        else:
            doctor = min(candidates, key=lambda d: len(d.queue))
        
        doctor.queue.append(patient)
        with doctor.resource.request() as req:
            yield req
            doctor.queue.remove(patient)
            patient.start_treatment = self.env.now
            
            yield self.env.timeout(patient.treatment_time)
            patient.end_treatment = self.env.now
            doctor.patients_treated += 1
            self.patients_treated += 1
    
    def data_collector(self):
        """Collect trajectory data periodically."""
        while True:
            yield self.env.timeout(60)  # Collect every hour
            
            # Calculate metrics
            busy_doctors = sum(1 for d in self.doctors if d.resource.count > 0)
            waiting_patients = sum(len(d.queue) for d in self.doctors)
            
            # Calculate average wait time (simplified)
            total_wait = 0
            wait_count = 0
            for doctor in self.doctors:
                for patient in doctor.queue:
                    total_wait += self.env.now - patient.arrival_time
                    wait_count += 1
            
            avg_wait_time = total_wait / wait_count if wait_count > 0 else 0
            
            # Save to database
            if self.trajectory_db_id:
                save_trajectory_result(
                    self.trajectory_db_id,
                    self.env.now,
                    self.patients_total,
                    self.patients_treated,
                    busy_doctors,
                    waiting_patients,
                    avg_wait_time
                )


class TrajectoryGenerator:
    """Generates multiple trajectory scenarios based on historical data."""
    
    def __init__(self, base_sim_id: int):
        """Initialize trajectory generator.
        
        Args:
            base_sim_id: ID of the base simulation to analyze
        """
        self.base_sim_id = base_sim_id
        self.base_stats = None
        self.trajectories_generated = 0
        
    def validate_simulation(self) -> bool:
        """Check if the base simulation is suitable for trajectory generation.
        
        Returns:
            bool: True if simulation has enough data (>= 1 month)
        """
        duration = get_simulation_duration(self.base_sim_id)
        if duration is None:
            print(f"Simulation {self.base_sim_id} not found.")
            return False
        
        # Check if simulation is at least 1 month (43,200 minutes = 30 days)
        min_duration = 30 * 24 * 60  # 30 days in minutes
        if duration < min_duration:
            print(f"Simulation {self.base_sim_id} has only {duration:.0f} minutes ({duration/1440:.1f} days).")
            print(f"Need at least {min_duration} minutes ({min_duration/1440} days) for trajectory generation.")
            return False
        
        print(f"Simulation {self.base_sim_id} has {duration:.0f} minutes ({duration/1440:.1f} days) - suitable for trajectories.")
        return True
    
    def load_base_statistics(self) -> bool:
        """Load statistical patterns from the base simulation.
        
        Returns:
            bool: True if statistics were successfully loaded
        """
        self.base_stats = get_simulation_statistics(self.base_sim_id)
        if self.base_stats is None:
            print(f"Could not load statistics for simulation {self.base_sim_id}")
            return False
        
        print(f"Loaded base statistics:")
        print(f"  - {self.base_stats['num_doctors']} doctors")
        print(f"  - {self.base_stats['arrival_rate']} base arrival rate")
        print(f"  - {len(self.base_stats['disease_statistics'])} disease patterns")
        print(f"  - {len(self.base_stats['hourly_patterns'])} hourly patterns")
        
        return True
    
    def generate_trajectory_parameters(self, num_trajectories: int = 50) -> List[Dict[str, Any]]:
        """Generate parameters for multiple trajectory scenarios.
        
        Args:
            num_trajectories: Number of trajectories to generate
            
        Returns:
            List of parameter dictionaries for each trajectory
        """
        trajectories = []
        
        for i in range(num_trajectories):
            # Base parameters
            params = {
                'trajectory_id': i + 1,
                'arrival_rate': self.base_stats['arrival_rate'],
                'arrival_variance': np.random.uniform(0.8, 1.3),  # ±30% variance
                'treatment_time_modifier': np.random.uniform(0.9, 1.2),  # ±20% treatment time
                'disease_weights_modifier': {}
            }
            
            # Add some random disease weight modifications
            if random.random() < 0.3:  # 30% chance of disease outbreak
                outbreak_disease = random.choice([d[0] for d in DISEASES])
                params['disease_weights_modifier'][outbreak_disease] = np.random.uniform(1.5, 3.0)
            
            if random.random() < 0.2:  # 20% chance of reduced disease
                reduced_disease = random.choice([d[0] for d in DISEASES])
                params['disease_weights_modifier'][reduced_disease] = np.random.uniform(0.3, 0.7)
            
            # Seasonal variations
            if random.random() < 0.4:  # 40% chance of seasonal effect
                params['arrival_rate'] *= np.random.uniform(0.7, 1.4)
            
            trajectories.append(params)
        
        return trajectories
    
    def run_trajectories(self, num_trajectories: int = 50, trajectory_duration_days: int = 30) -> bool:
        """Generate and run multiple trajectory scenarios.
        
        Args:
            num_trajectories: Number of trajectories to generate
            trajectory_duration_days: Duration of each trajectory in days
            
        Returns:
            bool: True if trajectories were successfully generated
        """
        if not self.validate_simulation():
            return False
        
        if not self.load_base_statistics():
            return False
        
        trajectory_params = self.generate_trajectory_parameters(num_trajectories)
        duration_minutes = trajectory_duration_days * 24 * 60
        
        print(f"\nGenerating {num_trajectories} trajectories of {trajectory_duration_days} days each...")
        print("This may take several minutes...")
        
        for i, params in enumerate(trajectory_params):
            print(f"Running trajectory {i+1}/{num_trajectories}...", end='', flush=True)
            
            # Create new environment for each trajectory
            env = simpy.Environment()
            
            # Create trajectory simulation
            traj_sim = TrajectorySimulation(env, self.base_stats, params, params['trajectory_id'])
            
            # Run the trajectory
            traj_sim.run_trajectory(duration_minutes, self.base_sim_id)
            
            self.trajectories_generated += 1
            print(" ✓")
        
        print(f"\nSuccessfully generated {self.trajectories_generated} trajectories for simulation {self.base_sim_id}")
        print(f"Results saved to database and can be accessed via the dashboard.")
        
        return True


def generate_trajectories_for_simulation(sim_id: int, num_trajectories: int = 50, 
                                       duration_days: int = 30) -> bool:
    """Main function to generate trajectories for a simulation.
    
    Args:
        sim_id: Base simulation ID
        num_trajectories: Number of trajectories to generate
        duration_days: Duration of each trajectory in days
        
    Returns:
        bool: True if successful
    """
    generator = TrajectoryGenerator(sim_id)
    return generator.run_trajectories(num_trajectories, duration_days)