#!/bin/bash

# Phase 1 Instant Rollback Script

echo "=========================================="
echo "Phase 1: Dynamic Ability Discovery"
echo "Instant Rollback Script"
echo "=========================================="
echo ""

# Check current state
if [ -z "$USE_DYNAMIC_DISCOVERY" ]; then
    echo "📋 Current State: Environment variable not set (default: DISABLED)"
    echo "🔧 Recommendation: No action needed"
else
    echo "📋 Current State: USE_DYNAMIC_DISCOVERY=$USE_DYNAMIC_DISCOVERY"
fi

echo ""
echo "=========================================="
echo "Rollback Options:"
echo "=========================================="
echo ""
echo "Option 1: Disable via Environment Variable (RECOMMENDED)"
echo "  Command: export USE_DYNAMIC_DISCOVERY=false"
echo "  Effect: Instant on application restart"
echo ""
echo "Option 2: Enable via Environment Variable"
echo "  Command: export USE_DYNAMIC_DISCOVERY=true"
echo "  Effect: Instant on application restart"
echo ""
echo "Option 3: Git Checkout (Complete Rollback)"
echo "  Command: git checkout backend/app/services/enhanced_parser.py"
echo "  Effect: Reverts all Phase 1 changes"
echo ""

echo "=========================================="
echo "Current Environment:"
echo "=========================================="
echo "USE_DYNAMIC_DISCOVERY=${USE_DYNAMIC_DISCOVERY:-not set}"
echo ""

echo "To disable dynamic discovery and revert to hardcoded mode:"
echo "  export USE_DYNAMIC_DISCOVERY=false"
echo "  Then restart your application"
