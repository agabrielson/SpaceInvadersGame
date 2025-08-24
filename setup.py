#!/usr/bin/env python3
"""
@file setup.py
@brief Builds the Space Invaders PyQt6 application as a macOS .app using py2app.

@details
This setup script uses setuptools and py2app to bundle the Space Invaders game
into a standalone macOS application. It includes the following features:

- Bundles all Python dependencies and assets (sprites, sounds, icons) into the .app.
- Automatically removes macOS extended attributes (xattr) that cause py2app
  to fail, ensuring the .app runs without manual intervention.
- Specifies Python version and pip dependencies required to run the game.
- Supports entry point for GUI scripts.
- Compatible with macOS 10.15+ and Python 3.9+.

@note After building, the .app will be created in the `dist/` directory.
@note User scores are stored in:
      ~/Library/Application Support/SpaceInvaders/scores.json
      which ensures writable storage outside the app bundle.

@note This command "python3 setup.py py2app" will enable
@note this command "open dist/space-invaders-pyqt.app"
"""

import os
import sys
import subprocess
from setuptools import setup, find_packages
from setuptools.command.build_py import build_py as _build_py

# ---------------------------------------------------------------------
# py2app build options
# ---------------------------------------------------------------------
OPTIONS = {
    "argv_emulation": True,
    "packages": ["PyQt6", "numpy", "scipy", "Pillow"],
    "resources": ["assets"],      # Bundle read-only assets
    "iconfile": "spaceinvaders.icns",  # Optional app icon
}

# ---------------------------------------------------------------------
# Custom build command
# ---------------------------------------------------------------------
class build_app(_build_py):
    """
    @class build_app
    @brief Custom build command to strip extended attributes from macOS .app.
    
    @details
    Subclasses the default setuptools build_py command. After building
    the Python package, this command removes Finder info and resource forks
    that prevent the .app from running on macOS.

    @note Only executed when building on macOS.
    """
    def run(self):
        """
        @brief Run the standard build process and then clean extended attributes.

        @details
        Calls the original build_py.run() method, then checks if the platform
        is macOS. If so, it looks for the .app bundle in the `dist` directory
        and recursively clears extended attributes using `xattr -cr`.
        """
        sys.setrecursionlimit(10000)  # default is ~1000
        _build_py.run(self)
        if sys.platform == "darwin":
            app_path = os.path.join("dist", "space-invaders-pyqt.app")
            if os.path.exists(app_path):
                print(f"Cleaning extended attributes in {app_path}...")
                subprocess.run(["xattr", "-cr", app_path])
                print("Extended attributes cleared.")

# ---------------------------------------------------------------------
# Setup configuration
# ---------------------------------------------------------------------
setup(
    name="space-invaders-pyqt",
    version="1.0.0",
    description="A PyQt6 Space Invaders clone with sprites, sound, and high scores.",
    author="Anthony Gabrielson",
    python_requires=">=3.9",
    packages=find_packages(exclude=["tests", "build", "dist"]),
    include_package_data=True,
    install_requires=[
        "PyQt6>=6.0",
        "numpy>=1.20",
        "scipy>=1.7",
        "Pillow>=8.0",
    ],
    entry_points={
        "gui_scripts": [
            "space-invaders=SpaceInvadersGame:main",  # Launch function
        ],
    },
    app=["SpaceInvadersGame.py"],  # Main game script
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
    cmdclass={"build_py": build_app},
)
