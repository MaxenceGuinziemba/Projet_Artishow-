"""
Hospital Danger Prediction System

This module implements machine learning models to predict various types of
"danger" situations in hospital operations across different time scales.

Danger types:
- Patient Overload: Too many patients arriving relative to capacity
- Long Wait Times: Average wait times exceeding acceptable thresholds
- Doctor Shortage: Insufficient doctors for patient load
- System Stress: Combined metrics indicating overall system strain

Time scales:
- Immediate (next 15-60 minutes)
- Short-term (next 2-6 hours) 
- Medium-term (next 1-3 days)
- Long-term (next 1-4 weeks)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional, Union
from datetime import datetime, timedelta
import sqlite3
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, mean_absolute_error, r2_score
import joblib
import warnings
warnings.filterwarnings('ignore')

from src.data.db import get_db_connection
from src.config import DB_PATH, SPECIALTIES

class HospitalDangerPredictor:
    """
    Main class for predicting hospital danger situations.
    
    This predictor combines multiple specialized models to assess
    different types of dangers across various time horizons.
    """
    
    def __init__(self):
        """Initialize the danger prediction system."""
        self.models = {}
        self.scalers = {}
        self.feature_columns = {}
        self.danger_thresholds = {
            'high_wait_time': 60,  # minutes
            'patient_overload_ratio': 1.2,  # patients per doctor
            'doctor_utilization': 0.9,  # fraction of doctors busy
            'system_stress_score': 0.8  # combined stress metric
        }
        self.time_windows = {
            'immediate': {'minutes': 60, 'label': '1 hour'},
            'short_term': {'minutes': 360, 'label': '6 hours'},
            'medium_term': {'minutes': 1440, 'label': '1 day'},
            'long_term': {'minutes': 10080, 'label': '1 week'}
        }
        
    def load_training_data(self, db_path: str = DB_PATH) -> pd.DataFrame:
        """
        Load and prepare training data from all simulations.

        Args:
            db_path: Path to database

        Returns:
            Combined training data from all simulations
        """
        conn = get_db_connection()

        # Load patient data with hospital state information
        query = """
        WITH hospital_metrics AS (
            SELECT 
                h.sim_minutes,
                h.sim_id,
                h.patients_total,
                h.waiting_patients as patients_waiting,
                h.patients_treated,
                h.busy_doctors as doctors_busy,
                (h.patients_total - h.waiting_patients - h.patients_treated) as doctors_free,
                h.sim_time as state_time,
                h.busy_doctors + (h.patients_total - h.waiting_patients - h.patients_treated) as total_doctors,
                CASE 
                    WHEN h.busy_doctors + (h.patients_total - h.waiting_patients - h.patients_treated) > 0 
                    THEN CAST(h.patients_total AS FLOAT) / (h.busy_doctors + (h.patients_total - h.waiting_patients - h.patients_treated))
                    ELSE 0 
                END as patient_doctor_ratio,
                CASE 
                    WHEN h.busy_doctors + (h.patients_total - h.waiting_patients - h.patients_treated) > 0
                    THEN CAST(h.busy_doctors AS FLOAT) / (h.busy_doctors + (h.patients_total - h.waiting_patients - h.patients_treated))
                    ELSE 0
                END as doctor_utilization
            FROM hospital_state h
        ),
        patient_metrics AS (
            SELECT 
                p.sim_minutes,
                p.sim_id,
                AVG(p.wait_time) as avg_wait_time,
                MAX(p.wait_time) as max_wait_time,
                COUNT(*) as patients_in_period,
                AVG(p.treatment_time) as avg_treatment_time
            FROM patient_treated p
            GROUP BY p.sim_id, p.sim_minutes
        )
        SELECT 
            hm.*,
            COALESCE(pm.avg_wait_time, 0) as avg_wait_time,
            COALESCE(pm.max_wait_time, 0) as max_wait_time,
            COALESCE(pm.patients_in_period, 0) as patients_treated_period,
            COALESCE(pm.avg_treatment_time, 0) as avg_treatment_time
        FROM hospital_metrics hm
        LEFT JOIN patient_metrics pm ON hm.sim_id = pm.sim_id 
                                      AND hm.sim_minutes = pm.sim_minutes
        ORDER BY hm.sim_id, hm.sim_minutes
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            print("No training data available")
            return df
            
        # Convert datetime
        df['state_time'] = pd.to_datetime(df['state_time'])
        
        # Extract time-based features
        df['hour'] = df['state_time'].dt.hour
        df['day_of_week'] = df['state_time'].dt.dayofweek
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        df['is_night'] = ((df['hour'] >= 22) | (df['hour'] <= 6)).astype(int)
        df['is_peak_hours'] = ((df['hour'] >= 8) & (df['hour'] <= 18)).astype(int)
        
        # Calculate danger indicators
        df['is_high_wait'] = (df['avg_wait_time'] > self.danger_thresholds['high_wait_time']).astype(int)
        df['is_overloaded'] = (df['patient_doctor_ratio'] > self.danger_thresholds['patient_overload_ratio']).astype(int)
        df['is_understaffed'] = (df['doctor_utilization'] > self.danger_thresholds['doctor_utilization']).astype(int)
        
        # Calculate system stress score (0-1)
        df['system_stress'] = (
            0.3 * np.clip(df['patient_doctor_ratio'] / 2.0, 0, 1) +
            0.3 * np.clip(df['doctor_utilization'], 0, 1) +
            0.2 * np.clip(df['avg_wait_time'] / 120.0, 0, 1) +
            0.2 * np.clip(df['patients_waiting'] / 50.0, 0, 1)
        )
        df['is_high_stress'] = (df['system_stress'] > self.danger_thresholds['system_stress_score']).astype(int)
        
        # Calculate trends (rate of change)
        for sim_id in df['sim_id'].unique():
            sim_mask = df['sim_id'] == sim_id
            sim_data = df[sim_mask].sort_values('sim_minutes')
            
            # Calculate trends over different windows
            for window in [60, 180, 360]:  # 1h, 3h, 6h windows
                col_name = f'patient_trend_{window}m'
                df.loc[sim_mask, col_name] = sim_data['patients_total'].rolling(
                    window=min(window//5, len(sim_data)), min_periods=1
                ).apply(lambda x: (x.iloc[-1] - x.iloc[0]) / len(x) if len(x) > 1 else 0)
                
                wait_col = f'wait_trend_{window}m'
                df.loc[sim_mask, wait_col] = sim_data['avg_wait_time'].rolling(
                    window=min(window//5, len(sim_data)), min_periods=1
                ).apply(lambda x: (x.iloc[-1] - x.iloc[0]) / len(x) if len(x) > 1 else 0)
        
        # Fill NaN values
        df = df.fillna(0)
        
        print(f"Loaded {len(df)} training samples from {df['sim_id'].nunique()} simulations")
        return df
        
    def prepare_features(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """
        Define feature sets for different prediction tasks.
        
        Args:
            df: Training dataframe
            
        Returns:
            Dictionary mapping task names to feature lists
        """
        base_features = [
            'patients_total', 'patients_waiting', 'patients_treated',
            'doctors_busy', 'doctors_free', 'total_doctors',
            'patient_doctor_ratio', 'doctor_utilization',
            'avg_wait_time', 'max_wait_time', 'avg_treatment_time',
            'hour', 'day_of_week', 'is_weekend', 'is_night', 'is_peak_hours'
        ]
        
        trend_features = [col for col in df.columns if 'trend' in col]
        
        feature_sets = {
            'wait_time_danger': base_features + trend_features,
            'overload_danger': base_features + trend_features,
            'staffing_danger': base_features + trend_features,
            'system_stress': base_features + trend_features,
            'wait_time_regression': base_features + trend_features,
            'patient_count_regression': base_features + trend_features
        }
        
        return feature_sets
        
    def train_models(self, db_path: str = DB_PATH) -> Dict[str, Any]:
        """
        Train all prediction models.
        
        Args:
            db_path: Path to database
            
        Returns:
            Training results and metrics
        """
        print("Loading training data...")
        df = self.load_training_data(db_path)
        
        if df.empty:
            return {"error": "No training data available"}
            
        feature_sets = self.prepare_features(df)
        results = {}
        
        # Classification tasks
        classification_tasks = {
            'wait_time_danger': 'is_high_wait',
            'overload_danger': 'is_overloaded', 
            'staffing_danger': 'is_understaffed',
            'system_stress': 'is_high_stress'
        }
        
        print("Training classification models...")
        for task_name, target_col in classification_tasks.items():
            print(f"  Training {task_name}...")
            
            features = feature_sets[task_name]
            available_features = [f for f in features if f in df.columns]
            
            X = df[available_features]
            y = df[target_col]
            
            # Handle class imbalance
            if y.sum() < len(y) * 0.1:  # Less than 10% positive cases
                print(f"    Warning: Low positive rate for {task_name}: {y.mean():.2%}")
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, stratify=y, random_state=42
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train models
            rf_model = RandomForestClassifier(
                n_estimators=100, max_depth=10, random_state=42,
                class_weight='balanced'
            )
            rf_model.fit(X_train_scaled, y_train)
            
            # Evaluate
            train_score = rf_model.score(X_train_scaled, y_train)
            test_score = rf_model.score(X_test_scaled, y_test)
            cv_scores = cross_val_score(rf_model, X_train_scaled, y_train, cv=5)
            
            # Store model and results
            self.models[task_name] = rf_model
            self.scalers[task_name] = scaler
            self.feature_columns[task_name] = available_features
            
            results[task_name] = {
                'train_score': train_score,
                'test_score': test_score,
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std(),
                'feature_count': len(available_features),
                'positive_rate': y.mean()
            }
            
            print(f"    Test accuracy: {test_score:.3f} (CV: {cv_scores.mean():.3f}±{cv_scores.std():.3f})")
        
        # Regression tasks
        regression_tasks = {
            'wait_time_regression': 'avg_wait_time',
            'patient_count_regression': 'patients_total'
        }
        
        print("Training regression models...")
        for task_name, target_col in regression_tasks.items():
            print(f"  Training {task_name}...")
            
            features = feature_sets[task_name]
            available_features = [f for f in features if f in df.columns and f != target_col]
            
            X = df[available_features]
            y = df[target_col]
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model
            gb_model = GradientBoostingRegressor(
                n_estimators=100, max_depth=6, random_state=42
            )
            gb_model.fit(X_train_scaled, y_train)
            
            # Evaluate
            train_score = gb_model.score(X_train_scaled, y_train)
            test_score = gb_model.score(X_test_scaled, y_test)
            y_pred = gb_model.predict(X_test_scaled)
            mae = mean_absolute_error(y_test, y_pred)
            
            # Store model and results
            self.models[task_name] = gb_model
            self.scalers[task_name] = scaler  
            self.feature_columns[task_name] = available_features
            
            results[task_name] = {
                'train_r2': train_score,
                'test_r2': test_score,
                'mae': mae,
                'feature_count': len(available_features)
            }
            
            print(f"    Test R²: {test_score:.3f}, MAE: {mae:.2f}")
        
        print(f"Training completed. {len(self.models)} models trained.")
        return results
    
    def predict_dangers(self, sim_id: int, db_path: str = DB_PATH) -> Dict[str, Any]:
        """
        Generate danger predictions for a specific simulation.
        
        Args:
            sim_id: ID of simulation to predict for
            db_path: Database path
            
        Returns:
            Comprehensive danger predictions
        """
        if not self.models:
            return {"error": "Models not trained. Call train_models() first."}
        
        # Get latest state for the simulation
        conn = sqlite3.connect(db_path)
        
        # Get current state
        current_state_query = """
        SELECT * FROM hospital_state 
        WHERE sim_id = ? 
        ORDER BY sim_minutes DESC 
        LIMIT 1
        """
        
        current_df = pd.read_sql_query(current_state_query, conn, params=[sim_id])
        
        if current_df.empty:
            conn.close()
            return {"error": f"No data found for simulation {sim_id}"}
        
        # Get recent patient data for context
        recent_patients_query = """
        SELECT AVG(wait_time) as avg_wait_time,
               MAX(wait_time) as max_wait_time,
               AVG(treatment_time) as avg_treatment_time,
               COUNT(*) as patients_in_period
        FROM patient_treated 
        WHERE sim_id = ? 
        AND sim_minutes >= ? 
        """
        
        recent_minutes = current_df['sim_minutes'].iloc[0] - 60  # Last hour
        patient_df = pd.read_sql_query(
            recent_patients_query, conn, 
            params=[sim_id, recent_minutes]
        )
        
        conn.close()
        
        # Prepare features
        feature_data = current_df.copy()
        feature_data['avg_wait_time'] = patient_df['avg_wait_time'].fillna(0).iloc[0]
        feature_data['max_wait_time'] = patient_df['max_wait_time'].fillna(0).iloc[0]
        feature_data['avg_treatment_time'] = patient_df['avg_treatment_time'].fillna(0).iloc[0]
        
        # Add derived features - map from DB schema to ML features
        feature_data['doctors_busy'] = feature_data['busy_doctors']
        feature_data['patients_waiting'] = feature_data['waiting_patients']
        feature_data['doctors_free'] = feature_data['patients_total'] - feature_data['waiting_patients'] - feature_data['patients_treated']
        feature_data['total_doctors'] = feature_data['busy_doctors'] + feature_data['doctors_free']
        feature_data['patient_doctor_ratio'] = np.where(
            feature_data['total_doctors'] > 0,
            feature_data['patients_total'] / feature_data['total_doctors'],
            0
        )
        feature_data['doctor_utilization'] = np.where(
            feature_data['total_doctors'] > 0,
            feature_data['busy_doctors'] / feature_data['total_doctors'],
            0
        )
        
        # Add time features
        current_time = pd.to_datetime(feature_data['sim_time'].iloc[0])
        feature_data['hour'] = current_time.hour
        feature_data['day_of_week'] = current_time.dayofweek
        feature_data['is_weekend'] = int(current_time.dayofweek >= 5)
        feature_data['is_night'] = int((current_time.hour >= 22) or (current_time.hour <= 6))
        feature_data['is_peak_hours'] = int((current_time.hour >= 8) and (current_time.hour <= 18))
        
        # Add placeholder trend features (would need historical data for real trends)
        for window in [60, 180, 360]:
            feature_data[f'patient_trend_{window}m'] = 0
            feature_data[f'wait_trend_{window}m'] = 0
        
        predictions = {}
        
        # Generate predictions for each model
        for model_name, model in self.models.items():
            try:
                features = self.feature_columns[model_name]
                available_features = [f for f in features if f in feature_data.columns]
                
                if len(available_features) == 0:
                    continue
                    
                X = feature_data[available_features]
                X_scaled = self.scalers[model_name].transform(X)
                
                if 'regression' in model_name:
                    pred_value = model.predict(X_scaled)[0]
                    # Map regression target properly
                    if 'wait_time' in model_name:
                        current_val = float(feature_data['avg_wait_time'].iloc[0])
                    elif 'patient_count' in model_name:
                        current_val = float(feature_data['patients_total'].iloc[0])
                    else:
                        current_val = 0.0
                        
                    predictions[model_name] = {
                        'predicted_value': float(pred_value),
                        'current_value': current_val
                    }
                else:
                    pred_proba = model.predict_proba(X_scaled)[0]
                    predictions[model_name] = {
                        'danger_probability': float(pred_proba[1]) if len(pred_proba) > 1 else 0.0,
                        'is_danger': bool(pred_proba[1] > 0.5) if len(pred_proba) > 1 else False
                    }
                    
            except Exception as e:
                print(f"Error predicting {model_name}: {e}")
                predictions[model_name] = {'error': str(e)}
        
        # Calculate overall danger score
        danger_scores = []
        for model_name, pred in predictions.items():
            if 'danger_probability' in pred:
                danger_scores.append(pred['danger_probability'])
        
        overall_danger = np.mean(danger_scores) if danger_scores else 0.0
        
        # Generate time-horizon predictions (simplified)
        time_predictions = {}
        for window_name, window_info in self.time_windows.items():
            time_predictions[window_name] = {
                'label': window_info['label'],
                'danger_score': overall_danger * (1 + np.random.normal(0, 0.1)),  # Add some variation
                'risk_level': 'High' if overall_danger > 0.7 else 'Medium' if overall_danger > 0.4 else 'Low'
            }
        
        return {
            'sim_id': sim_id,
            'current_time': current_time.isoformat(),
            'overall_danger_score': float(overall_danger),
            'individual_predictions': predictions,
            'time_horizon_predictions': time_predictions,
            'current_metrics': {
                'patients_total': int(feature_data['patients_total'].iloc[0]),
                'patients_waiting': int(feature_data['waiting_patients'].iloc[0]),
                'doctors_busy': int(feature_data['busy_doctors'].iloc[0]),
                'doctors_free': int(feature_data['doctors_free'].iloc[0]),
                'avg_wait_time': float(feature_data['avg_wait_time'].iloc[0]),
                'doctor_utilization': float(feature_data['doctor_utilization'].iloc[0])
            }
        }
    
    def save_models(self, filepath: str = "models/hospital_danger_models.joblib") -> None:
        """Save trained models to file."""
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        model_data = {
            'models': self.models,
            'scalers': self.scalers,
            'feature_columns': self.feature_columns,
            'danger_thresholds': self.danger_thresholds,
            'time_windows': self.time_windows
        }
        joblib.dump(model_data, filepath)
        print(f"Models saved to {filepath}")
    
    def load_models(self, filepath: str = "models/hospital_danger_models.joblib") -> None:
        """Load trained models from file."""
        try:
            model_data = joblib.load(filepath)
            self.models = model_data['models']
            self.scalers = model_data['scalers']
            self.feature_columns = model_data['feature_columns']
            self.danger_thresholds = model_data['danger_thresholds']
            self.time_windows = model_data['time_windows']
            print(f"Models loaded from {filepath}")
        except FileNotFoundError:
            print(f"Model file {filepath} not found. Train models first.")
        except Exception as e:
            print(f"Error loading models: {e}")

# Convenience functions for the dashboard
def train_hospital_models(db_path: str = DB_PATH) -> Dict[str, Any]:
    """Train hospital danger prediction models."""
    predictor = HospitalDangerPredictor()
    results = predictor.train_models(db_path)
    predictor.save_models()
    return results

def get_danger_predictions(sim_id: int, db_path: str = DB_PATH) -> Dict[str, Any]:
    """Get danger predictions for a simulation."""
    predictor = HospitalDangerPredictor()
    predictor.load_models()
    return predictor.predict_dangers(sim_id, db_path)
