from pathlib import Path
import shutil
import subprocess

from PySide6.QtCore import QObject, Signal, QUrl, QTimer
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from .audio_engine import AudioEngine
from .url_cache import URLCache

class Player(QObject):
    # forward AudioEngine's positionChanged/durationChanged signals
    positionChanged    = Signal("qlonglong")
    durationChanged    = Signal("qlonglong")
    mediaStatusChanged = Signal(QMediaPlayer.MediaStatus)

    def __init__(self):
        super().__init__()
        
        # Track which backend is being used for the CURRENT track
        self._current_backend = None  # Will be 'engine', 'qmedia', or 'ffplay'
        
        # URL cache for Plex streams
        self._url_cache = URLCache()
        
        # ffplay subprocess for Plex URLs (fallback if download fails)
        self._ffplay_process = None
        self._ffplay_url = None
        
        # Use AudioEngine for real EQ support
        try:
            self._engine = AudioEngine()
            self._audio_engine_available = True
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
            self._audio_engine_available = False
            
        # Always initialize QMediaPlayer (for URLs, fallback, etc.)
        self._audio_output = QAudioOutput()
        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._audio_output)
        
        # Connect QMediaPlayer signals
        self._player.positionChanged.connect(self.positionChanged)
        self._player.durationChanged.connect(self.durationChanged)
        self._player.mediaStatusChanged.connect(self.mediaStatusChanged)
        self._player.errorOccurred.connect(self._on_player_error)
        
        # Set initial volume to 50% to prevent ear damage!
        if self._audio_engine_available:
            self._engine.set_volume(0.5)
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
    
    def _on_player_error(self, error, error_string):
        """Handle QMediaPlayer errors."""
        print(f"[Player] ❌ QMediaPlayer error: {error} - {error_string}")
    
    def _update_position(self):
        """Update position from AudioEngine via timer."""
        if self._current_backend == 'engine' and self._engine.is_playing:
            position_ms = self._engine.get_position()
            self.positionChanged.emit(position_ms)
        
    def setSource(self, path: str):
        """Set the audio source - downloads URLs to cache, then loads via AudioEngine."""
        try:
            # Stop any existing playback first
            self._stop_all_backends()
            
            # Check if this is an HTTP/HTTPS URL (Plex stream)
            is_url = path.startswith(('http://', 'https://'))
            
            if is_url:
                # Try to use cached version or download
                print(f"[Player] Plex stream detected: {path[:60]}...")
                
                # Check cache first
                cached_path = self._url_cache.get_cached_path(path)
                
                if cached_path:
                    # Use cached file with AudioEngine
                    print(f"[Player] Using cached file: {cached_path.name}")
                    if self._audio_engine_available:
                        success = self._engine.load_file(str(cached_path))
                        if success:
                            self._current_backend = 'engine'
                            return True
                        else:
                            print("[Player] ❌ AudioEngine failed to load cached stream; attempting fallbacks…")
                            # Fall back to ffplay if available, else QMediaPlayer URL playback
                            if shutil.which('ffplay'):
                                self._ffplay_url = path
                                self._current_backend = 'ffplay'
                                return True
                            else:
                                print("[Player] ⚠️ ffplay not found on PATH, trying QMediaPlayer for URL…")
                                self._player.setSource(QUrl(path))
                                self._current_backend = 'qmedia'
                                return True
                else:
                    # Download and cache (blocking - could add progress bar later)
                    print("[Player] Downloading stream to cache...")
                    cached_path = self._url_cache.download_and_cache(path)
                    
                    if cached_path and self._audio_engine_available:
                        # Load cached file
                        success = self._engine.load_file(str(cached_path))
                        if success:
                            print("[Player] ✅ Stream cached and loaded successfully")
                            self._current_backend = 'engine'
                            return True
                        else:
                            print("[Player] ❌ AudioEngine failed to load downloaded stream; attempting fallbacks…")
                            if shutil.which('ffplay'):
                                self._ffplay_url = path
                                self._current_backend = 'ffplay'
                                return True
                            else:
                                print("[Player] ⚠️ ffplay not found on PATH, trying QMediaPlayer for URL…")
                                self._player.setSource(QUrl(path))
                                self._current_backend = 'qmedia'
                                return True
                
                # If download failed or AudioEngine unavailable, fall back to ffplay
                print("[Player] ⚠️ Falling back to ffplay (no EQ/volume control)")
                if shutil.which('ffplay'):
                    self._ffplay_url = path
                    self._current_backend = 'ffplay'
                    return True
                else:
                    print("[Player] ⚠️ ffplay not found on PATH, trying QMediaPlayer for URL…")
                    self._player.setSource(QUrl(path))
                    self._current_backend = 'qmedia'
                    return True
            
            # Local file - use AudioEngine directly
            if self._audio_engine_available:
                print(f"[Player] Loading local file via AudioEngine: {Path(path).name}...")
                success = self._engine.load_file(path)
                if success:
                    print("[Player] ✅ File loaded successfully")
                    self._current_backend = 'engine'
                else:
                    print("[Player] ❌ Failed to load file")
                    self._current_backend = None
                return success
            else:
                # Fallback to QMediaPlayer for local files if AudioEngine fails
                url = QUrl.fromLocalFile(path)
                print(f"[Player] Loading file via QMediaPlayer: {Path(path).name}")
                self._player.setSource(url)
                self._current_backend = 'qmedia'
                return True
        except Exception as e:
            print(f"[Player] Error loading file: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _stop_all_backends(self):
        """Stop all playback backends to ensure clean state."""
        try:
            if self._audio_engine_available:
                self._engine.stop()
                self._position_timer.stop()
        except Exception:
            pass
        
        try:
            self._stop_ffplay()
        except Exception:
            pass
        
        try:
            self._player.stop()
        except Exception:
            pass
    
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

        # Start only the selected backend and ensure others are stopped
        if self._current_backend == 'engine':
            # Extra safety: stop any alternate backends before play
            try:
                self._stop_ffplay()
            except Exception:
                pass
            try:
                self._player.stop()
            except Exception:
                pass
            self._engine.play()
            self._position_timer.start()  # Start position updates
        elif self._current_backend == 'ffplay':
            # Ensure QMediaPlayer and AudioEngine are not active
            try:
                if self._audio_engine_available:
                    self._engine.stop()
                    self._position_timer.stop()
            except Exception:
                pass
            try:
                self._player.stop()
            except Exception:
                pass
            # Use ffplay for Plex URLs
            self._start_ffplay()
        elif self._current_backend == 'qmedia':
            # Ensure ffplay and AudioEngine are not active
            try:
                self._stop_ffplay()
            except Exception:
                pass
            try:
                if self._audio_engine_available:
                    self._engine.stop()
                    self._position_timer.stop()
            except Exception:
                pass
            self._player.play()
    
    def _start_ffplay(self):
        """Start ffplay subprocess for Plex URL playback."""
        try:
            # Kill any existing ffplay process
            self._stop_ffplay()
            
            if not self._ffplay_url:
                print("[Player] ❌ No URL set for ffplay")
                return

            # Ensure ffplay is available
            if not shutil.which('ffplay'):
                print("[Player] ❌ ffplay not found in PATH; cannot play streamed URL")
                self._current_backend = None
                return

            # Start ffplay in background
            # -nodisp: no video display
            # -autoexit: exit when done
            # -loglevel quiet: suppress ffplay output
            print(f"[Player] Starting ffplay for: {self._ffplay_url[:80]}...")
            self._ffplay_process = subprocess.Popen(
                ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', self._ffplay_url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("[Player] ✅ ffplay started successfully")
        except Exception as e:
            print(f"[Player] ❌ Failed to start ffplay: {e}")
            self._current_backend = None
    
    def _stop_ffplay(self):
        """Stop ffplay subprocess."""
        if self._ffplay_process:
            try:
                self._ffplay_process.terminate()
                try:
                    self._ffplay_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self._ffplay_process.kill()
                    self._ffplay_process.wait()
            except Exception as e:
                print(f"[Player] Warning: Error stopping ffplay: {e}")
                try:
                    self._ffplay_process.kill()
                except Exception:
                    pass
            self._ffplay_process = None

    def pause(self):
        if self._current_backend == 'engine':
            self._engine.pause()
            self._position_timer.stop()
        elif self._current_backend == 'ffplay':
            # ffplay doesn't support pause via subprocess - just stop it
            self._stop_ffplay()
        elif self._current_backend == 'qmedia':
            self._player.pause()

    def stop(self):
        if self._current_backend == 'engine':
            self._engine.stop()
            self._position_timer.stop()
        elif self._current_backend == 'ffplay':
            self._stop_ffplay()
        elif self._current_backend == 'qmedia':
            self._player.stop()

    def is_playing(self):
        if self._current_backend == 'engine':
            return self._engine.is_playing and not self._engine.is_paused
        elif self._current_backend == 'ffplay':
            return self._ffplay_process is not None and self._ffplay_process.poll() is None
        elif self._current_backend == 'qmedia':
            return self._player.playbackState() == QMediaPlayer.PlayingState
        return False

    def set_volume(self, v: float):
        """Set volume. Accepts 0.0-1.0 or 0-100."""
        try:
            if v is None:
                return
            v = float(v)
            if v > 1.5:  # assume 0-100
                v = max(0.0, min(100.0, v)) / 100.0
            v = max(0.0, min(1.0, v))
            
            if self._current_backend == 'engine':
                self._engine.set_volume(v)
            elif self._current_backend == 'ffplay':
                # ffplay doesn't support volume control via subprocess
                print("[Player] ⚠️  Volume control not available for ffplay")
            elif self._current_backend == 'qmedia':
                self._audio_output.setVolume(v)
        except Exception:
            pass

    def volume(self) -> float:
        if self._current_backend == 'engine':
            return float(self._engine.volume)
        elif self._current_backend == 'qmedia':
            return float(self._audio_output.volume())
        return 0.5

    def set_position(self, ms: int):
        """Seek to position in milliseconds."""
        try:
            if self._current_backend == 'engine':
                self._engine.seek(int(ms))
            elif self._current_backend == 'ffplay':
                # ffplay doesn't support seeking via subprocess
                print("[Player] ⚠️  Seeking not available for ffplay")
            elif self._current_backend == 'qmedia':
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
            
            if self._current_backend == 'engine':
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
                print("[Player] ⚠️ EQ not available for streamed sources (using QMediaPlayer)")
                print(f"[Player] ⚠️  EQ not available (using QMediaPlayer): {eq_values}")
                
        except Exception as e:
            print(f"[Player] Failed to set EQ: {e}")
    
    def get_eq_values(self) -> list:
        """Get current EQ values."""
        return getattr(self, '_eq_values', [0] * 7)
