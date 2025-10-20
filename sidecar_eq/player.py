from pathlib import Path

from PySide6.QtCore import QObject, Signal, QUrl, QTimer
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from .audio_engine import AudioEngine

class Player(QObject):
    # forward AudioEngine's positionChanged/durationChanged signals
    positionChanged    = Signal("qlonglong")
    durationChanged    = Signal("qlonglong")
    mediaStatusChanged = Signal(QMediaPlayer.MediaStatus)

    def __init__(self):
        super().__init__()
        
        # Use AudioEngine for real EQ support
        try:
            self._engine = AudioEngine()
            self._use_audio_engine = True
            print("[Player] ✅ AudioEngine initialized - Real EQ enabled!")
            
            # Set up callbacks for position/duration updates
            self._engine.position_callback = self._on_position_changed
            self._engine.duration_callback = self._on_duration_changed
            self._engine.finished_callback = self._on_playback_finished
            
            # Timer for position updates when using AudioEngine
            self._position_timer = QTimer()
            self._position_timer.timeout.connect(self._update_position)
            self._position_timer.setInterval(100)  # Update every 100ms
            
        except Exception as e:
            print(f"[Player] ⚠️  AudioEngine unavailable: {e}")
            print("[Player] Falling back to QMediaPlayer (no EQ)")
            self._use_audio_engine = False
            
            # Fallback to QMediaPlayer
            self._audio_output = QAudioOutput()
            self._player = QMediaPlayer()
            self._player.setAudioOutput(self._audio_output)
            
            # Connect QMediaPlayer signals
            self._player.positionChanged.connect(self.positionChanged)
            self._player.durationChanged.connect(self.durationChanged)
            self._player.mediaStatusChanged.connect(self.mediaStatusChanged)
        
        # Set initial volume to 50% to prevent ear damage!
        if self._use_audio_engine:
            self._engine.set_volume(0.5)
        else:
            self._audio_output.setVolume(0.5)
    
    def _on_position_changed(self, position_ms: int):
        """Callback from AudioEngine for position updates."""
        # Note: AudioEngine calls this from playback thread, but Qt signals are thread-safe
        pass  # Position updates happen via timer instead
    
    def _on_duration_changed(self, duration_ms: int):
        """Callback from AudioEngine for duration updates."""
        self.durationChanged.emit(duration_ms)
    
    def _on_playback_finished(self):
        """Callback from AudioEngine when playback finishes."""
        self._position_timer.stop()
        self.mediaStatusChanged.emit(QMediaPlayer.MediaStatus.EndOfMedia)
    
    def _update_position(self):
        """Update position from AudioEngine via timer."""
        if self._use_audio_engine and self._engine.is_playing:
            position_ms = self._engine.get_position()
            self.positionChanged.emit(position_ms)
        
    def setSource(self, path: str):
        """Set the audio source - loads file for AudioEngine."""
        try:
            if self._use_audio_engine:
                # Show loading message (file loading can be slow)
                print(f"[Player] Loading file: {Path(path).name}...")
                success = self._engine.load_file(path)
                if success:
                    print(f"[Player] ✅ File loaded successfully")
                else:
                    print(f"[Player] ❌ Failed to load file")
                return success
            else:
                # QMediaPlayer loads asynchronously
                url = QUrl.fromLocalFile(path)
                self._player.setSource(url)
                return True
        except Exception as e:
            print(f"[Player] Error loading file: {e}")
            return False
    
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
        
        if self._use_audio_engine:
            self._engine.play()
            self._position_timer.start()  # Start position updates
        else:
            self._player.play()

    def pause(self):
        if self._use_audio_engine:
            self._engine.pause()
            self._position_timer.stop()
        else:
            self._player.pause()

    def stop(self):
        if self._use_audio_engine:
            self._engine.stop()
            self._position_timer.stop()
        else:
            self._player.stop()

    def is_playing(self):
        if self._use_audio_engine:
            return self._engine.is_playing and not self._engine.is_paused
        else:
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
            
            if self._use_audio_engine:
                self._engine.set_volume(v)
            else:
                self._audio_output.setVolume(v)
        except Exception:
            pass

    def volume(self) -> float:
        if self._use_audio_engine:
            return float(self._engine.volume)
        else:
            return float(self._audio_output.volume())

    def set_position(self, ms: int):
        """Seek to position in milliseconds."""
        try:
            if self._use_audio_engine:
                self._engine.seek(int(ms))
            else:
                self._player.setPosition(int(ms))
        except Exception:
            pass
    
    def set_eq_values(self, eq_values: list):
        """Set EQ values for real-time audio processing.
        
        Args:
            eq_values: List of slider values (0-200, where 100 = flat/0dB)
        """
        try:
            # Store EQ values
            self._eq_values = eq_values
            
            if self._use_audio_engine:
                # Apply REAL EQ! 🎉
                if len(eq_values) >= 7:
                    for band_index, slider_value in enumerate(eq_values[:7]):
                        # Convert slider value (0-200) to dB (-10 to +10)
                        # slider 0 = -10dB, slider 100 = 0dB, slider 200 = +10dB
                        gain_db = (slider_value - 100) / 10.0
                        self._engine.set_eq_band(band_index, gain_db)
                    print(f"[Player] ✅ Real EQ applied: {eq_values[:7]}")
            else:
                # QMediaPlayer fallback - just log for now
                print(f"[Player] ⚠️  EQ not available (using QMediaPlayer): {eq_values}")
                
        except Exception as e:
            print(f"[Player] Failed to set EQ: {e}")
    
    def get_eq_values(self) -> list:
        """Get current EQ values."""
        return getattr(self, '_eq_values', [0] * 7)
