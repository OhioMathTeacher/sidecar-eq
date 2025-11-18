"""Build configuration for Sidecar EQ cross-platform distribution.

This script creates standalone executables for:
- macOS: .app bundle (using py2app)
- Windows: .exe (using PyInstaller)
- Linux: .AppImage (using PyInstaller + AppImage tools)
"""

import sys
from pathlib import Path

# Application metadata
APP_NAME = "Sidecar EQ"
APP_VERSION = "2.2.0"
BUNDLE_ID = "com.ohiomathteacher.sidecar-eq"
AUTHOR = "Michael Todd Edwards"
DESCRIPTION = "Music player with per-track EQ and volume memory"

# Source files
MAIN_SCRIPT = "sidecar_eq/app.py"
ICON_FILE = "icons/app_icon.icns"  # macOS
ICON_ICO = "icons/app_icon.ico"    # Windows
ICON_PNG = "icons/app_icon.png"    # Linux

# Data files to include
DATA_FILES = [
    ('icons', 'icons'),
    ('README.md', '.'),
    ('LICENSE', '.'),
]

# Hidden imports (modules not auto-detected)
HIDDEN_IMPORTS = [
    'sidecar_eq',
    'sidecar_eq.player',
    'sidecar_eq.queue_model',
    'sidecar_eq.eq.eq_manager',
    'sidecar_eq.eq.volume_manager',
    'sidecar_eq.ui.beam_slider',
    'sidecar_eq.ui.led_meter',
    'sidecar_eq.metadata_cache',
    'sidecar_eq.online_metadata',
    'sidecar_eq.plex_helpers',
    'sidecar_eq.yt_helper',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtMultimedia',
    'PySide6.QtMultimediaWidgets',
    'librosa',
    'soundfile',
    'numpy',
    'scipy',
]

# py2app options (macOS)
PY2APP_OPTIONS = {
    'app': [MAIN_SCRIPT],
    'data_files': DATA_FILES,
    'options': {
        'py2app': {
            'argv_emulation': False,
            'includes': HIDDEN_IMPORTS,
            'packages': ['sidecar_eq', 'PySide6'],
            'iconfile': ICON_FILE,
            'plist': {
                'CFBundleName': APP_NAME,
                'CFBundleDisplayName': APP_NAME,
                'CFBundleIdentifier': BUNDLE_ID,
                'CFBundleVersion': APP_VERSION,
                'CFBundleShortVersionString': APP_VERSION,
                'NSHumanReadableCopyright': f'Copyright © 2025 {AUTHOR}',
                'LSMinimumSystemVersion': '10.15.0',
                'NSHighResolutionCapable': True,
            },
        }
    },
}

# PyInstaller spec template (Windows/Linux)
PYINSTALLER_SPEC_TEMPLATE = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{main_script}'],
    pathex=[],
    binaries=[],
    datas={data_files},
    hiddenimports={hidden_imports},
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{app_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='{icon}',
)

# macOS bundle (alternative to py2app)
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='{app_name}.app',
        icon='{icon}',
        bundle_identifier='{bundle_id}',
        info_plist={{
            'NSHighResolutionCapable': 'True',
            'LSMinimumSystemVersion': '10.15.0',
        }},
    )
"""

def get_platform():
    """Detect current platform."""
    if sys.platform.startswith('darwin'):
        return 'macos'
    elif sys.platform.startswith('win'):
        return 'windows'
    elif sys.platform.startswith('linux'):
        return 'linux'
    else:
        raise RuntimeError(f"Unsupported platform: {sys.platform}")


def generate_pyinstaller_spec(platform='windows'):
    """Generate PyInstaller spec file for the given platform."""
    icon = ICON_ICO if platform == 'windows' else ICON_PNG
    
    spec_content = PYINSTALLER_SPEC_TEMPLATE.format(
        main_script=MAIN_SCRIPT,
        data_files=repr(DATA_FILES),
        hidden_imports=repr(HIDDEN_IMPORTS),
        app_name=APP_NAME.replace(' ', '_'),
        icon=icon,
        bundle_id=BUNDLE_ID,
    )
    
    spec_file = f"sidecar_eq_{platform}.spec"
    Path(spec_file).write_text(spec_content)
    print(f"Generated {spec_file}")
    return spec_file


if __name__ == '__main__':
    platform = get_platform()
    print(f"Detected platform: {platform}")
    
    if platform == 'macos':
        print("\nFor macOS .app bundle, use:")
        print("  python setup_py2app.py py2app")
    else:
        spec_file = generate_pyinstaller_spec(platform)
        print(f"\nFor {platform} executable, use:")
        print(f"  pyinstaller {spec_file}")
