#!/usr/bin/env python3
"""
@file generate_sprites.py
@brief Generates all pixel-art sprites for the Space Invaders game.
@details
This script creates:
  - Player sprite
  - Bullet sprite
  - Alien sprites (squid, crab, octopus) with 2-frame animations per color
  - Alien bullets
  - Mystery ship

Aliens have 6 colors, and each color has 2 frames using slightly different patterns
for simple animation. Sprites are saved as PNG files in the current directory.
"""

from PIL import Image, ImageDraw
import random
from pathlib import Path

ASSET_DIR = Path(__file__).parent / "assets"
"""@brief directory with external files."""

def draw_pixel_sprite(pattern, pixel_size, color, filename):
    """
    @brief Draws a pixel-art sprite from a binary pattern and saves it as PNG.
    @param pattern List of strings containing '1' (filled) or '0' (empty) pixels.
    @param pixel_size Size of each pixel in the output image.
    @param color Tuple (R,G,B) color for filled pixels.
    @param filename Filename to save the PNG sprite.
    """
    rows = len(pattern)
    cols = len(pattern[0])
    img = Image.new("RGBA", (cols * pixel_size, rows * pixel_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for y, row in enumerate(pattern):
        for x, c in enumerate(row):
            if c == "1":
                x0, y0 = x * pixel_size, y * pixel_size
                x1, y1 = x0 + pixel_size, y0 + pixel_size
                draw.rectangle([x0, y0, x1, y1], fill=color)

    img.save(ASSET_DIR / filename)

# ---------------------------------------------------------------------
# Player and bullets
# ---------------------------------------------------------------------

player_pattern = [
    "0001000",
    "0011100",
    "0010100",
    "0110110",
    "1111111",
    "1110111",
    "1101011",
]
draw_pixel_sprite(player_pattern, 6, (0, 255, 0), "player.png")

bullet_pattern = ["1", "1", "1"]
draw_pixel_sprite(bullet_pattern, 5, (255, 255, 0), "bullet.png")

alien_bullet_pattern = ["1", "0", "1", "0", "1"]
draw_pixel_sprite(alien_bullet_pattern, 5, (255, 0, 255), "alien_bullet.png")

# ---------------------------------------------------------------------
# Aliens (animated frames)
# ---------------------------------------------------------------------

# Animation comes from splicing these two patterns together
alien_patterns = {
    "squid": [
        "00111100",
        "01111110",
        "11111111",
        "11011011",
        "11111111",
        "01100110",
        "11000011",
    ],
    "crab": [
        "01100110",
        "11111111",
        "11011011",
        "11111111",
        "00111100",
        "01111110",
        "11000011",
    ],
    "octopus": [
        "00111100",
        "01111110",
        "11111111",
        "10111101",
        "11111111",
        "01011010",
        "10100101",
    ],
}

alien_patterns2 = {
    "squid": [
        "00111100",
        "01111110",
        "11111111",
        "11011011",
        "11111111",
        "01100110",
        "01100110",
    ],
    "crab": [
        "01100110",
        "11111111",
        "11011011",
        "11111111",
        "00111100",
        "01111110",
        "01100110",
    ],
    "octopus": [
        "00111100",
        "01111110",
        "11111111",
        "10111101",
        "11111111",
        "01011010",
        "00110110",
    ],
}

# 6-color palette for aliens
colors = [
    (255, 0, 0),      # Red
    (0, 255, 0),      # Green
    (0, 0, 255),      # Blue
    (255, 255, 0),    # Yellow
    (255, 0, 255),    # Magenta
    (0, 255, 255),    # Cyan
]

# Generate two frames per alien using both patterns
for alien_name in alien_patterns.keys():
    pattern1 = alien_patterns[alien_name]
    pattern2 = alien_patterns2[alien_name]
    for i, base_color in enumerate(colors):
        # Frame 0
        draw_pixel_sprite(pattern1, 5, base_color,
                          f"alien_{alien_name}_{i}_0.png")
        # Frame 1
        draw_pixel_sprite(pattern2, 5, base_color,
                          f"alien_{alien_name}_{i}_1.png")

# ---------------------------------------------------------------------
# Mystery ship
# ---------------------------------------------------------------------

mystery_ship_pattern = [
    "000111000",
    "001111100",
    "011111110",
    "101101101",
    "011101110",
    "001000100",
]
mystery_color = tuple(random.randint(100, 255) for _ in range(3))
draw_pixel_sprite(mystery_ship_pattern, 5, mystery_color, "mystery_ship.png")

# ---------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------
print("Sprites generated:")
print("player.png, bullet.png, alien_bullet.png")
print("alien_<type>_<color>_0.png, alien_<type>_<color>_1.png")
print("mystery_ship.png")
