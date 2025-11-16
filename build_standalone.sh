#!/bin/bash
# Build standalone executable for Sidecar EQ using PyInstaller
# This is simpler than AppImage and works well for local use

set -e  # Exit on error

echo "Building SidecarEQ standalone executable..."

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "Installing PyInstaller..."
    .venv/bin/pip install pyinstaller
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist *.spec

# Build with PyInstaller
echo "Running PyInstaller..."
.venv/bin/pyinstaller \
    --name SidecarEQ \
    --windowed \
    --onefile \
    --icon=icons/app_icon.png \
    --add-data "icons:icons" \
    --add-data "assets:assets" \
    --add-data "examples:examples" \
    --hidden-import PySide6.QtCore \
    --hidden-import PySide6.QtWidgets \
    --hidden-import PySide6.QtGui \
    --hidden-import PySide6.QtMultimedia \
    --hidden-import PySide6.QtMultimediaWidgets \
    --hidden-import PySide6.QtSvg \
    --hidden-import mutagen \
    --hidden-import plexapi \
    --hidden-import yt_dlp \
    --collect-all PySide6 \
    --collect-all mutagen \
    --collect-all plexapi \
    --collect-all yt_dlp \
    run_sidecar.py

echo ""
echo "✓ Build complete!"
echo "Executable location: dist/SidecarEQ"
echo ""
echo "To run:"
echo "  ./dist/SidecarEQ"
echo ""
echo "To install system-wide (optional):"
echo "  sudo cp dist/SidecarEQ /usr/local/bin/"
echo "  sudo cp icons/app_icon.png /usr/share/pixmaps/sidecareq.png"
echo ""
