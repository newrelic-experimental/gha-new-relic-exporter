#!/bin/bash
# Activate venv, run all tests in tests/ folder, and output results

set -e

if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "ERROR: venv not found. Please create and activate your Python virtual environment."
    exit 1
fi

echo "Upgrading pip and installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Running all unit and integration tests in tests/ folder..."
python -m unittest discover tests
