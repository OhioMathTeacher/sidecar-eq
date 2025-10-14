"""Background worker threads for Sidecar EQ application.

This module provides QThread-based workers for performing long-running
operations without blocking the UI thread.
"""

from pathlib import Path

from PySide6.QtCore import QThread, Signal


class BackgroundAnalysisWorker(QThread):
    """Background worker thread for audio analysis.

    Performs audio analysis (frequency spectrum, tempo, etc.) in a separate
    thread to prevent UI freezing. Emits signals on completion or failure
    that can be connected to UI update slots.

    The analysis can be cancelled by calling stop_analysis(), which sets an
    internal flag checked periodically during processing.

    Signals:
        analysis_complete(str, dict): Emitted on successful analysis with
            file path and analysis results dictionary.
        analysis_failed(str, str): Emitted on error with file path and
            error message.

    Args:
        audio_path: Path to the audio file to analyze.
        parent: Parent QObject (optional).

    Attributes:
        audio_path: Path to the file being analyzed.

    Example:
        >>> worker = BackgroundAnalysisWorker("/path/to/song.mp3")
        >>> worker.analysis_complete.connect(handle_results)
        >>> worker.analysis_failed.connect(handle_error)
        >>> worker.start()
    """

    # Signals to communicate with main thread
    analysis_complete = Signal(str, dict)  # path, analysis_result
    analysis_failed = Signal(str, str)  # path, error_message

    def __init__(self, audio_path: str, parent=None):
        """Initialize the background analysis worker.

        Args:
            audio_path: Full path to the audio file to analyze.
            parent: Parent QObject, defaults to None.
        """
        super().__init__(parent)
        self.audio_path = audio_path
        self._should_stop = False

    def stop_analysis(self):
        """Request cancellation of the analysis.

        Sets an internal flag that the run() method checks periodically.
        The thread will exit gracefully at the next check point.
        """
        self._should_stop = True

    def run(self):
        """Execute audio analysis in the background thread.

        This method is called automatically when start() is invoked on the
        worker. It loads the analyzer module, processes the audio file, and
        emits either analysis_complete or analysis_failed based on the result.

        The method checks _should_stop at multiple points and exits early
        if cancellation was requested.

        Note:
            This method should not be called directly. Use start() instead.
        """
        try:
            if self._should_stop:
                return

            from .analyzer import analyze

            print(
                f"[BackgroundAnalysis] Starting analysis for: {Path(self.audio_path).stem}"
            )

            # Run the analysis
            analysis_result = analyze(self.audio_path)

            if self._should_stop:
                return

            if analysis_result:
                self.analysis_complete.emit(self.audio_path, analysis_result)
            else:
                self.analysis_failed.emit(
                    self.audio_path, "Analysis returned no results"
                )

        except Exception as e:
            if not self._should_stop:
                self.analysis_failed.emit(self.audio_path, str(e))
