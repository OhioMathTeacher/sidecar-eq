"""
py2app setup script for Sidecar EQ macOS .app bundle.

Usage:
    python setup_py2app.py py2app

Options:
    py2app          Build .app bundle
    py2app -A       Build alias mode (faster for development)
"""

from setuptools import setup
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

APP = ['sidecar_eq/app.py']
APP_NAME = 'Sidecar EQ'
VERSION = '2.0.0'
BUNDLE_ID = 'com.ohiomathteacher.sidecar-eq'

DATA_FILES = [
    ('icons', list(Path('icons').glob('*.svg')) + list(Path('icons').glob('*.png'))),
]

OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'icons/app_icon.icns' if Path('icons/app_icon.icns').exists() else None,
    'plist': {
        'CFBundleName': APP_NAME,
        'CFBundleDisplayName': APP_NAME,
        'CFBundleIdentifier': BUNDLE_ID,
        'CFBundleVersion': VERSION,
        'CFBundleShortVersionString': VERSION,
        'NSHumanReadableCopyright': 'Copyright © 2025 Michael Todd Edwards',
        'LSMinimumSystemVersion': '10.15.0',
        'NSHighResolutionCapable': True,
        'LSApplicationCategoryType': 'public.app-category.music',
    },
    'packages': [
        'sidecar_eq',
        'PySide6',
        'librosa',
        'numpy',
        'scipy',
    ],
    'includes': [
        'sidecar_eq.player',
        'sidecar_eq.queue_model',
        'sidecar_eq.eq.eq_manager',
        'sidecar_eq.eq.volume_manager',
        'sidecar_eq.ui',
        'sidecar_eq.ui.beam_slider',
        'sidecar_eq.ui.led_meter',
        'sidecar_eq.metadata_cache',
        'sidecar_eq.online_metadata',
    ],
    'excludes': [
        'tkinter',
        'matplotlib',
        'IPython',
        'jupyter',
    ],
}

setup(
    name=APP_NAME,
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
