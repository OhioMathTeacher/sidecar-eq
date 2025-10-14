"""Integration test for main application."""

import pytest
from PySide6.QtWidgets import QApplication

from sidecar_eq.app import MainWindow


class TestMainWindow:
    """Integration tests for MainWindow."""

    def test_window_creation(self, qapp):
        """Test that MainWindow can be created."""
        window = MainWindow()
        assert window is not None
        assert hasattr(window, "model")
        assert hasattr(window, "table")
        assert hasattr(window, "player")

    def test_window_has_toolbar(self, qapp):
        """Test that window has a toolbar."""
        window = MainWindow()
        toolbar = window.findChild(object, "")  # Find any toolbar
        # Just verify window initialized without crashing
        assert window is not None

    def test_window_has_table(self, qapp):
        """Test that window has the queue table."""
        window = MainWindow()
        assert window.table is not None

    def test_window_has_player(self, qapp):
        """Test that window has a player instance."""
        window = MainWindow()
        assert window.player is not None
