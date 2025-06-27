"""
Hospital simulation models.

This module contains the model classes used in the simulation, such as Doctor and Patient.
"""

import simpy
from typing import Optional

class Doctor:
    """Represents a doctor in the hospital simulation.
    
    Attributes:
        id (int): Unique identifier for the doctor
        specialty (str): Medical specialty of the doctor
        resource (simpy.Resource): SimPy resource for patient handling
        patients_treated (int): Count of patients treated by this doctor
        queue (list): List of patients waiting for this doctor
    """
    
    def __init__(self, id: int, specialty: str, env: simpy.Environment):
        """Initialize a new doctor.
        
        Args:
            id: Unique identifier for the doctor
            specialty: Medical specialty of the doctor
            env: SimPy environment for simulation
        """
        self.id = id
        self.specialty = specialty
        self.resource = simpy.Resource(env, capacity=1)
        self.patients_treated = 0
        self.queue = []


class Patient:
    """Represents a patient in the hospital simulation.
    
    Attributes:
        id (str): Unique identifier for the patient
        disease (str): Disease the patient is suffering from
        treatment_time (int): Required time for treatment in minutes
        specialty (str): Required doctor specialty for treatment
        arrival_time (float): Time when patient arrived in simulation minutes
        start_treatment (Optional[float]): Time when treatment started, None if not started
        end_treatment (Optional[float]): Time when treatment ended, None if not ended
    """
    
    def __init__(self, id: str, disease: str, treatment_time: int, specialty: str, arrival_time: float):
        """Initialize a new patient.
        
        Args:
            id: Unique identifier for the patient
            disease: Disease the patient is suffering from
            treatment_time: Required time for treatment in minutes
            specialty: Required doctor specialty for treatment
            arrival_time: Time when patient arrived in simulation minutes
        """
        self.id = id
        self.disease = disease
        self.treatment_time = treatment_time
        self.specialty = specialty
        self.arrival_time = arrival_time
        self.start_treatment = None
        self.end_treatment = None