"""Test configuration for pytest."""

import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

# Ensure sidecar_eq module is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
    # Don't quit - other tests might need it
