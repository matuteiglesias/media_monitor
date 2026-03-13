import os, sys
# Add project root (one level up from tests/) to sys.path so `import backend` works
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
