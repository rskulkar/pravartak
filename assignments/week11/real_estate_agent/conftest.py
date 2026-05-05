import sys
import os

# ensures imports like `from state import ...` resolve
# when pytest is run from inside the real_estate_agent/ directory
sys.path.insert(0, os.path.dirname(__file__))
