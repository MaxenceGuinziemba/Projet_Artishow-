#!/usr/bin/env python3
"""
Main script to run the hospital simulation.

This script initializes and runs the hospital simulation with the specified parameters.

Usage examples:
  python src/run_simulation.py --doctors=30 --rate=20 --minutes=1440
  python src/run_simulation.py --resume --minutes=720
  python src/run_simulation.py --clean --doctors=25 --rate=15

For trajectory generation:
  python -m src.simulation.sim_utils trajectories 1 --num=50 --days=30
  python -m src.simulation.sim_utils analyze 1
"""

import simpy
import threading
import sys
import os
import time as pytime
import signal
from datetime import timedelta
from pathlib import Path

# Add project root to Python path so 'src' can be imported
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.data.db import init_database
from src.simulation.hospital_sim import HospitalSim
from src.config import DEFAULT_NUM_DOCTORS, DEFAULT_ARRIVAL_RATE, DEFAULT_SIM_MINUTES, DB_PATH


def main() -> None:
    """Main entry point for the hospital simulation.
    
    Initializes the simulation environment, handles command-line arguments,
    and sets up simulation monitoring and graceful shutdown.
    """
    # Parse command line arguments
    resume = "--resume" in sys.argv
    clean = "--clean" in sys.argv
    resume_sim_id = None
    additional_minutes = None
    
    # Get custom parameters if provided
    num_doctors = DEFAULT_NUM_DOCTORS
    arrival_rate = DEFAULT_ARRIVAL_RATE
    sim_minutes = DEFAULT_SIM_MINUTES
    
    # Override with command line arguments if provided
    for arg in sys.argv:
        if arg.startswith("--doctors="):
            try:
                num_doctors = int(arg.split("=")[1])
            except:
                print(f"Invalid doctors value: {arg}")
        elif arg.startswith("--rate="):
            try:
                arrival_rate = float(arg.split("=")[1])
            except:
                print(f"Invalid arrival rate value: {arg}")
        elif arg.startswith("--minutes="):
            try:
                minutes_value = int(arg.split("=")[1])
                if resume:
                    additional_minutes = minutes_value
                else:
                    sim_minutes = minutes_value
            except:
                print(f"Invalid minutes value: {arg}")
        elif arg.startswith("--sim-id="):
            try:
                resume_sim_id = int(arg.split("=")[1])
                resume = True  # Enable resume if sim_id is provided
            except:
                print(f"Invalid simulation ID value: {arg}")
    
    # Clean database if requested
    if clean:
        if os.path.exists(DB_PATH):
            try:
                print("Cleaning previous simulation data...")
                os.remove(DB_PATH)
                print("Database cleaned.")
            except Exception as e:
                print(f"Error cleaning database: {e}")
    
    # Initialize the database
    init_database()
    
    # If resuming, show available simulations if no ID specified
    if resume and resume_sim_id is None:
        from src.data.db import get_all_simulation_ids
        simulations = get_all_simulation_ids()
        if simulations:
            print("Available simulations:")
            print("ID | Start Time           | Doctors | Arrival Rate | Description")
            print("---|---------------------|---------|--------------|-------------")
            for sim_info in simulations[:10]:  # Show last 10
                print(f"{sim_info['id']:2d} | {sim_info['start_time'][:19]} | {sim_info['num_doctors']:7d} | {sim_info['arrival_rate']:12.1f} | {sim_info['description']}")
            print(f"Will resume latest simulation (ID: {simulations[0]['id']})")
        else:
            print("No previous simulations found. Starting new simulation.")
            resume = False
    
    # Initialize simulation
    env = simpy.Environment()
    sim = HospitalSim(env, num_doctors=num_doctors, arrival_rate=arrival_rate, 
                      resume=resume, resume_sim_id=resume_sim_id)
    stop_flag = [False]
    
    # Calculate target time for progress display
    if resume:
        if additional_minutes is not None:
            target_time = sim.env.now + additional_minutes
            progress_total = additional_minutes
            progress_offset = sim.env.now
        else:
            target_time = 525600  # 1 year
            progress_total = 525600
            progress_offset = 0
    else:
        target_time = sim_minutes
        progress_total = sim_minutes
        progress_offset = 0
    
    # Set up a progress display thread
    def timer():
        while not stop_flag[0]:
            current_date = sim.start_date + timedelta(minutes=sim.env.now)
            date_str = current_date.strftime("%Y-%m-%d %H:%M")
            
            if resume and additional_minutes is not None:
                # Show progress for additional minutes
                progress = ((sim.env.now - progress_offset) / progress_total) * 100
                sys.stdout.write(f"\rSimulation date: {date_str} [{int(sim.env.now - progress_offset)}/{additional_minutes} additional minutes - {progress:.1f}%]")
            elif resume:
                # Show progress toward 1 year
                percentage = (sim.env.now / 525600) * 100
                sys.stdout.write(f"\rSimulation date: {date_str} [{int(sim.env.now)}/525600 minutes - {percentage:.1f}%]")
            else:
                # Show progress for new simulation
                percentage = (sim.env.now / sim_minutes) * 100
                sys.stdout.write(f"\rSimulation date: {date_str} [{int(sim.env.now)}/{sim_minutes} minutes - {percentage:.1f}%]")
            
            sys.stdout.flush()
            pytime.sleep(0.2)
        print("\nSimulation complete.")

    # Set up a flag for clean shutdown
    running = [True]
    
    # Register a signal handler to save state on exit
    def signal_handler(sig, frame):
        print("\nInterrupted. Saving simulation state before exit...")
        sim.save_simulation_state()
        stop_flag[0] = True
        running[0] = False
        # No need to call sys.exit() - we'll exit cleanly
        
    # Register the handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)

    t = threading.Thread(target=timer)
    t.start()
    
    # Start a second thread that runs the simulation
    # This allows the main thread to remain responsive to signals
    def run_simulation():
        try:
            # Use the new run method with proper parameter handling
            if resume and additional_minutes is not None:
                # Resume with additional minutes
                print(f"Running simulation for {additional_minutes} additional minutes from current position")
                sim.run(additional_minutes=additional_minutes)
            elif resume:
                # Resume until 1 year default
                print(f"Resuming simulation until 1 year mark")
                sim.run()  # Will use default 1 year and resume logic
            else:
                # New simulation
                print(f"Running new simulation for {sim_minutes} minutes")
                sim.run(sim_minutes=sim_minutes)
            
            # Final state save at completion
            if running[0]:  # Only save if not already saved by signal handler
                sim.save_simulation_state()
                print(f"\nSimulation completed successfully.")
                print(f"Final state: {sim.patients_total} total patients, {sim.patients_treated} treated")
        except Exception as e:
            print(f"\nError in simulation: {e}")
        finally:
            stop_flag[0] = True
            running[0] = False
    
    sim_thread = threading.Thread(target=run_simulation)
    sim_thread.daemon = True  # Allow the program to exit even if this thread is running
    sim_thread.start()
    
    # Keep the main thread alive until the simulation is done or interrupted
    try:
        while running[0] and sim_thread.is_alive():
            sim_thread.join(0.1)  # Check every 0.1 seconds if we should exit
    except KeyboardInterrupt:
        # This is a fallback in case the signal handler doesn't work
        print("\nInterrupted. Saving simulation state before exit...")
        sim.save_simulation_state()
        running[0] = False
        stop_flag[0] = True
    finally:
        # Make sure the timer thread exits
        t.join(timeout=1)


if __name__ == "__main__":
    main()