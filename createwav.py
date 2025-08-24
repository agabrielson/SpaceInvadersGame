#!/usr/bin/env python3

"""
@file beep_generator.py
@brief Generates simple WAV sound effects for a game.

@details
Uses NumPy and SciPy to synthesize basic sine wave sounds and
write them to WAV files. Generates player shooting, alien hit,
and alien shooting sounds.

@note
All output WAV files are written to the current working directory.
"""

import numpy as np
from scipy.io.wavfile import write
from pathlib import Path

ASSET_DIR = Path(__file__).parent / "assets"
"""@brief directory with external files."""

def create_beep(filename, freq=440, duration_ms=150, volume=0.3, framerate=44100):
    """
    Generate a simple sine wave beep and save it as a WAV file.

    @param filename  Name of the output WAV file.
    @param freq      Frequency of the sine wave in Hz (default: 440).
    @param duration_ms Duration of the beep in milliseconds (default: 150).
    @param volume    Volume of the beep, range 0.0 to 1.0 (default: 0.3).
    @param framerate Sampling rate in Hz (default: 44100).

    @return None
    """
    t = np.linspace(0, duration_ms/1000, int(framerate*duration_ms/1000), False)
    tone = np.sin(freq * t * 2 * np.pi) * volume
    audio = np.int16(tone * 32767)
    write(ASSET_DIR / filename, framerate, audio)

# ---------------------------------------------------------------------
# Create game sounds
# ---------------------------------------------------------------------
create_beep("shoot.wav", freq=800, duration_ms=100)         # Player shooting
create_beep("hit.wav", freq=1000, duration_ms=120)          # Alien hit
create_beep("alien_shoot.wav", freq=600, duration_ms=150)   # Alien shooting

print("WAV files created!")
