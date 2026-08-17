"""
Demo Runner for YC Application Video & Testing
Supports passing any file path via CLI argument!
Usage: python test_demo.py [filepath]
Example: python test_demo.py target_stripe.py
"""

import os
import sys

# Ensure project root is in python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from apipatch.engine import ApiPatchEngine

if __name__ == "__main__":
    target_arg = sys.argv[1] if len(sys.argv) > 1 else "target_sample.py"
    if not os.path.isabs(target_arg) and not os.path.exists(target_arg):
        candidate = os.path.join(CURRENT_DIR, target_arg)
        if os.path.exists(candidate):
            target_arg = candidate

    engine = ApiPatchEngine()
    if os.path.isdir(target_arg):
        engine.process_directory(target_arg)
    else:
        engine.process_file(target_arg)
