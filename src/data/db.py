"""
Database utilities for hospital simulation.

This module provides functions for database initialization and access.
"""

import sqlite3
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

from src.config import DB_PATH

def init_database() -> None:
    """Initialize SQLite database with required tables for the hospital simulation.
    
    Creates tables for patient treatments, hospital state, and simulation metadata if they don't exist.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create simulations table to track different simulation runs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS simulations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        start_time TEXT,
        config TEXT,
        num_doctors INTEGER,
        arrival_rate REAL,
        description TEXT
    )
    ''')
    
    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS patient_treated (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sim_id INTEGER,
        doctor_id INTEGER,
        doctor_specialty TEXT,
        disease TEXT,
        treatment_time INTEGER,
        wait_time INTEGER,
        arrival_time TEXT,
        start_treatment TEXT,
        end_treatment TEXT,
        sim_minutes REAL,
        timestamp TEXT,
        FOREIGN KEY (sim_id) REFERENCES simulations (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS hospital_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sim_id INTEGER,
        patients_total INTEGER,
        patients_treated INTEGER,
        busy_doctors INTEGER,
        waiting_patients INTEGER,
        sim_time TEXT,
        sim_minutes REAL,
        timestamp TEXT,
        FOREIGN KEY (sim_id) REFERENCES simulations (id)
    )
    ''')
    
    # Add a simulation metadata table to store the current state for resuming
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sim_metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sim_id INTEGER,
        start_date TEXT,
        last_sim_time REAL,
        patients_total INTEGER,
        patients_treated INTEGER,
        active_doctors TEXT,
        timestamp TEXT,
        FOREIGN KEY (sim_id) REFERENCES simulations (id)
    )
    ''')
    
    # Create a table for simulation events (patient flow, doctor assignments, etc.)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS simulation_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sim_id INTEGER,
        event_id TEXT,
        event_type TEXT,
        params TEXT,
        start_time TEXT,
        end_time TEXT,
        start_sim_minutes REAL,
        end_sim_minutes REAL,
        timestamp TEXT,
        FOREIGN KEY (sim_id) REFERENCES simulations (id)
    )
    ''')
    
    # Create a table for parameter changes during simulation
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS parameter_changes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sim_id INTEGER,
        sim_time TEXT,
        sim_minutes REAL,
        old_values TEXT,
        new_values TEXT,
        timestamp TEXT,
        FOREIGN KEY (sim_id) REFERENCES simulations (id)
    )
    ''')
    
    # Create a table for detailed simulation events (arrivals, treatments, etc.)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS detailed_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sim_id INTEGER,
        event_type TEXT,
        patient_id TEXT,
        doctor_id INTEGER,
        event_time TEXT,
        sim_minutes REAL,
        details TEXT,
        timestamp TEXT,
        FOREIGN KEY (sim_id) REFERENCES simulations (id)
    )
    ''')
    
    # Create a table for ML model predictions
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sim_id INTEGER,
        prediction_date TEXT,
        prediction_type TEXT,
        value REAL,
        confidence REAL,
        model_name TEXT,
        features TEXT,
        timestamp TEXT,
        FOREIGN KEY (sim_id) REFERENCES simulations (id)
    )
    ''')
    
    # Create tables for trajectory analysis
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trajectories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        base_sim_id INTEGER,
        trajectory_id INTEGER,
        trajectory_start_time REAL,
        trajectory_end_time REAL,
        parameters TEXT,
        description TEXT,
        timestamp TEXT,
        FOREIGN KEY (base_sim_id) REFERENCES simulations (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trajectory_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trajectory_id INTEGER,
        sim_time REAL,
        patients_total INTEGER,
        patients_treated INTEGER,
        busy_doctors INTEGER,
        waiting_patients INTEGER,
        avg_wait_time REAL,
        timestamp TEXT,
        FOREIGN KEY (trajectory_id) REFERENCES trajectories (id)
    )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection() -> sqlite3.Connection:
    """Connect to the SQLite database and set up row factory.
    
    Returns:
        sqlite3.Connection: An open connection to the database with row_factory set
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_new_simulation(num_doctors: int, arrival_rate: float, description: str = "") -> int:
    """Create a new simulation record and return its ID.
    
    Args:
        num_doctors: Number of doctors in the simulation
        arrival_rate: Patient arrival rate per hour
        description: Optional description of this simulation run
        
    Returns:
        int: ID of the newly created simulation record
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    config = json.dumps({
        "num_doctors": num_doctors,
        "arrival_rate": arrival_rate,
        "start_time": datetime.now().isoformat()
    })
    
    cursor.execute(
        "INSERT INTO simulations (start_time, config, num_doctors, arrival_rate, description) VALUES (?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), config, num_doctors, arrival_rate, description)
    )
    
    sim_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return sim_id

def get_latest_simulation_id() -> Optional[int]:
    """Get the ID of the most recent simulation run.
    
    Returns:
        int: ID of the most recent simulation, or None if no simulations exist
    """
    conn = get_db_connection()
    result = conn.execute("SELECT id FROM simulations ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    
    if result:
        return result['id']
    return None

def get_all_simulation_ids() -> List[Dict[str, Any]]:
    """Get all simulation IDs and their basic information.
    
    Returns:
        List[Dict]: List of dictionaries containing simulation info
    """
    conn = get_db_connection()
    result = conn.execute("""
        SELECT id, start_time, num_doctors, arrival_rate, description 
        FROM simulations 
        ORDER BY id DESC
    """).fetchall()
    conn.close()
    
    simulations = []
    for row in result:
        simulations.append({
            'id': row['id'],
            'start_time': row['start_time'],
            'num_doctors': row['num_doctors'],
            'arrival_rate': row['arrival_rate'],
            'description': row['description']
        })
    
    return simulations

def get_simulation_by_id(sim_id: int) -> Optional[Dict[str, Any]]:
    """Get simulation information by ID.
    
    Args:
        sim_id: Simulation ID to look up
        
    Returns:
        Dict containing simulation info, or None if not found
    """
    conn = get_db_connection()
    result = conn.execute("""
        SELECT * FROM simulations WHERE id = ?
    """, (sim_id,)).fetchone()
    conn.close()
    
    if result:
        return dict(result)
    return None

def get_simulation_duration(sim_id: int) -> Optional[float]:
    """Get the duration of a simulation in minutes.
    
    Args:
        sim_id: Simulation ID to check
        
    Returns:
        Duration in minutes, or None if simulation not found
    """
    conn = get_db_connection()
    result = conn.execute("""
        SELECT MAX(sim_minutes) - MIN(sim_minutes) as duration
        FROM hospital_state 
        WHERE sim_id = ?
    """, (sim_id,)).fetchone()
    conn.close()
    
    if result and result['duration'] is not None:
        return float(result['duration'])
    return None

def get_simulation_statistics(sim_id: int) -> Optional[Dict[str, Any]]:
    """Get comprehensive statistics from a simulation for trajectory generation.
    
    Args:
        sim_id: Simulation ID to analyze
        
    Returns:
        Dictionary with simulation statistics, or None if not found
    """
    conn = get_db_connection()
    
    # Basic simulation info
    sim_info = conn.execute("""
        SELECT * FROM simulations WHERE id = ?
    """, (sim_id,)).fetchone()
    
    if not sim_info:
        conn.close()
        return None
    
    # Patient statistics by disease
    disease_stats = conn.execute("""
        SELECT disease, 
               COUNT(*) as count,
               AVG(treatment_time) as avg_treatment_time,
               AVG(wait_time) as avg_wait_time,
               doctor_specialty
        FROM patient_treated 
        WHERE sim_id = ?
        GROUP BY disease, doctor_specialty
    """, (sim_id,)).fetchall()
    
    # Hourly arrival patterns
    hourly_patterns = conn.execute("""
        SELECT strftime('%H', arrival_time) as hour,
               COUNT(*) as arrivals
        FROM patient_treated 
        WHERE sim_id = ?
        GROUP BY hour
        ORDER BY hour
    """, (sim_id,)).fetchall()
    
    # Overall statistics
    overall_stats = conn.execute("""
        SELECT AVG(patients_total) as avg_patients_total,
               AVG(patients_treated) as avg_patients_treated,
               AVG(busy_doctors) as avg_busy_doctors,
               AVG(waiting_patients) as avg_waiting_patients
        FROM hospital_state 
        WHERE sim_id = ?
    """, (sim_id,)).fetchone()
    
    # Weekly patterns
    weekly_patterns = conn.execute("""
        SELECT strftime('%w', arrival_time) as day_of_week,
               COUNT(*) as arrivals
        FROM patient_treated 
        WHERE sim_id = ?
        GROUP BY day_of_week
        ORDER BY day_of_week
    """, (sim_id,)).fetchall()
    
    conn.close()
    
    # Convert to dictionaries for easier processing
    disease_data = []
    for row in disease_stats:
        disease_data.append(dict(row))
    
    hourly_data = {}
    for row in hourly_patterns:
        hourly_data[int(row['hour'])] = row['arrivals']
    
    weekly_data = {}
    for row in weekly_patterns:
        weekly_data[int(row['day_of_week'])] = row['arrivals']
    
    return {
        'sim_id': sim_id,
        'num_doctors': sim_info['num_doctors'],
        'arrival_rate': sim_info['arrival_rate'],
        'disease_statistics': disease_data,
        'hourly_patterns': hourly_data,
        'weekly_patterns': weekly_data,
        'overall_statistics': dict(overall_stats) if overall_stats else {},
        'start_time': sim_info['start_time']
    }

def save_trajectory(base_sim_id: int, trajectory_id: int, start_time: float, 
                   end_time: float, parameters: Dict[str, Any], description: str) -> int:
    """Save trajectory metadata to database.
    
    Args:
        base_sim_id: ID of the base simulation
        trajectory_id: Unique trajectory identifier
        start_time: Trajectory start time in simulation minutes
        end_time: Trajectory end time in simulation minutes
        parameters: Parameters used for this trajectory
        description: Description of the trajectory
        
    Returns:
        Database ID of the created trajectory record
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO trajectories 
        (base_sim_id, trajectory_id, trajectory_start_time, trajectory_end_time, 
         parameters, description, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        base_sim_id, trajectory_id, start_time, end_time,
        json.dumps(parameters), description, datetime.now().isoformat()
    ))
    
    trajectory_db_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return trajectory_db_id

