"""
Setup script for building macOS .app bundle with py2app
"""
from setuptools import setup

APP = ['sidecar_eq/app.py']
DATA_FILES = [
    ('icons', [
        'icons/addfiles.svg',
        'icons/addfolder.svg',
        'icons/download_hover.svg',
        'icons/download_pressed.svg',
        'icons/download.svg',
        'icons/fileplus_hover.svg',
        'icons/fileplus_pressed.svg',
        'icons/folderplus_hover.svg',
        'icons/folderplus_pressed.svg',
        'icons/next_hover.svg',
        'icons/next_pressed.svg',
        'icons/next.svg',
        'icons/play_active.svg',
        'icons/play_hover.svg',
        'icons/play.svg',
        'icons/playlist_hover.svg',
        'icons/playlist_pressed.svg',
        'icons/playlist.svg',
        'icons/stop_hover.svg',
        'icons/stop_pressed.svg',
        'icons/stop.svg',
        'icons/trash_hover.svg',
        'icons/trash_pressed.svg',
        'icons/trash.svg',
    ])
]

OPTIONS = {
    'argv_emulation': True,
    'iconfile': None,  # Add custom icon path if you have one
    'plist': {
        'CFBundleName': 'SidecarEQ',
        'CFBundleDisplayName': 'Sidecar EQ',
        'CFBundleIdentifier': 'com.ohiomathteacher.sidecar-eq',
        'CFBundleVersion': '1.1.1',
        'CFBundleShortVersionString': '1.1.1',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.14',
    },
    'packages': [
        'PySide6',
        'librosa',
        'soundfile',
        'numpy',
        'scipy',
        'pyqtgraph',
        'dotenv',
        'plexapi',
        'sidecar_eq',
    ],
    'includes': [
        'sidecar_eq.app',
        'sidecar_eq.player',
        'sidecar_eq.queue_model',
        'sidecar_eq.playlist',
        'sidecar_eq.store',
        'sidecar_eq.metadata',
        'sidecar_eq.analyzer',
        'sidecar_eq.collapsible_panel',
        'sidecar_eq.search',
        'sidecar_eq.star_rating_delegate',
        'sidecar_eq.ui',
        'sidecar_eq.workers',
        'sidecar_eq.plex_helpers',
        'sidecar_eq.plex_account_manager',
        'sidecar_eq.plex_browser',
        'sidecar_eq.indexer',
    ],
    'excludes': [
        'tkinter',
        'matplotlib',
        'IPython',
        'jupyter',
    ],
}

setup(
    name='SidecarEQ',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
