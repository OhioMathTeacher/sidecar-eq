"""Unit tests for background workers."""

import pytest
from PySide6.QtCore import QCoreApplication

from sidecar_eq.workers import BackgroundAnalysisWorker


class TestBackgroundAnalysisWorker:
    """Tests for BackgroundAnalysisWorker thread."""

    def test_initialization(self, qapp):
        """Test that worker initializes correctly."""
        worker = BackgroundAnalysisWorker("/fake/path.mp3")
        assert worker is not None
        assert worker.audio_path == "/fake/path.mp3"
        assert worker._should_stop is False

    def test_stop_analysis(self, qapp):
        """Test that stop_analysis sets the flag."""
        worker = BackgroundAnalysisWorker("/fake/path.mp3")
        assert worker._should_stop is False

        worker.stop_analysis()
        assert worker._should_stop is True

    def test_has_signals(self, qapp):
        """Test that worker has required signals."""
        worker = BackgroundAnalysisWorker("/fake/path.mp3")
        assert hasattr(worker, "analysis_complete")
        assert hasattr(worker, "analysis_failed")

    def test_signals_connectable(self, qapp):
        """Test that signals can be connected."""
        worker = BackgroundAnalysisWorker("/fake/path.mp3")
        results = []

        def on_complete(path, data):
            results.append(("complete", path, data))

        def on_failed(path, error):
            results.append(("failed", path, error))

        worker.analysis_complete.connect(on_complete)
        worker.analysis_failed.connect(on_failed)

        # Emit test signals
        worker.analysis_complete.emit("/test.mp3", {"test": "data"})
        QCoreApplication.processEvents()

        assert len(results) == 1
        assert results[0][0] == "complete"
        assert results[0][1] == "/test.mp3"
