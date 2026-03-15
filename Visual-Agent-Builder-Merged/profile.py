"""
Redirect module — profile page lives in pages/profile.py.
This file exists for backward compatibility with flat-structure imports.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pages.profile import *

if __name__ == "__main__":
    main()
