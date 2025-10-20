"""
Audio Engine with Real-time EQ Processing (Pedalboard-based)
=============================================================

PyAudio + Pedalboard audio playback engine with 7-band parametric EQ.

Uses Spotify's battle-tested Pedalboard library for stable, professional EQ.
"""

import threading
import time
import numpy as np
from pathlib import Path
from typing import Callable

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

try:
    from pedalboard import Pedalboard, PeakFilter
    from pedalboard.io import AudioFile
    PEDALBOARD_AVAILABLE = True
except ImportError:
    PEDALBOARD_AVAILABLE = False

# EQ band center frequencies (Hz)
EQ_BANDS = [60, 150, 400, 1000, 2400, 6000, 15000]

# Chunk size for audio processing
CHUNK_SIZE = 2048


class AudioEngine:
    """Audio playback engine with real-time EQ using Pedalboard."""
    
    def __init__(self):
        """Initialize audio engine."""
        if not PYAUDIO_AVAILABLE:
            raise ImportError("PyAudio is required")
        if not PEDALBOARD_AVAILABLE:
            raise ImportError("Pedalboard is required for EQ")
        
        # PyAudio
        self.pyaudio = pyaudio.PyAudio()
        
        # Audio data
        self.audio_data: np.ndarray | None = None
        self.sample_rate: int = 44100
        self.channels: int = 2
        
        # Playback state
        self.is_playing = False
        self.is_paused = False
        self.playback_position = 0
        self.stream: pyaudio.Stream | None = None
        
        # Threading
        self.playback_thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.state_lock = threading.Lock()
        
        # Pedalboard EQ
        self.eq_gains = [0.0] * len(EQ_BANDS)  # dB values
        self.pedalboard = Pedalboard([])
        self.pedalboard_lock = threading.Lock()  # Protect pedalboard updates
        self._update_pedalboard()
        
        # Volume
        self.volume = 1.0
        
        # Callbacks
        self.position_callback: Callable[[int], None] | None = None
        self.duration_callback: Callable[[int], None] | None = None
        self.finished_callback: Callable[[], None] | None = None
    
    def _update_pedalboard(self):
        """Update Pedalboard with current EQ settings."""
        filters = []
        for freq, gain_db in zip(EQ_BANDS, self.eq_gains, strict=True):
            if abs(gain_db) > 0.1:  # Only add filter if gain is significant
                filters.append(PeakFilter(
                    cutoff_frequency_hz=freq,
                    gain_db=gain_db,
                    q=1.0
                ))
        
        # Thread-safe replacement of pedalboard
        with self.pedalboard_lock:
            self.pedalboard = Pedalboard(filters)
    
    def set_eq_band(self, band_index: int, gain_db: float):
        """Set EQ gain for a specific band."""
        if 0 <= band_index < len(EQ_BANDS):
            self.eq_gains[band_index] = gain_db
            self._update_pedalboard()
    
    def load_file(self, filepath: str) -> bool:
        """Load audio file (blocking - consider calling in thread)."""
        try:
            self.stop()
            
            # Load with pedalboard's AudioFile (supports everything)
            # NOTE: This can be slow for large files - caller should show loading indicator
            with AudioFile(filepath) as f:
                audio = f.read(f.frames)
                sample_rate = f.samplerate
            
            with self.state_lock:
                self.audio_data = audio.T  # Transpose to (frames, channels)
                self.sample_rate = int(sample_rate)
                self.channels = audio.shape[0]
                self.playback_position = 0
            
            if self.duration_callback:
                duration_ms = int((len(self.audio_data) / self.sample_rate) * 1000)
                self.duration_callback(duration_ms)
            
            print(f"[AudioEngine] Loaded: {Path(filepath).name}")
            print(f"[AudioEngine]   {self.sample_rate} Hz, {self.channels} channels, {len(self.audio_data)/self.sample_rate:.1f}s")
            return True
            
        except Exception as e:
            print(f"[AudioEngine] Failed to load {filepath}: {e}")
            return False
    
    def play(self):
        """Start playback."""
        if self.audio_data is None:
            return
        
        with self.state_lock:
            if self.is_playing and not self.is_paused:
                return  # Already playing
            
            if self.is_paused:
                # Resume from pause
                self.is_paused = False
                return
            
            # Start fresh playback
            self.is_playing = True
            self.is_paused = False
            self.stop_event.clear()
        
        # Start playback thread
        self.playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self.playback_thread.start()
    
    def pause(self):
        """Pause playback."""
        with self.state_lock:
            if self.is_playing:
                self.is_paused = True
    
    def stop(self):
        """Stop playback."""
        self.stop_event.set()
        
        with self.state_lock:
            self.is_playing = False
            self.is_paused = False
            self.playback_position = 0
        
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=1.0)
        
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
            self.stream = None
    
    def seek(self, position_ms: int):
        """Seek to position in milliseconds."""
        if self.audio_data is None:
            return
        
        position_samples = int((position_ms / 1000.0) * self.sample_rate)
        position_samples = max(0, min(position_samples, len(self.audio_data) - 1))
        
        with self.state_lock:
            self.playback_position = position_samples
    
    def get_position(self) -> int:
        """Get current position in milliseconds."""
        with self.state_lock:
            if self.audio_data is None:
                return 0
            return int((self.playback_position / self.sample_rate) * 1000)
    
    def get_duration(self) -> int:
        """Get duration in milliseconds."""
        with self.state_lock:
            if self.audio_data is None:
                return 0
            return int((len(self.audio_data) / self.sample_rate) * 1000)
    
    def set_volume(self, volume: float):
        """Set volume (0.0 to 1.0)."""
        self.volume = max(0.0, min(1.0, volume))
    
    def _playback_loop(self):
        """Main playback loop (runs in separate thread)."""
        try:
            # Open PyAudio stream
            self.stream = self.pyaudio.open(
                format=pyaudio.paFloat32,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=CHUNK_SIZE
            )
            
            while not self.stop_event.is_set():
                # Check pause
                if self.is_paused:
                    time.sleep(0.01)
                    continue
                
                with self.state_lock:
                    # Check end
                    if self.playback_position >= len(self.audio_data):
                        self.is_playing = False
                        break
                    
                    # Get chunk
                    start = self.playback_position
                    end = min(start + CHUNK_SIZE, len(self.audio_data))
                    chunk = self.audio_data[start:end].copy()
                    
                    # Update position
                    self.playback_position = end
                
                # Apply EQ with Pedalboard (outside lock for performance)
                # Use pedalboard_lock to safely access the pedalboard object
                with self.pedalboard_lock:
                    if len(self.pedalboard) > 0:
                        # Pedalboard expects (channels, frames), we have (frames, channels)
                        chunk_t = chunk.T
                        chunk_t = self.pedalboard(chunk_t, self.sample_rate)
                        chunk = chunk_t.T
                
                # Apply volume
                chunk = chunk * self.volume
                
                # Clip to prevent overflow
                chunk = np.clip(chunk, -1.0, 1.0)
                
                # Send position callback
                if self.position_callback:
                    pos_ms = int((self.playback_position / self.sample_rate) * 1000)
                    self.position_callback(pos_ms)
                
                # Write to stream
                try:
                    self.stream.write(chunk.astype(np.float32).tobytes())
                except Exception as e:
                    print(f"[AudioEngine] Stream write error: {e}")
                    break
            
            # Clean up after playback ends
            with self.state_lock:
                self.is_playing = False
            
            # Fire finished callback AFTER cleanup
            if self.finished_callback and self.playback_position >= len(self.audio_data):
                self.finished_callback()
        
        except Exception as e:
            print(f"[AudioEngine] Playback error: {e}")
            with self.state_lock:
                self.is_playing = False
        finally:
            if self.stream:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except:
                    pass
                self.stream = None
    
    def cleanup(self):
        """Cleanup resources."""
        self.stop()
        if self.pyaudio:
            self.pyaudio.terminate()
