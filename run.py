#!/usr/bin/env python3
"""
Run the Streamlit frontend
"""

import subprocess
import sys
import os

if __name__ == "__main__":
    # Set environment variables
    os.environ.setdefault("PYTHONPATH", ".")
    
    # Run the Streamlit app
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", 
        "app.py",
        "--server.port=8501",
        "--server.address=0.0.0.0"
    ])