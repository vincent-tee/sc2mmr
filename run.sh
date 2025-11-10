#!/bin/bash

# SC2 MMR Tracker - Run Script

echo "Starting SC2 MMR Tracker..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
    echo "Installing dependencies..."
    source venv/bin/activate
    pip install -r backend/requirements.txt
else
    source venv/bin/activate
fi

# Run the application
cd backend
echo "Starting FastAPI server on http://localhost:8000"
echo "API documentation available at http://localhost:8000/docs"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
