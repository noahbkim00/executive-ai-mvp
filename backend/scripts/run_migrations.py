#!/usr/bin/env python
"""Script to run Alembic migrations."""

import os
import sys
import subprocess

# Set environment variable to prevent async engine creation
os.environ['ALEMBIC_CONFIG'] = 'true'

# Change to backend directory
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(backend_dir)

# Run alembic upgrade
result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], capture_output=True, text=True)

print(result.stdout)
if result.stderr:
    print(result.stderr, file=sys.stderr)

sys.exit(result.returncode)