def save_trajectory_result(trajectory_db_id: int, sim_time: float, 
                          patients_total: int, patients_treated: int,
                          busy_doctors: int, waiting_patients: int,
                          avg_wait_time: float) -> None:
    """Save trajectory simulation results.
    
    Args:
        trajectory_db_id: Database ID of the trajectory
        sim_time: Current simulation time
        patients_total: Total patients in system
        patients_treated: Total patients treated
        busy_doctors: Number of busy doctors
        waiting_patients: Number of waiting patients
        avg_wait_time: Average wait time
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO trajectory_results 
        (trajectory_id, sim_time, patients_total, patients_treated, 
         busy_doctors, waiting_patients, avg_wait_time, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        trajectory_db_id, sim_time, patients_total, patients_treated,
        busy_doctors, waiting_patients, avg_wait_time, datetime.now().isoformat()
    ))
    
    conn.commit()
    conn.close()

def get_trajectory_results(base_sim_id: int) -> List[Dict[str, Any]]:
    """Get all trajectory results for a base simulation.
    
    Args:
        base_sim_id: Base simulation ID
        
    Returns:
        List of trajectory results with metadata
    """
    conn = get_db_connection()
    
    results = conn.execute("""
        SELECT t.trajectory_id, t.parameters, t.description,
               tr.sim_time, tr.patients_total, tr.patients_treated,
               tr.busy_doctors, tr.waiting_patients, tr.avg_wait_time
        FROM trajectories t
        JOIN trajectory_results tr ON t.id = tr.trajectory_id
        WHERE t.base_sim_id = ?
        ORDER BY t.trajectory_id, tr.sim_time
    """, (base_sim_id,)).fetchall()
    
    conn.close()
    
    trajectory_data = []
    for row in results:
        trajectory_data.append(dict(row))
    
    return trajectory_data

def optimize_database_performance():
    """Apply SQLite performance optimizations for better Linux performance."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Enable WAL mode for better concurrent access
    cursor.execute("PRAGMA journal_mode=WAL")
    # Increase cache size (10MB cache)
    cursor.execute("PRAGMA cache_size=10000")
    # Reduce synchronization for speed
    cursor.execute("PRAGMA synchronous=NORMAL")
    # Memory temp store
    cursor.execute("PRAGMA temp_store=MEMORY")
    # Increase page size for better I/O
    cursor.execute("PRAGMA page_size=4096")
    
    conn.commit()
    conn.close()