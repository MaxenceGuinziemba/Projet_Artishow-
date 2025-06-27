#!/usr/bin/env python3
"""
Machine learning operations runner.

This script handles training and prediction operations for hospital ML models.
"""

import argparse
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.ml.danger_prediction import train_hospital_models, get_danger_predictions
from src.data.db import get_db_connection
from src.config import DB_PATH


def train_models():
    """Train all ML models."""
    print("Starting ML model training...")
    print("=" * 50)
    
    try:
        results = train_hospital_models()
        
        if "error" in results:
            print(f"Training failed: {results['error']}")
            return False
            
        print("\nTraining Results:")
        print("-" * 30)
        
        for model_name, metrics in results.items():
            print(f"\n{model_name}:")
            for metric, value in metrics.items():
                if isinstance(value, float):
                    print(f"  {metric}: {value:.3f}")
                else:
                    print(f"  {metric}: {value}")
        
        print("\n✅ All models trained successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Training failed: {e}")
        return False


def generate_predictions(simulation_id: int):
    """Generate predictions for a specific simulation."""
    print(f"Generating predictions for simulation {simulation_id}...")
    print("=" * 50)
    
    try:
        predictions = get_danger_predictions(simulation_id)
        
        if "error" in predictions:
            print(f"Prediction failed: {predictions['error']}")
            return False
        
        print(f"\nPredictions for Simulation {simulation_id}")
        print("-" * 40)
        
        print(f"Overall Danger Score: {predictions['overall_danger_score']:.2%}")
        print(f"Current Time: {predictions['current_time']}")
        
        print("\nCurrent Metrics:")
        for metric, value in predictions['current_metrics'].items():
            print(f"  {metric}: {value}")
        
        print("\nDanger Predictions:")
        for model_name, pred in predictions['individual_predictions'].items():
            if 'danger_probability' in pred:
                prob = pred['danger_probability']
                status = "🔴 DANGER" if pred['is_danger'] else "🟢 SAFE"
                print(f"  {model_name}: {prob:.2%} {status}")
            elif 'predicted_value' in pred:
                print(f"  {model_name}: {pred['predicted_value']:.2f}")
        
        print("\nTime Horizon Predictions:")
        for window, pred in predictions['time_horizon_predictions'].items():
            risk_emoji = "🔴" if pred['risk_level'] == 'High' else "🟡" if pred['risk_level'] == 'Medium' else "🟢"
            print(f"  {pred['label']}: {pred['danger_score']:.2%} {risk_emoji} {pred['risk_level']}")
        
        print("\n✅ Predictions generated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Prediction failed: {e}")
        return False


def list_simulations():
    """List available simulations."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT simulation_id, 
               MIN(datetime) as start_time,
               MAX(datetime) as end_time,
               COUNT(*) as data_points
        FROM hospital_state 
        GROUP BY simulation_id 
        ORDER BY simulation_id
        """)
        
        sims = cursor.fetchall()
        conn.close()
        
        if not sims:
            print("No simulations found in database.")
            return
        
        print("Available Simulations:")
        print("-" * 50)
        for sim_id, start, end, points in sims:
            print(f"  Simulation {sim_id}: {start} to {end} ({points} data points)")
            
    except Exception as e:
        print(f"Error listing simulations: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Hospital ML Operations")
    
    parser.add_argument("--train", action="store_true", help="Train ML models")
    parser.add_argument("--predict", type=int, metavar="SIM_ID", help="Generate predictions for simulation")
    parser.add_argument("--list", action="store_true", help="List available simulations")
    
    args = parser.parse_args()
    
    if args.list:
        list_simulations()
    elif args.train:
        success = train_models()
        sys.exit(0 if success else 1)
    elif args.predict is not None:
        success = generate_predictions(args.predict)
        sys.exit(0 if success else 1)
    else:
        print("Hospital ML Operations")
        print("=" * 30)
        print("Usage:")
        print("  python src/run_ml.py --train                    # Train models")
        print("  python src/run_ml.py --predict SIM_ID          # Generate predictions")
        print("  python src/run_ml.py --list                    # List simulations")
        print("\nExamples:")
        print("  python src/run_ml.py --train")
        print("  python src/run_ml.py --predict 1")


if __name__ == "__main__":
    main()