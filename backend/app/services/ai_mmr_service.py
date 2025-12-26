"""
AI MMR Service for team balancing with AI players.

Provides AI MMR values for team balancing. Values are loaded from a config file
for easy recalibration without code changes.
"""
import json
import os
from pathlib import Path

# Default values (used if config file doesn't exist)
DEFAULT_AI_MMR_VALUES = {
    "very_easy": 1400,
    "easy": 1650,
    "medium": 1900,
    "hard": 2100,
    "very_hard": 2350,
    "elite": 2500,
}

def get_config_path() -> Path:
    """Get path to AI MMR config file."""
    return Path(__file__).parent.parent / "config" / "ai_mmr.json"

def load_ai_mmr_values() -> dict:
    """Load AI MMR values from config file, falling back to defaults."""
    config_path = get_config_path()
    
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    return DEFAULT_AI_MMR_VALUES.copy()

def get_ai_mmr(difficulty: str) -> float:
    """
    Get the MMR value for a given AI difficulty.
    
    Args:
        difficulty: One of "very_easy", "easy", "medium", "hard", "very_hard", "elite"
        
    Returns:
        MMR value for the AI difficulty
    """
    values = load_ai_mmr_values()
    return values.get(difficulty.lower(), values.get("medium", 1900))

def get_all_ai_difficulties() -> dict:
    """Get all available AI difficulties and their MMR values."""
    return load_ai_mmr_values()
