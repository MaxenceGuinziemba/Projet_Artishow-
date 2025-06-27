"""
Configuration settings for the hospital simulation.

This module contains all the configuration settings and constants used 
by the simulation, dashboard, and machine learning components.
"""

import os
from datetime import datetime
from typing import Dict, List, Tuple, Any

# Path configuration
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
DB_PATH = os.path.join(DATA_DIR, 'hospital_sim.db')

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Simulation start date: January 1, 2025 at 00:00
SIM_START_DATE = datetime(2025, 1, 1, 0, 0)

# Disease definitions: [name, mean_treatment_time, required_specialty]
DISEASES: List[List[Any]] = [
    ["viral_infection", 20, "generalist"],           # 20 mins for examination, prescription
    ["minor_fracture", 40, "emergency"],             # 40 mins for x-ray, casting
    ["open_wound", 25, "emergency"],                 # 25 mins for cleaning and suturing
    ["asthma_attack", 35, "pulmonologist"],          # Changed from paleontologist to pulmonologist
    ["abdominal_pain", 45, "generalist"],            # 45 mins for examination and tests
    ["acute_back_pain", 25, "generalist"],           # 25 mins for examination
    ["urinary_infection", 15, "generalist"],         # 15 mins for quick diagnosis
    ["chest_pain", 40, "cardiologist"],              # Changed from malaise to chest_pain
    ["gastroenteritis", 30, "generalist"],           # 30 mins for diagnosis and treatment
    ["pregnant_woman", 60, "gynecologist"],          # 60 mins for prenatal checkup
    ["stroke", 120, "neurologist"],                  # 120 mins for emergency stroke care
    ["heart_attack", 90, "cardiologist"],            # 90 mins for emergency cardiac care
]

DISEASE_WEIGHTS: List[int] = [25, 14, 12, 6, 8, 9, 10, 6, 5, 2, 1, 2]

SPECIALTIES: List[str] = [
    "generalist", "emergency", "neurologist", "cardiologist", 
    "gynecologist", "pulmonologist"
]

SPECIALTY_PROPORTIONS: Dict[str, float] = {
    "generalist": 0.40,      # Increased since most common diseases need generalists
    "emergency": 0.20,       # High for urgent/trauma cases
    "cardiologist": 0.10,    # For heart conditions
    "neurologist": 0.08,     # For stroke and neurological issues
    "gynecologist": 0.10,    # For women's health
    "pulmonologist": 0.12,   # For respiratory issues like asthma
}

# Special dates that affect hospital arrivals
SPECIAL_DATES: List[Dict[str, Any]] = [
    # New Year's Eve and Day (increased accidents)
    {"month": 12, "day": 31, "factor": 1.5, "name": "New Year's Eve"},
    {"month": 1, "day": 1, "factor": 1.6, "name": "New Year's Day"},
    # Fourth of July (fireworks and outdoor injuries)
    {"month": 7, "day": 4, "factor": 1.4, "name": "Independence Day"},
    # Halloween (injuries related to activities)
    {"month": 10, "day": 31, "factor": 1.3, "name": "Halloween"},
    # Christmas (usually quieter except for accidents)
    {"month": 12, "day": 24, "factor": 0.8, "name": "Christmas Eve"},
    {"month": 12, "day": 25, "factor": 0.7, "name": "Christmas Day"},
    # Thanksgiving (cooking accidents, family tensions)
    {"month": 11, "day": 26, "factor": 1.2, "name": "Thanksgiving"}, # Approximate date
]

# Hour of day factors (0-23): each factor represents patient arrival rate relative to average
HOUR_FACTORS = [
    0.4,  # 00:00 - Very quiet overnight
    0.3,  # 01:00
    0.2,  # 02:00 - Lowest point of the day
    0.2,  # 03:00
    0.3,  # 04:00
    0.4,  # 05:00 - Starting to pick up
    0.6,  # 06:00 - Morning increase
    0.9,  # 07:00
    1.3,  # 08:00 - Morning rush
    1.5,  # 09:00 - Peak morning hours
    1.4,  # 10:00
    1.3,  # 11:00
    1.4,  # 12:00 - Lunch time incidents
    1.3,  # 13:00
    1.2,  # 14:00
    1.1,  # 15:00
    1.2,  # 16:00 - Afternoon pickup
    1.4,  # 17:00 - After work rush
    1.6,  # 18:00 - Evening peak
    1.5,  # 19:00 - Dinner time
    1.3,  # 20:00
    1.1,  # 21:00 - Starting to slow down
    0.8,  # 22:00
    0.6,  # 23:00 - Late night
]

# Day of week factors (0-6, where 0 is Monday): 
# how arrival rate varies by day of week
DAY_FACTORS = [
    1.0,  # Monday - Average
    0.9,  # Tuesday - Slightly below average
    0.9,  # Wednesday
    1.0,  # Thursday
    1.1,  # Friday - Slight increase
    1.4,  # Saturday - Weekend peak
    1.2,  # Sunday - Still high but lower than Saturday
]

# Month factors (1-12): seasonal variations
MONTH_FACTORS = [
    1.2,  # January - Winter illnesses
    1.2,  # February - Still high with flu season
    1.1,  # March - Starting to decrease
    1.0,  # April
    0.9,  # May
    0.8,  # June - Summer lull
    0.8,  # July - Summer low point
    0.8,  # August - Still low
    0.9,  # September - Back to school/work
    1.0,  # October - Fall illnesses begin
    1.1,  # November - Increasing illnesses
    1.2,  # December - Winter illnesses, holiday accidents
]

# Dashboard configuration
DASHBOARD_PORT = 8080
DASHBOARD_DEBUG = True
DASHBOARD_UPDATE_INTERVAL = 5000  # milliseconds

# Default simulation parameters
DEFAULT_NUM_DOCTORS = 25  # Adjusted from 30 to 25 for better balance
DEFAULT_ARRIVAL_RATE = 20  # Reduced from 50 to 20 patients per hour (1 per 3 minutes on average)
DEFAULT_SIM_MINUTES = 525600  # 1 year
