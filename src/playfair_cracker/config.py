"""
Configuration constants and mode settings for Playfair cracker.
"""

import os
from dataclasses import dataclass
from typing import Optional

# Playfair alphabet (25 letters, J->I)
ALPHABET = "ABCDEFGHIKLMNOPQRSTUVWXYZ"
ALPHABET_SIZE = 25

# Letter to ID mapping
LETTER_TO_ID = {letter: idx for idx, letter in enumerate(ALPHABET)}
ID_TO_LETTER = {idx: letter for idx, letter in enumerate(ALPHABET)}

# Vocali per penalty
VOWELS = {0, 4, 8, 13, 19}  # A, E, I, O, U


@dataclass
class ModeConfig:
    """Configuration for a specific execution mode."""
    restarts: int
    iters: int
    T0: float
    cooling: float
    top_k: int
    w_full: float
    w_core: float
    w_tri: float
    w_inword: float
    w_letter: float


# Fast mode configuration
FAST_MODE = ModeConfig(
    restarts=50,
    iters=1_000_000,
    T0=20.0,
    cooling=0.999995,
    top_k=50,
    w_full=0.55,
    w_core=0.45,
    w_tri=0.05,
    w_inword=0.05,
    w_letter=0.02,
)

# Deep mode configuration
DEEP_MODE = ModeConfig(
    restarts=300,
    iters=10_000_000,
    T0=35.0,
    cooling=0.9999992,
    top_k=100,
    w_full=0.40,
    w_core=0.60,
    w_tri=0.05,
    w_inword=0.05,
    w_letter=0.02,
)

# Deep mode refinement configuration
DEEP_REFINEMENT = ModeConfig(
    restarts=1,
    iters=2_000_000,
    T0=10.0,
    cooling=0.999998,
    top_k=20,
    w_full=0.75,
    w_core=0.25,
    w_tri=0.05,
    w_inword=0.05,
    w_letter=0.02,
)


def get_mode_config(mode: str) -> ModeConfig:
    """Get configuration for specified mode."""
    if mode == "fast":
        return FAST_MODE
    elif mode == "deep":
        return DEEP_MODE
    else:
        raise ValueError(f"Unknown mode: {mode}")

