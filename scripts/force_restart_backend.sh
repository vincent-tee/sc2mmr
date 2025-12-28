#!/bin/bash
# Forcefully restart the backend with complete cleanup

echo "="
echo "Force Restart Backend"
echo "="

# Step 1: Kill all Python processes running uvicorn
echo "Step 1: Killing all uvicorn processes..."
pkill -9 -f "uvicorn app.main:app"
sleep 1

# Verify they're dead
REMAINING=$(ps aux | grep -v grep | grep "uvicorn app.main:app" | wc -l)
if [ $REMAINING -gt 0 ]; then
    echo "⚠️  Warning: $REMAINING uvicorn process(es) still running"
    ps aux | grep -v grep | grep uvicorn
else
    echo "✓ All uvicorn processes killed"
fi

# Step 2: Clear Python bytecode cache
echo ""
echo "Step 2: Clearing Python cache..."
cd /home/vtee/projects/sc2mmr/backend
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
find . -name "*.pyo" -delete 2>/dev/null
echo "✓ Python cache cleared"

# Step 3: Verify the code has the new exception
echo ""
echo "Step 3: Verifying code has WinnerDeterminationError..."
if grep -q "except WinnerDeterminationError" /home/vtee/projects/sc2mmr/backend/app/api/replays.py; then
    echo "✓ Code has WinnerDeterminationError handler"
else
    echo "✗ ERROR: Code does NOT have WinnerDeterminationError handler"
    echo "   This means the code wasn't committed properly"
    exit 1
fi

# Step 4: Start fresh backend
echo ""
echo "Step 4: Starting backend..."
echo "Command: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "To verify it's working after startup:"
echo "  1. Upload a problem replay"
echo "  2. Error should say 'Winner determination failed:' (NOT 'Parse error:')"
echo "  3. Check Failed Uploads page - should see 'Winner Determination' category"
echo ""
cd /home/vtee/projects/sc2mmr/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
