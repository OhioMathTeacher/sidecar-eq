#!/usr/bin/env python3
"""Entry point for Sidecar EQ application.

This script starts the Sidecar EQ audio player with EQ interface.
It can be run directly or used as the entry point for PyInstaller builds.
"""

import sys
from pathlib import Path

# Add the parent directory to path so we can import sidecar_eq
sys.path.insert(0, str(Path(__file__).parent))

from sidecar_eq.app import main

if __name__ == "__main__":
    sys.exit(main())
