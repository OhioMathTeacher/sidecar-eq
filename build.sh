#!/usr/bin/env bash
# Build script for Sidecar EQ cross-platform distribution
# Supports: macOS (.app), Windows (.exe), Linux (.AppImage)

set -e  # Exit on error

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

APP_NAME="Sidecar EQ"
VERSION="2.1.0"
DIST_DIR="dist"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[BUILD]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

detect_platform() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo "windows"
    else
        error "Unsupported platform: $OSTYPE"
    fi
}

check_dependencies() {
    log "Checking build dependencies..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        error "python3 is not installed"
    fi
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        error "pip3 is not installed"
    fi
    
    success "Dependencies OK"
}

install_build_tools() {
    local platform=$1
    log "Installing build tools for $platform..."
    
    case $platform in
        macos)
            pip3 install --upgrade py2app
            ;;
        windows|linux)
            pip3 install --upgrade pyinstaller
            ;;
    esac
    
    success "Build tools installed"
}

build_macos() {
    log "Building macOS .app bundle..."
    
    # Clean previous build
    rm -rf build dist
    
    # Build with py2app
    python3 setup_py2app.py py2app
    
    # Check result
    if [ -d "dist/Sidecar EQ.app" ]; then
        success "macOS build complete: dist/Sidecar EQ.app"
        
        # Create DMG (optional)
        if command -v create-dmg &> /dev/null; then
            log "Creating DMG installer..."
            create-dmg \
                --volname "Sidecar EQ" \
                --window-pos 200 120 \
                --window-size 600 400 \
                --icon-size 100 \
                --icon "Sidecar EQ.app" 175 120 \
                --hide-extension "Sidecar EQ.app" \
                --app-drop-link 425 120 \
                "dist/SidecarEQ-${VERSION}.dmg" \
                "dist/Sidecar EQ.app"
            success "DMG created: dist/SidecarEQ-${VERSION}.dmg"
        else
            warn "create-dmg not installed. Skipping DMG creation."
            warn "Install with: brew install create-dmg"
        fi
    else
        error "macOS build failed"
    fi
}

build_windows() {
    log "Building Windows .exe..."
    
    # Generate spec file
    python3 build_config.py
    
    # Clean previous build
    rm -rf build dist
    
    # Build with PyInstaller
    pyinstaller sidecar_eq_windows.spec
    
    # Check result
    if [ -f "dist/Sidecar_EQ.exe" ]; then
        success "Windows build complete: dist/Sidecar_EQ.exe"
        
        # Create installer with Inno Setup (if available)
        if command -v iscc &> /dev/null; then
            log "Creating Windows installer..."
            # TODO: Create Inno Setup script
            warn "Inno Setup script not yet implemented"
        fi
    else
        error "Windows build failed"
    fi
}

build_linux() {
    log "Building Linux AppImage..."
    
    # Generate spec file
    python3 build_config.py
    
    # Clean previous build
    rm -rf build dist
    
    # Build with PyInstaller
    pyinstaller sidecar_eq_linux.spec
    
    # Check result
    if [ -f "dist/Sidecar_EQ" ]; then
        success "Linux build complete: dist/Sidecar_EQ"
        
        # Create AppImage (requires appimagetool)
        if command -v appimagetool &> /dev/null; then
            log "Creating AppImage..."
            
            # Create AppDir structure
            mkdir -p dist/SidecarEQ.AppDir/usr/bin
            mkdir -p dist/SidecarEQ.AppDir/usr/share/icons/hicolor/256x256/apps
            mkdir -p dist/SidecarEQ.AppDir/usr/share/applications
            
            # Copy executable
            cp dist/Sidecar_EQ dist/SidecarEQ.AppDir/usr/bin/sidecar-eq
            
            # Copy icon (if exists)
            if [ -f "icons/app_icon.png" ]; then
                cp icons/app_icon.png dist/SidecarEQ.AppDir/usr/share/icons/hicolor/256x256/apps/sidecar-eq.png
                cp icons/app_icon.png dist/SidecarEQ.AppDir/sidecar-eq.png
            fi
            
            # Create desktop file
            cat > dist/SidecarEQ.AppDir/sidecar-eq.desktop << EOF
[Desktop Entry]
Type=Application
Name=Sidecar EQ
Comment=Music player with per-track EQ memory
Icon=sidecar-eq
Exec=sidecar-eq
Categories=AudioVideo;Audio;Player;
Terminal=false
EOF
            
            # Create AppRun script
            cat > dist/SidecarEQ.AppDir/AppRun << 'EOF'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin:${PATH}"
exec "${HERE}/usr/bin/sidecar-eq" "$@"
EOF
            chmod +x dist/SidecarEQ.AppDir/AppRun
            
            # Build AppImage
            appimagetool dist/SidecarEQ.AppDir dist/SidecarEQ-${VERSION}-x86_64.AppImage
            
            success "AppImage created: dist/SidecarEQ-${VERSION}-x86_64.AppImage"
        else
            warn "appimagetool not installed. Skipping AppImage creation."
            warn "Install from: https://github.com/AppImage/AppImageKit/releases"
        fi
    else
        error "Linux build failed"
    fi
}

show_usage() {
    cat << EOF
Usage: $0 [PLATFORM]

Build Sidecar EQ for the specified platform.

Platforms:
    macos       Build macOS .app bundle (requires py2app)
    windows     Build Windows .exe (requires PyInstaller)
    linux       Build Linux AppImage (requires PyInstaller + appimagetool)
    all         Build for all platforms (requires Docker or VMs)
    current     Build for current platform (default)

Options:
    -h, --help  Show this help message

Examples:
    $0                  # Build for current platform
    $0 macos            # Build for macOS
    $0 all              # Build for all platforms
EOF
}

# Main script
main() {
    local platform="${1:-current}"
    
    case $platform in
        -h|--help)
            show_usage
            exit 0
            ;;
        current)
            platform=$(detect_platform)
            ;;
        all)
            error "Building for all platforms requires Docker or VMs. Not yet implemented."
            ;;
        macos|windows|linux)
            ;;
        *)
            error "Unknown platform: $platform"
            ;;
    esac
    
    log "Starting build for: $platform"
    log "Version: $VERSION"
    
    check_dependencies
    install_build_tools "$platform"
    
    case $platform in
        macos)
            build_macos
            ;;
        windows)
            build_windows
            ;;
        linux)
            build_linux
            ;;
    esac
    
    success "Build complete!"
    log "Output directory: $DIST_DIR"
}

main "$@"
