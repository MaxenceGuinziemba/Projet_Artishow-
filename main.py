#!/usr/bin/env python3
"""
Main entry point for the hospital simulation system.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

# Ensure we can import from src
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def main():
    """Main entry point for the hospital simulation system."""
    # Apply Linux-specific optimizations
    import sys
    import os
    if sys.platform.startswith('linux'):
        os.environ['PYTHONUNBUFFERED'] = '1'
        os.environ['PYTHONHASHSEED'] = '0'
    
    parser = argparse.ArgumentParser(description="Hospital Simulation System with AI Predictions")
    
    # Mode selection
    parser.add_argument("--simulation", action="store_true", help="Run the simulation")
    parser.add_argument("--dashboard", action="store_true", help="Run the dashboard")
    parser.add_argument("--ml", action="store_true", help="Run ML operations")
    parser.add_argument("--all", action="store_true", help="Run all components")
    parser.add_argument("--docs", action="store_true", help="Generate documentation")
    
    # Dashboard options
    parser.add_argument("--port", type=int, help="Dashboard port (default: 8080)")
    parser.add_argument("--host", type=str, help="Dashboard host (default: localhost)")
    parser.add_argument("--debug", action="store_true", help="Run dashboard in debug mode")
    
    # Simulation options
    parser.add_argument("--resume", action="store_true", help="Resume from last saved state")
    parser.add_argument("--sim-id", type=int, help="Specific simulation ID to resume")
    parser.add_argument("--doctors", type=int, help="Number of doctors")
    parser.add_argument("--rate", type=float, help="Patient arrival rate")
    parser.add_argument("--minutes", type=int, help="Simulation duration in minutes")
    parser.add_argument("--duration", type=int, help="Simulation duration in days")
    parser.add_argument("--clean", action="store_true", help="Clean database before starting")
    
    # ML options
    parser.add_argument("--train", action="store_true", help="Train ML models")
    parser.add_argument("--predict", action="store_true", help="Generate predictions")
    parser.add_argument("--days", type=int, help="Days to predict")
    parser.add_argument("--list", action="store_true", help="List available simulations")
    
    args = parser.parse_args()
    
    # Handle documentation generation
    if args.docs:
        cmd = [sys.executable, "src/utils/generate_docs.py"]
        subprocess.run(cmd)
        return
    
    # Handle dashboard launch
    if args.dashboard and not args.all:
        cmd = [sys.executable, "src/run_dashboard.py"]
        if args.port:
            import os
            os.environ['DASHBOARD_PORT'] = str(args.port)
        if args.host:
            os.environ['DASHBOARD_HOST'] = args.host
        if args.debug:
            os.environ['DASHBOARD_DEBUG'] = '1'
        subprocess.run(cmd)
        return
    
    # Handle simulation
    if args.simulation and not args.all:
        cmd = [sys.executable, "src/run_simulation.py"]
        if args.resume:
            cmd.append("--resume")
        if args.sim_id:
            cmd.append(f"--sim-id={args.sim_id}")
        if args.doctors:
            cmd.append(f"--doctors={args.doctors}")
        if args.rate:
            cmd.append(f"--rate={args.rate}")
        if args.minutes:
            cmd.append(f"--minutes={args.minutes}")
        if args.duration:
            cmd.append(f"--duration={args.duration}")
        if args.clean:
            cmd.append("--clean")
        subprocess.run(cmd)
        return
    
    # Handle ML operations
    if args.ml and not args.all:
        cmd = [sys.executable, "src/run_ml.py"]
        if args.train:
            cmd.append("--train")
        if args.predict:
            if args.sim_id:
                cmd.append(f"--predict={args.sim_id}")
            else:
                cmd.append("--predict=1")  # Default to simulation 1
        if args.list:
            cmd.append("--list")
        if args.days:
            cmd.append(f"--days={args.days}")
        subprocess.run(cmd)
        return
    
    # Handle running all components
    if args.all:
        print("Starting all components...")
        print("=" * 60)
        
        # Start simulation in background
        sim_cmd = [sys.executable, "src/run_simulation.py"]
        if args.doctors:
            sim_cmd.append(f"--doctors={args.doctors}")
        if args.rate:
            sim_cmd.append(f"--rate={args.rate}")
        if args.duration:
            sim_cmd.append(f"--duration={args.duration}")
        
        print("1. Starting simulation...")
        sim_proc = subprocess.Popen(sim_cmd)
        time.sleep(3)  # Give simulation time to start
        
        # Start ML training in background
        print("2. Training ML models...")
        ml_proc = subprocess.Popen([sys.executable, "src/run_ml.py", "--train"])
        time.sleep(2)
        
        # Start dashboard
        print("3. Starting dashboard...")
        dash_cmd = [sys.executable, "src/run_dashboard.py"]
        if args.port:
            import os
            os.environ['DASHBOARD_PORT'] = str(args.port)
        
        try:
            subprocess.run(dash_cmd)
        except KeyboardInterrupt:
            print("\nShutting down all components...")
            sim_proc.terminate()
            ml_proc.terminate()
        return
    
    # If no options specified, show help and interactive mode
    print("Hospital Simulation & AI Prediction System")
    print("=" * 60)
    print("Comprehensive hospital simulation with machine learning predictions")
    print()
    print("Usage examples:")
    print("  python main.py --dashboard")
    print("  python main.py --simulation --doctors=30 --rate=20")
    print("  python main.py --ml --train")
    print("  python main.py --ml --predict --sim-id=1")
    print("  python main.py --all --doctors=25 --rate=15")
    print()
    print("For trajectory generation:")
    print("  python -m src.simulation.sim_utils trajectories 1 --num=50 --days=30")
    print("  python -m src.simulation.sim_utils analyze 1")
    print()
    print("For detailed help: python main.py --help")
    print()
    
    # Interactive mode
    print("Interactive Mode")
    print("What would you like to run?")
    print("1. Simulation only")
    print("2. Dashboard only") 
    print("3. ML operations only")
    print("4. All components")
    print("5. Generate documentation")
    print("6. Test trajectory generation")
    print("7. Exit")
    
    try:
        choice = input("\nEnter your choice (1-7): ").strip()
    except KeyboardInterrupt:
        print("\nExiting.")
        return
    
    if choice == "1":
        cmd = [sys.executable, "src/run_simulation.py"]
        subprocess.run(cmd)
    elif choice == "2":
        cmd = [sys.executable, "src/run_dashboard.py"]
        subprocess.run(cmd)
    elif choice == "3":
        cmd = [sys.executable, "src/run_ml.py", "--train", "--predict=1"]
        subprocess.run(cmd)
    elif choice == "4":
        print("\nStarting all components...")
        # Start simulation in background
        sim_proc = subprocess.Popen([sys.executable, "src/run_simulation.py"])
        time.sleep(2)  # Give simulation time to start
        # Start dashboard
        dash_proc = subprocess.Popen([sys.executable, "src/run_dashboard.py"])
        try:
            # Wait for processes
            sim_proc.wait()
            dash_proc.wait()
        except KeyboardInterrupt:
            print("\nShutting down...")
            sim_proc.terminate()
            dash_proc.terminate()
    elif choice == "5":
        cmd = [sys.executable, "src/utils/generate_docs.py"]
        subprocess.run(cmd)
    elif choice == "6":
        cmd = [sys.executable, "test_trajectories.py"]
        subprocess.run(cmd)
    else:
        print("Goodbye!")


if __name__ == "__main__":
    main()
