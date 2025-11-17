#!/bin/bash
# Build AppImage for Sidecar EQ
# This script creates a standalone AppImage that can be run without installation

set -e  # Exit on error

echo "🎵 Building Sidecar EQ AppImage..."

# Configuration
APP_NAME="SidecarEQ"
APP_DIR="AppDir"
PYTHON_VERSION="3.11"

# Read version from pyproject.toml
APP_VERSION=$(grep -E '^version\s*=\s*"' pyproject.toml | head -n1 | sed -E 's/[^\"]*"([^"]+)".*/\1/')
if [ -z "$APP_VERSION" ]; then
    APP_VERSION="0.0.0"
fi

# Detect architecture for correct appimagetool and output naming
UNAME_ARCH=$(uname -m)
case "$UNAME_ARCH" in
    x86_64|amd64)
        APPIMAGE_ARCH="x86_64"
        ;;
    aarch64|arm64)
        APPIMAGE_ARCH="aarch64"
        ;;
    armv7l)
        APPIMAGE_ARCH="armhf"
        ;;
    *)
        echo "⚠️  Unknown architecture '$UNAME_ARCH', defaulting to x86_64"
        APPIMAGE_ARCH="x86_64"
        ;;
esac

# Clean previous build
echo "📦 Cleaning previous build..."
rm -rf "$APP_DIR" *.AppImage

# Create AppDir structure
echo "📁 Creating AppDir structure..."
mkdir -p "$APP_DIR/usr/bin"
mkdir -p "$APP_DIR/usr/lib"
mkdir -p "$APP_DIR/usr/share/applications"
mkdir -p "$APP_DIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$APP_DIR/usr/share/metainfo"

# Install Python and dependencies into AppDir
echo "🐍 Installing Python environment..."
python3 -m venv "$APP_DIR/usr"
source "$APP_DIR/usr/bin/activate"

# Install all dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install PySide6 mutagen pillow python-dotenv requests beautifulsoup4 \
    lxml plexapi yt-dlp pedalboard numpy librosa soundfile

# Copy application files
echo "📋 Copying application files..."
cp -r sidecar_eq "$APP_DIR/usr/lib/"
cp -r icons "$APP_DIR/usr/lib/sidecar_eq/" 2>/dev/null || true

# Create launcher script
echo "🚀 Creating launcher script..."
cat > "$APP_DIR/usr/bin/sidecar-eq" << 'EOF'
#!/bin/bash
# Sidecar EQ Launcher

# Get the directory where this script is located
APPDIR="$(dirname "$(dirname "$(readlink -f "$0")")")"

# Set up environment
export PATH="$APPDIR/usr/bin:$PATH"
export PYTHONPATH="$APPDIR/usr/lib:$PYTHONPATH"
export LD_LIBRARY_PATH="$APPDIR/usr/lib:$LD_LIBRARY_PATH"

# Qt platform plugin path
export QT_PLUGIN_PATH="$APPDIR/usr/lib/python*/site-packages/PySide6/Qt/plugins"

# Run the application
cd "$APPDIR/usr/lib"
exec "$APPDIR/usr/bin/python3" -m sidecar_eq.app "$@"
EOF

chmod +x "$APP_DIR/usr/bin/sidecar-eq"

# Create .desktop file (both in AppDir root and usr/share to satisfy appimagetool)
echo "🖼️ Creating desktop entry..."
cat > "$APP_DIR/sidecar-eq.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Sidecar EQ
Comment=Educational audio player with 7-band EQ
Exec=sidecar-eq
Icon=sidecar-eq
Categories=AudioVideo;Audio;Player;
Terminal=false
EOF

# Also install to usr/share/applications for completeness
mkdir -p "$APP_DIR/usr/share/applications"
cp "$APP_DIR/sidecar-eq.desktop" "$APP_DIR/usr/share/applications/sidecar-eq.desktop"

# Create AppRun
echo "⚙️ Creating AppRun..."
cat > "$APP_DIR/AppRun" << 'EOF'
#!/bin/bash
# AppImage entry point

APPDIR="$(dirname "$(readlink -f "$0")")"
export PATH="$APPDIR/usr/bin:$PATH"
export PYTHONPATH="$APPDIR/usr/lib:$PYTHONPATH"
export LD_LIBRARY_PATH="$APPDIR/usr/lib:$LD_LIBRARY_PATH"
export QT_PLUGIN_PATH="$APPDIR/usr/lib/python*/site-packages/PySide6/Qt/plugins"

cd "$APPDIR/usr/lib"
exec "$APPDIR/usr/bin/python3" -m sidecar_eq.app "$@"
EOF

chmod +x "$APP_DIR/AppRun"

# Create icon (using a placeholder if icons don't exist)
if [ -f "icons/sidecar-eq.png" ]; then
    cp "icons/sidecar-eq.png" "$APP_DIR/usr/share/icons/hicolor/256x256/apps/sidecar-eq.png"
    cp "icons/sidecar-eq.png" "$APP_DIR/sidecar-eq.png"
else
    echo "⚠️  No icon found, using placeholder"
    # Create a simple placeholder icon
    convert -size 256x256 xc:none -fill '#4a9eff' -draw 'circle 128,128 128,50' \
            -pointsize 80 -fill white -gravity center -annotate +0+0 'EQ' \
            "$APP_DIR/sidecar-eq.png" 2>/dev/null || echo "ImageMagick not available"
fi

# Copy icon to required locations
cp "$APP_DIR/sidecar-eq.png" "$APP_DIR/.DirIcon" 2>/dev/null || true

# Download appimagetool for this architecture if not present
APPIMAGETOOL="appimagetool-${APPIMAGE_ARCH}.AppImage"
if [ ! -f "$APPIMAGETOOL" ]; then
    echo "📥 Downloading appimagetool for $APPIMAGE_ARCH..."
    wget -q "https://github.com/AppImage/AppImageKit/releases/download/continuous/${APPIMAGETOOL}"
    chmod +x "$APPIMAGETOOL"
fi

# Build AppImage
echo "🔨 Building AppImage (arch=$APPIMAGE_ARCH, version=$APP_VERSION)..."
# Use extract-and-run to avoid FUSE requirement in restricted environments
OUTPUT_NAME="${APP_NAME}-${APP_VERSION}-${APPIMAGE_ARCH}.AppImage"
APPIMAGE_EXTRACT_AND_RUN=1 ARCH="$APPIMAGE_ARCH" ./$APPIMAGETOOL "$APP_DIR" "$OUTPUT_NAME"

# Make it executable
chmod +x "$OUTPUT_NAME"

echo ""
echo "✅ Build complete!"
echo "📦 AppImage created: $OUTPUT_NAME"
echo ""
echo "To run:"
echo "  ./$OUTPUT_NAME"
echo ""
echo "To install system-wide (optional):"
echo "  sudo mv $OUTPUT_NAME /usr/local/bin/sidecar-eq"
echo "  sudo chmod +x /usr/local/bin/sidecar-eq"
