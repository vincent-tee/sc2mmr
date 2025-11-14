#!/bin/bash
# Find SC2 replays on Windows drive (WSL2)

echo "Searching for StarCraft II replays on Windows drive..."
echo "This may take a moment..."
echo ""

# Find all SC2 replay files
REPLAYS=$(find /mnt/c/Users/ -name "*.SC2Replay" 2>/dev/null)

if [ -z "$REPLAYS" ]; then
    echo "No SC2 replay files found."
    echo ""
    echo "Manual search:"
    echo "  cd /mnt/c/Users/YourUsername/Documents/"
    echo "  cd 'StarCraft II/Accounts'"
    exit 1
fi

# Count total replays
TOTAL=$(echo "$REPLAYS" | wc -l)
echo "Found $TOTAL SC2 replay file(s)"
echo ""

# Show first 10
echo "First 10 replays found:"
echo "$REPLAYS" | head -10
echo ""

# Find multiplayer replays specifically
MULTIPLAYER=$(echo "$REPLAYS" | grep -i "Multiplayer")
MULTIPLAYER_COUNT=$(echo "$MULTIPLAYER" | grep -c "SC2Replay")

if [ $MULTIPLAYER_COUNT -gt 0 ]; then
    echo "Found $MULTIPLAYER_COUNT multiplayer replay(s)"
    echo ""
    echo "Multiplayer replay location(s):"
    echo "$MULTIPLAYER" | head -5 | xargs -I {} dirname {} | sort -u
    echo ""
fi

# Ask if user wants to copy them
echo "Options:"
echo "  1. Copy all replays to ~/sc2_replays/"
echo "  2. Copy only multiplayer replays to ~/sc2_replays/"
echo "  3. Just show me the paths (no copy)"
echo ""
read -p "Choose (1/2/3): " choice

case $choice in
    1)
        mkdir -p ~/sc2_replays
        echo "$REPLAYS" | while read file; do
            cp "$file" ~/sc2_replays/
        done
        echo "✓ Copied $TOTAL replay(s) to ~/sc2_replays/"
        ls -lh ~/sc2_replays/ | head -10
        ;;
    2)
        if [ $MULTIPLAYER_COUNT -gt 0 ]; then
            mkdir -p ~/sc2_replays
            echo "$MULTIPLAYER" | while read file; do
                cp "$file" ~/sc2_replays/
            done
            echo "✓ Copied $MULTIPLAYER_COUNT multiplayer replay(s) to ~/sc2_replays/"
            ls -lh ~/sc2_replays/ | head -10
        else
            echo "No multiplayer replays found."
        fi
        ;;
    3)
        echo ""
        echo "All replay paths:"
        echo "$REPLAYS"
        ;;
    *)
        echo "Invalid choice. Exiting."
        ;;
esac
