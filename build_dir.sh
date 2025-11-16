#!/bin/bash
# Build standalone directory bundle for Sidecar EQ using PyInstaller
# This creates a directory with all dependencies (easier to debug than onefile)

set -e  # Exit on error

echo "Building SidecarEQ standalone directory bundle..."

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "Installing PyInstaller..."
    .venv/bin/pip install pyinstaller
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist_dir *.spec

# Build with PyInstaller (directory mode for easier debugging)
echo "Running PyInstaller..."
.venv/bin/pyinstaller \
    --name SidecarEQ \
    --windowed \
    --onedir \
    --icon=icons/app_icon.png \
    --add-data "icons:icons" \
    --add-data "assets:assets" \
    --add-data "examples:examples" \
    --add-data "sidecar_eq/MLKDream_64kb.mp3:sidecar_eq" \
    --hidden-import PySide6.QtCore \
    --hidden-import PySide6.QtWidgets \
    --hidden-import PySide6.QtGui \
    --hidden-import PySide6.QtMultimedia \
    --hidden-import PySide6.QtMultimediaWidgets \
    --hidden-import PySide6.QtSvg \
    --hidden-import PySide6.QtSvgWidgets \
    --hidden-import mutagen \
    --hidden-import plexapi \
    --hidden-import yt_dlp \
    --hidden-import dotenv \
    --hidden-import librosa \
    --hidden-import numpy \
    --hidden-import PIL \
    --collect-all PySide6 \
    --collect-all mutagen \
    --collect-all plexapi \
    --collect-all yt_dlp \
    --collect-submodules sidecar_eq \
    --paths . \
    --distpath dist_dir \
    run_sidecar.py

echo ""
echo "✓ Build complete!"
echo "Executable location: dist_dir/SidecarEQ/SidecarEQ"
echo ""
echo "To run:"
echo "  ./dist_dir/SidecarEQ/SidecarEQ"
echo ""
echo "To create a launcher script:"
echo "  echo '#!/bin/bash' > sidecar-eq"
echo "  echo 'cd $(dirname \$0)/dist_dir/SidecarEQ && ./SidecarEQ' >> sidecar-eq"
echo "  chmod +x sidecar-eq"
echo ""
