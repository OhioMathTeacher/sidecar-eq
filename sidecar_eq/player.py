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
        
        # Set initial volume to 50% to prevent ear damage!
        self._audio_output.setVolume(0.5)

        # now this will connect cleanly
        self._player.positionChanged.connect(self.positionChanged)
        self._player.durationChanged.connect(self.durationChanged)
        self._player.mediaStatusChanged.connect(self.mediaStatusChanged)
        
    def setSource(self, path: str):
        # Handle different path types
        if path.startswith('plex://'):
            # Plex track - generate fresh stream URL
            print(f"[Player] Attempting to play Plex track: {path}")
            url = self._get_plex_stream_url(path)
            if not url:
                print(f"[Player] ❌ Failed to get Plex stream URL for: {path}")
                return
            print(f"[Player] ✅ Got Plex stream URL")
        elif path.startswith(('http://', 'https://')):
            url = QUrl(path)  # Network URL
        else:
            url = QUrl.fromLocalFile(path)  # Local file
        self._player.setSource(url)
    
    def _get_plex_stream_url(self, plex_path: str) -> QUrl:
        """Generate fresh Plex stream URL from plex:// path.
        
        Args:
            plex_path: Format is plex://<server_name>/<track_key>
        
        Returns:
            QUrl with fresh stream URL, or None if failed
        """
        try:
            # Parse plex://downstairs/library/metadata/12345
            parts = plex_path.replace('plex://', '').split('/', 1)
            if len(parts) != 2:
                return None
            
            server_name, track_key = parts
            
            # Import here to avoid circular dependencies
            import os
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except ImportError:
                pass
            
            from plexapi.myplex import MyPlexAccount
            
            # Connect to Plex
            token = os.getenv('PLEX_TOKEN', '')
            if not token:
                print("[Player] No PLEX_TOKEN found in .env")
                return None
            
            account = MyPlexAccount(token=token)
            servers = [r for r in account.resources() if r.provides == 'server']
            if not servers:
                return None
            
            plex = servers[0].connect()
            
            # Fetch track and get fresh stream URL
            track = plex.fetchItem(track_key)
            stream_url = track.getStreamURL()
            
            return QUrl(stream_url)
            
        except Exception as e:
            print(f"[Player] Plex stream error: {e}")
            return None

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
