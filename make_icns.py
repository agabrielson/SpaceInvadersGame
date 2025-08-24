#!/usr/bin/env python3

from PIL import Image
import os
import subprocess
import sys

def png_to_icns(png_path, icns_path):
    # Create a temporary iconset folder
    iconset = "temp.iconset"
    os.makedirs(iconset, exist_ok=True)

    # Required macOS icon sizes
    sizes = [16, 32, 64, 128, 256, 512, 1024]

    img = Image.open(png_path)

    for size in sizes:
        for scale in [1, 2]:
            scaled_size = size * scale
            filename = f"icon_{size}x{size}{'@2x' if scale == 2 else ''}.png"
            out_path = os.path.join(iconset, filename)
            img.resize((scaled_size, scaled_size), Image.Resampling.LANCZOS).save(out_path)

    # Use macOS built-in tool to convert to .icns
    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", icns_path])

    # Clean up
    subprocess.run(["rm", "-rf", iconset])

def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} input.png output.icns")
        sys.exit(1)

    png_path = sys.argv[1]
    icns_path = sys.argv[2]

    if not os.path.exists(png_path):
        print(f"Error: {png_path} does not exist.")
        sys.exit(1)

    png_to_icns(png_path, icns_path)
    print(f"✅ Converted {png_path} → {icns_path}")

if __name__ == "__main__":
    main()
