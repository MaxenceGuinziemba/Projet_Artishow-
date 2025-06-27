#!/usr/bin/env python3
"""
Dashboard launcher script.

This script launches the hospital simulation dashboard web application.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path (parent of src directory)
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def main():
    """Launch the dashboard."""
    try:
        from src.visualizations.dashboard import app
        from src.config import DASHBOARD_PORT, DASHBOARD_DEBUG
        
        # Check for port override from environment
        port = int(os.environ.get('DASHBOARD_PORT', DASHBOARD_PORT))
        host = os.environ.get('DASHBOARD_HOST', '0.0.0.0')
        debug = os.environ.get('DASHBOARD_DEBUG', '0') == '1'
        
        print("=" * 60)
        print("HOSPITAL SIMULATION DASHBOARD")
        print("=" * 60)
        print(f"Starting dashboard server...")
        print(f"Dashboard URL: http://localhost:{port}")
        print(f"Debug mode: {'ON' if debug else 'OFF'}")
        print("=" * 60)
        print("\nPress Ctrl+C to stop the server")
        print()
        
        app.run(
            host=host, 
            port=port, 
            debug=debug
        )
        
    except ImportError as e:
        print(f"Error importing dashboard modules: {e}")
        print("Make sure all dependencies are installed:")
        print("  pip install flask")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting dashboard: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()