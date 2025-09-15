from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

class Player(QObject):
    # forward QMediaPlayer’s 64-bit positionChanged out
    positionChanged    = Signal("qlonglong")
    durationChanged    = Signal("qlonglong")
    mediaStatusChanged = Signal(QMediaPlayer.MediaStatus)

    def __init__(self):
        super().__init__()
        self._audio_output = QAudioOutput()
        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._audio_output)

        # now this will connect cleanly
        self._player.positionChanged.connect(self.positionChanged)
        self._player.durationChanged.connect(self.durationChanged)
        self._player.mediaStatusChanged.connect(self.mediaStatusChanged)
        
    def setSource(self, path: str):
        # Handle both local files and HTTP/HTTPS URLs (for Plex streams)
        if path.startswith(('http://', 'https://')):
            url = QUrl(path)  # Network URL
        else:
            url = QUrl.fromLocalFile(path)  # Local file
        self._player.setSource(url)

    def play(self, path: str):
        """Load & play a new file in one call."""
        self.setSource(path)
        self._player.play()

    def pause(self):
        self._player.pause()

    def stop(self):
        self._player.stop()

    def is_playing(self):
        return self._player.playbackState() == QMediaPlayer.PlayingState

    def set_volume(self, v: float):
        """Set volume. Accepts 0.0-1.0 or 0-100."""
        try:
            if v is None:
                return
            v = float(v)
            if v > 1.5:  # assume 0-100
                v = max(0.0, min(100.0, v)) / 100.0
            v = max(0.0, min(1.0, v))
            self._audio_output.setVolume(v)
        except Exception:
            pass

    def volume(self) -> float:
        return float(self._audio_output.volume())

    def set_position(self, ms: int):
        """Seek to position in milliseconds."""
        try:
            self._player.setPosition(int(ms))
        except Exception:
            pass
    
    def set_eq_values(self, eq_values: list):
        """Set EQ values. This is a placeholder for future audio processing."""
        try:
            # Store EQ values for potential future use
            self._eq_values = eq_values
            
            # For now, we can only do basic volume compensation
            # Real EQ would require audio processing framework
            print(f"[Player] EQ values set: {eq_values}")
            
            # Basic bass/treble simulation using volume
            if len(eq_values) >= 7:
                bass = (eq_values[0] + eq_values[1]) / 2  # Average of 60Hz and 150Hz
                treble = (eq_values[5] + eq_values[6]) / 2  # Average of 6kHz and 15kHz
                
                # Note: This is just for demonstration
                # Real EQ would need proper audio filtering
                print(f"[Player] Simulated Bass: {bass:+.1f}dB, Treble: {treble:+.1f}dB")
                
        except Exception as e:
            print(f"[Player] Failed to set EQ: {e}")
    
    def get_eq_values(self) -> list:
        """Get current EQ values."""
        return getattr(self, '_eq_values', [0] * 7)
