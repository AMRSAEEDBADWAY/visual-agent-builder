"""
Redirect — login.py points to app.py (the main entry point).
This file exists for backward compatibility with the First0.2 structure
which used login.py as the entry point instead of app.py.
"""
import importlib
import sys
import os

# Ensure the correct path is set
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the main app
import app
app.main()
