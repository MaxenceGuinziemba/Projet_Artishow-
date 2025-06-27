#!/usr/bin/env python3
"""
Dashboard application for hospital simulation visualization.

This Flask application provides a web interface to visualize and monitor
hospital simulation data with real-time playback capabilities.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from datetime import datetime, timedelta
import sqlite3
import json
from typing import Dict, List, Any, Optional
import numpy as np

from src.config import DB_PATH, DASHBOARD_PORT
from src.data.db import get_db_connection, get_all_simulation_ids, get_trajectory_results, get_simulation_duration
from src.ml.danger_prediction import get_danger_predictions, train_hospital_models

app = Flask(__name__, 
           template_folder='templates',
           static_folder='static')

@app.route('/')
def index():
    """Main dashboard page with simulation selection."""
    return render_template('index.html')

@app.route('/analytics/<int:sim_id>')
def analytics(sim_id: int):
    """Analytics page showing comprehensive time-based graphs."""
    return render_template('analytics.html', sim_id=sim_id)

@app.route('/incidents/<int:sim_id>')
def incidents(sim_id: int):
    """Incidents page showing alerts and problematic periods."""
    return render_template('incidents.html', sim_id=sim_id)

@app.route('/realtime/<int:sim_id>')
def realtime(sim_id: int):
    """Real-time simulation playback page."""
    return render_template('realtime.html', sim_id=sim_id)

@app.route('/predictions/<int:sim_id>')
def predictions_page(sim_id):
    """Display the predictions page for a simulation."""
    # Check if simulation exists
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM hospital_state WHERE sim_id = ?", (sim_id,))
    count = cursor.fetchone()[0]
    conn.close()
    
    if count == 0:
        flash(f'Simulation {sim_id} not found', 'error')
        return redirect(url_for('index'))
    
    return render_template('predictions.html', sim_id=sim_id)

@app.route('/trajectories/<int:sim_id>')
def trajectories(sim_id):
    """Display trajectory analysis page for a simulation."""
    return render_template('trajectories.html', sim_id=sim_id)

# API Routes

@app.route('/api/simulations')
def api_simulations():
    """Get list of all simulations with basic info."""
    try:
        conn = get_db_connection()
        
        # Get all simulations with their basic info directly from database
        sim_rows = conn.execute("""
            SELECT id, start_time, num_doctors, arrival_rate, description
            FROM simulations 
            ORDER BY start_time DESC
        """).fetchall()
        
        simulations = []
        for row in sim_rows:
            sim_data = {
                'id': row['id'],
                'start_time': row['start_time'],
                'num_doctors': row['num_doctors'],
                'arrival_rate': row['arrival_rate'],
                'description': row['description']
            }
            simulations.append(sim_data)
        
        conn.close()
        return jsonify({'success': True, 'data': simulations})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/simulation/<int:sim_id>/info')
def api_simulation_info(sim_id: int):
    """Get detailed information about a specific simulation."""
    try:
        conn = get_db_connection()
        
        # Get simulation basic info
        sim_info = conn.execute("""
            SELECT * FROM simulations WHERE id = ?
        """, (sim_id,)).fetchone()
        
        if not sim_info:
            return jsonify({'success': False, 'error': 'Simulation not found'}), 404
        
        # Get latest metadata (check if table exists)
        metadata = None
        try:
            metadata = conn.execute("""
                SELECT * FROM sim_metadata WHERE sim_id = ? 
                ORDER BY timestamp DESC LIMIT 1
            """, (sim_id,)).fetchone()
        except sqlite3.OperationalError:
            pass
        
        # Get time range
        time_range = conn.execute("""
            SELECT MIN(sim_minutes) as min_time, MAX(sim_minutes) as max_time
            FROM hospital_state WHERE sim_id = ?
        """, (sim_id,)).fetchone()
        
        # Get total events count (check if table exists)
        events_count = None
        try:
            events_count = conn.execute("""
                SELECT COUNT(*) as count FROM detailed_events WHERE sim_id = ?
            """, (sim_id,)).fetchone()
        except sqlite3.OperationalError:
            events_count = {'count': 0}
        
        conn.close()
        
        result = {
            'id': sim_info['id'],
            'start_time': sim_info['start_time'],
            'num_doctors': sim_info['num_doctors'],
            'arrival_rate': sim_info['arrival_rate'],
            'description': sim_info['description'],
            'time_range': {
                'min': time_range['min_time'] if time_range['min_time'] else 0,
                'max': time_range['max_time'] if time_range['max_time'] else 0
            },
            'events_count': events_count['count'] if events_count else 0
        }
        
        if metadata:
            result.update({
                'patients_total': metadata['patients_total'],
                'patients_treated': metadata['patients_treated'],
                'last_update': metadata['timestamp']
            })
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/simulation/<int:sim_id>/analytics')
def api_analytics_data(sim_id: int):
    """Get analytics data for charts."""
    try:
        conn = get_db_connection()
        
        # Get hospital state over time with proper ordering and precision
        hospital_states = conn.execute("""
            SELECT sim_minutes, patients_total, patients_treated, busy_doctors, 
                   waiting_patients, sim_time
            FROM hospital_state 
            WHERE sim_id = ? 
            ORDER BY sim_minutes ASC
        """, (sim_id,)).fetchall()
        
        print(f"Retrieved {len(hospital_states)} hospital state records for simulation {sim_id}")
        if len(hospital_states) > 0:
            print(f"Time range: {hospital_states[0]['sim_minutes']:.1f} to {hospital_states[-1]['sim_minutes']:.1f} minutes")
            # Show a sample of the time differences to verify minute-level granularity
            if len(hospital_states) > 1:
                time_diffs = [hospital_states[i+1]['sim_minutes'] - hospital_states[i]['sim_minutes'] 
                             for i in range(min(10, len(hospital_states)-1))]
                print(f"Sample time differences (first 10): {time_diffs}")
        
        
        # Get patient treatments by hour
        hourly_treatments = conn.execute("""
            SELECT strftime('%H', start_treatment) as hour,
                   COUNT(*) as count,
                   AVG(wait_time) as avg_wait_time,
                   AVG(treatment_time) as avg_treatment_time
            FROM patient_treated 
            WHERE sim_id = ?
            GROUP BY hour
            ORDER BY hour
        """, (sim_id,)).fetchall()
        
        # Get disease distribution
        disease_distribution = conn.execute("""
            SELECT disease, COUNT(*) as count
            FROM patient_treated 
            WHERE sim_id = ?
            GROUP BY disease
            ORDER BY count DESC
        """, (sim_id,)).fetchall()
        
        # Get doctor performance
        doctor_performance = conn.execute("""
            SELECT doctor_id, doctor_specialty, 
                   COUNT(*) as patients_treated,
                   AVG(treatment_time) as avg_treatment_time,
                   AVG(wait_time) as avg_wait_time
            FROM patient_treated 
            WHERE sim_id = ?
            GROUP BY doctor_id, doctor_specialty
            ORDER BY patients_treated DESC
        """, (sim_id,)).fetchall()
        
        # Get daily patterns
        daily_patterns = conn.execute("""
            SELECT DATE(start_treatment) as date,
                   COUNT(*) as patients,
                   AVG(wait_time) as avg_wait_time,
                   MAX(wait_time) as max_wait_time
            FROM patient_treated 
            WHERE sim_id = ?
            GROUP BY date
            ORDER BY date
        """, (sim_id,)).fetchall()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'hospital_states': [dict(row) for row in hospital_states],
                'hourly_treatments': [dict(row) for row in hourly_treatments],
                'disease_distribution': [dict(row) for row in disease_distribution],
                'doctor_performance': [dict(row) for row in doctor_performance],
                'daily_patterns': [dict(row) for row in daily_patterns]
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/simulation/<int:sim_id>/incidents')
def api_incidents_data(sim_id: int):
    """Get incidents and alerts data."""
    try:
        conn = get_db_connection()
        
        # Define thresholds for incidents
        HIGH_WAIT_TIME_THRESHOLD = 60  # minutes
        HIGH_OCCUPANCY_THRESHOLD = 0.9  # 90% of doctors busy
        
        # Check if tables exist first
        tables_check = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('hospital_state', 'patient_treated', 'simulation_events', 'simulations')
        """).fetchall()
        
        existing_tables = [row['name'] for row in tables_check]
        
        # Get simulation info safely
        if 'simulations' in existing_tables:
            sim_info = conn.execute("SELECT num_doctors FROM simulations WHERE id = ?", (sim_id,)).fetchone()
            total_doctors = sim_info['num_doctors'] if sim_info else 30
        else:
            total_doctors = 30  # Default fallback
        
        # Find high wait time incidents
        high_wait_incidents = []
        if 'hospital_state' in existing_tables:
            high_wait_incidents = conn.execute("""
                SELECT sim_time, sim_minutes, patients_total, patients_treated,
                       busy_doctors, waiting_patients
                FROM hospital_state 
                WHERE sim_id = ? AND waiting_patients > 10
                ORDER BY sim_minutes
            """, (sim_id,)).fetchall()
        
        # Find high occupancy periods
        high_occupancy_incidents = []
        if 'hospital_state' in existing_tables:
            high_occupancy_incidents = conn.execute("""
                SELECT sim_time, sim_minutes, patients_total, patients_treated,
                       busy_doctors, waiting_patients,
                       CAST(busy_doctors AS FLOAT) / ? as occupancy_rate
                FROM hospital_state 
                WHERE sim_id = ? AND CAST(busy_doctors AS FLOAT) / ? > ?
                ORDER BY sim_minutes
            """, (total_doctors, sim_id, total_doctors, HIGH_OCCUPANCY_THRESHOLD)).fetchall()
        
        # Find patients with very long wait times
        long_wait_patients = []
        if 'patient_treated' in existing_tables:
            long_wait_patients = conn.execute("""
                SELECT doctor_id as patient_id, disease, wait_time, start_treatment, doctor_specialty
                FROM patient_treated 
                WHERE sim_id = ? AND wait_time > ?
                ORDER BY wait_time DESC
                LIMIT 50
            """, (sim_id, HIGH_WAIT_TIME_THRESHOLD)).fetchall()
        
        # Get active events during simulation (only if table exists)
        active_events = []
        if 'simulation_events' in existing_tables:
            try:
                active_events = conn.execute("""
                    SELECT event_id, event_type, start_time, end_time, 
                           start_sim_minutes, end_sim_minutes, params
                    FROM simulation_events 
                    WHERE sim_id = ?
                    ORDER BY start_sim_minutes
                """, (sim_id,)).fetchall()
            except sqlite3.OperationalError:
                # Table exists but might have different structure
                active_events = []
        
        # Calculate incident statistics safely
        total_high_wait_periods = len(high_wait_incidents)
        total_high_occupancy_periods = len(high_occupancy_incidents)
        max_waiting_patients = max([row['waiting_patients'] for row in high_wait_incidents]) if high_wait_incidents else 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'high_wait_incidents': [dict(row) for row in high_wait_incidents],
                'high_occupancy_incidents': [dict(row) for row in high_occupancy_incidents],
                'long_wait_patients': [dict(row) for row in long_wait_patients],
                'active_events': [dict(row) for row in active_events],
                'statistics': {
                    'total_high_wait_periods': total_high_wait_periods,
                    'total_high_occupancy_periods': total_high_occupancy_periods,
                    'max_waiting_patients': max_waiting_patients,
                    'total_doctors': total_doctors
                }
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/simulation/<int:sim_id>/realtime')
def api_realtime_data(sim_id: int):
    """Get real-time simulation data for playback."""
    try:
        start_time = float(request.args.get('start_time', 0))
        end_time = float(request.args.get('end_time', start_time + 60))  # Default 1 hour window
        
        conn = get_db_connection()
        
        # Get hospital states in time range
        hospital_states = conn.execute("""
            SELECT * FROM hospital_state 
            WHERE sim_id = ? AND sim_minutes >= ? AND sim_minutes <= ?
            ORDER BY sim_minutes
        """, (sim_id, start_time, end_time)).fetchall()
        
        # Get detailed events in time range (check if table exists)
        detailed_events = []
        try:
            detailed_events = conn.execute("""
                SELECT * FROM detailed_events 
                WHERE sim_id = ? AND sim_minutes >= ? AND sim_minutes <= ?
                ORDER BY sim_minutes
            """, (sim_id, start_time, end_time)).fetchall()
        except sqlite3.OperationalError:
            # Table doesn't exist, use empty list
            detailed_events = []
        
        # Get patient treatments in time range with doctor specialties
        patient_treatments = conn.execute("""
            SELECT * FROM patient_treated 
            WHERE sim_id = ? AND sim_minutes >= ? AND sim_minutes <= ?
            ORDER BY sim_minutes
        """, (sim_id, start_time, end_time)).fetchall()
        
        # Get doctor information with their specialties from recent treatments
        doctors_info = conn.execute("""
            SELECT DISTINCT doctor_id, doctor_specialty,
                   MAX(sim_minutes) as last_activity
            FROM patient_treated 
            WHERE sim_id = ? AND sim_minutes <= ?
            GROUP BY doctor_id, doctor_specialty
            ORDER BY doctor_id
        """, (sim_id, end_time)).fetchall()
        
        # Build doctor status list with actual specialties and current status
        doctors = []
        for doctor in doctors_info:
            # Determine if doctor is currently busy (treated patient in last 30 sim minutes)
            recent_activity = conn.execute("""
                SELECT MAX(sim_minutes) as last_treatment
                FROM patient_treated 
                WHERE sim_id = ? AND doctor_id = ? 
                AND sim_minutes >= ? AND sim_minutes <= ?
            """, (sim_id, doctor['doctor_id'], end_time - 30, end_time)).fetchone()
            
            is_busy = (recent_activity and recent_activity['last_treatment'] and 
                      (end_time - recent_activity['last_treatment']) < 30)
            
            doctors.append({
                'id': doctor['doctor_id'],
                'specialty': doctor['doctor_specialty'],  # Real specialty from database
                'status': 'busy' if is_busy else 'available',
                'last_activity': doctor['last_activity']
            })
        
        # Get simulation events affecting this time period (check if table exists)
        sim_events = []
        try:
            sim_events = conn.execute("""
                SELECT * FROM simulation_events 
                WHERE sim_id = ? AND start_sim_minutes <= ? AND end_sim_minutes >= ?
                ORDER BY start_sim_minutes
            """, (sim_id, end_time, start_time)).fetchall()
        except sqlite3.OperationalError:
            # Table doesn't exist, use empty list
            sim_events = []
        
        # Get total number of doctors for this simulation
        total_doctors = 25  # Default fallback
        try:
            # First try to get from simulations table
            sim_info = conn.execute("SELECT num_doctors FROM simulations WHERE id = ?", (sim_id,)).fetchone()
            if sim_info and sim_info['num_doctors']:
                total_doctors = int(sim_info['num_doctors'])
            else:
                # Fallback: get max doctor_id from patient_treated
                max_doctor = conn.execute("""
                    SELECT MAX(doctor_id) as max_id FROM patient_treated WHERE sim_id = ?
                """, (sim_id,)).fetchone()
                if max_doctor and max_doctor['max_id']:
                    total_doctors = int(max_doctor['max_id'])
        except Exception:
            pass
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'hospital_states': [dict(row) for row in hospital_states],
                'detailed_events': [dict(row) for row in detailed_events],
                'patient_treatments': [dict(row) for row in patient_treatments],
                'simulation_events': [dict(row) for row in sim_events],
                'doctors': doctors,  # Include doctor information with specialties
                'total_doctors': total_doctors,
                'time_range': {
                    'start': start_time,
                    'end': end_time
                }
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/simulation/<int:sim_id>/timerange')
def api_time_range(sim_id: int):
    """Get the time range of available data for a simulation."""
    try:
        conn = get_db_connection()
        
        time_range = conn.execute("""
            SELECT MIN(sim_minutes) as min_time, MAX(sim_minutes) as max_time,
                   MIN(sim_time) as start_date, MAX(sim_time) as end_date
            FROM hospital_state 
            WHERE sim_id = ?
        """, (sim_id,)).fetchone()
        
        conn.close()
        
        if not time_range or time_range['min_time'] is None:
            return jsonify({'success': False, 'error': 'No data found for simulation'}), 404
        
        return jsonify({
            'success': True,
            'data': dict(time_range)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/simulation/<int:sim_id>/predictions')
def api_get_predictions(sim_id):
    """Get danger predictions for a simulation."""
    try:
        predictions = get_danger_predictions(sim_id)
        return jsonify(predictions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ml/train', methods=['POST'])
def api_train_models():
    """Train ML models."""
    try:
        results = train_hospital_models()
        return jsonify({
            'success': True,
            'message': 'Models trained successfully',
            'results': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/simulation/<int:sim_id>/predict-future')
def api_predict_future(sim_id):
    """Get future predictions for different time horizons."""
    try:
        # This would implement more sophisticated time-series prediction
        # For now, return a placeholder response
        return jsonify({
            'simulation_id': sim_id,
            'future_predictions': {
                '1h': {'danger_score': 0.3, 'confidence': 0.8},
                '6h': {'danger_score': 0.4, 'confidence': 0.7},
                '1d': {'danger_score': 0.5, 'confidence': 0.6},
                '1w': {'danger_score': 0.4, 'confidence': 0.5}
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/simulation/<int:sim_id>/trajectories')
def api_trajectories(sim_id):
    """API endpoint for trajectory data."""
    try:
        # Get trajectory results
        trajectory_results = get_trajectory_results(sim_id)
        
        if not trajectory_results:
            return jsonify({
                'trajectories': [],
                'total_trajectories': 0,
                'message': 'No trajectories found for this simulation'
            })
        
        # Group results by trajectory
        trajectories_dict = {}
        for result in trajectory_results:
            traj_id = result['trajectory_id']
            if traj_id not in trajectories_dict:
                trajectories_dict[traj_id] = {
                    'trajectory_id': traj_id,
                    'parameters': result['parameters'],
                    'description': result['description'],
                    'data': []
                }
            trajectories_dict[traj_id]['data'].append({
                'sim_time': result['sim_time'],
                'patients_total': result['patients_total'],
                'patients_treated': result['patients_treated'],
                'busy_doctors': result['busy_doctors'],
                'waiting_patients': result['waiting_patients'],
                'avg_wait_time': result['avg_wait_time']
            })
        
        trajectories = list(trajectories_dict.values())
        
        # Calculate duration
        duration_minutes = 0
        if trajectories and trajectories[0]['data']:
            first_time = min(point['sim_time'] for point in trajectories[0]['data'])
            last_time = max(point['sim_time'] for point in trajectories[0]['data'])
            duration_minutes = last_time - first_time
        
        # Calculate statistics across all trajectories
        statistics = calculate_trajectory_statistics(trajectories)
        
        # Calculate average trajectory
        average_trajectory = calculate_average_trajectory(trajectories)
        
        return jsonify({
            'trajectories': trajectories,
            'total_trajectories': len(trajectories),
            'duration_minutes': duration_minutes,
            'duration_days': duration_minutes / (24 * 60),
            'statistics': statistics,
            'average_trajectory': average_trajectory
        })
        
    except Exception as e:
        print(f"Error getting trajectory data for simulation {sim_id}: {e}")
        return jsonify({'error': str(e)}), 500

def calculate_trajectory_statistics(trajectories):
    """Calculate statistics across all trajectories."""
    if not trajectories:
        return {}
    
    # Get final values for each trajectory
    final_values = {}
    metrics = ['patients_total', 'patients_treated', 'waiting_patients', 'busy_doctors', 'avg_wait_time']
    
    for metric in metrics:
        values = []
        for traj in trajectories:
            if traj['data']:
                final_point = traj['data'][-1]  # Get last data point
                values.append(final_point[metric])
        
        if values:
            final_values[metric] = {
                'mean': float(np.mean(values)),
                'median': float(np.median(values)),
                'std': float(np.std(values)),
                'min': float(np.min(values)),
                'max': float(np.max(values)),
                'p25': float(np.percentile(values, 25)),
                'p75': float(np.percentile(values, 75))
            }
    
    return final_values

def calculate_average_trajectory(trajectories):
    """Calculate the average trajectory across all simulations."""
    if not trajectories:
        return []
    
    # Get all unique time points
    all_times = set()
    for traj in trajectories:
        for point in traj['data']:
            all_times.add(point['sim_time'])
    
    sorted_times = sorted(all_times)
    
    # Calculate averages for each time point
    average_trajectory = []
    metrics = ['patients_total', 'patients_treated', 'waiting_patients', 'busy_doctors', 'avg_wait_time']
    
    for time in sorted_times:
        avg_point = {'sim_time': time}
        
        for metric in metrics:
            values = []
            for traj in trajectories:
                # Find data point for this time
                point = next((p for p in traj['data'] if p['sim_time'] == time), None)
                if point:
                    values.append(point[metric])
            
            if values:
                avg_point[metric] = float(np.mean(values))
            else:
                avg_point[metric] = 0
        
        average_trajectory.append(avg_point)
    
    return average_trajectory