"""
Audio Engine with Real-time EQ Processing
==========================================

PyAudio + Pedalboard-based audio playback engine with 7-band parametric EQ.

Features:
- File playback (WAV, MP3, FLAC, etc.)
- Streaming support (HTTP URLs, Plex)
- Real-time 7-band parametric EQ (using Spotify's Pedalboard)
- Thread-safe playback control
- Position/duration reporting

EQ Bands (Hz):
    60, 150, 400, 1000, 2400, 6000, 15000
"""

import threading
import queue
import time
import numpy as np
from pathlib import Path
from typing import Optional, Callable

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    print("⚠️  PyAudio not available - audio playback disabled")

try:
    from pedalboard import Pedalboard, PeakFilter
    from pedalboard.io import AudioFile
    PEDALBOARD_AVAILABLE = True
except ImportError:
    PEDALBOARD_AVAILABLE = False
    print("⚠️  pedalboard not available - EQ disabled")

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False
    print("⚠️  soundfile not available - WAV/FLAC support limited")


# EQ band center frequencies (Hz)
EQ_BANDS = [60, 150, 400, 1000, 2400, 6000, 15000]


class AudioEngine:
    """Audio playback engine with real-time EQ processing.
    
    This engine handles:
    - Audio file loading and decoding
    - Real-time playback with PyAudio
    - 7-band parametric EQ processing
    - Thread-safe control (play/pause/stop/seek)
    - Position/duration callbacks
    """
    
    def __init__(self):
        """Initialize audio engine."""
        if not PYAUDIO_AVAILABLE:
            raise ImportError("PyAudio is required for audio playback")
        if not SCIPY_AVAILABLE:
            raise ImportError("scipy is required for EQ processing")
        
        # PyAudio instance
        self.pyaudio = pyaudio.PyAudio()
        
        # Audio data
        self.audio_data: Optional[np.ndarray] = None
        self.sample_rate: int = 44100
        self.channels: int = 2
        
        # Playback state
        self.is_playing = False
        self.is_paused = False
        self.playback_position = 0  # Current position in samples
        self.stream: Optional[pyaudio.Stream] = None
        
        # Threading
        self.playback_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.state_lock = threading.Lock()
        
        # EQ settings (dB values for each band)
        self.eq_gains = [0.0] * len(EQ_BANDS)  # Start flat
        self.eq_filters = []  # Filter coefficients (b, a) for each band
        self.eq_filter_states = []  # Filter states (zi) for continuous filtering
        self._update_eq_filters()
        
        # Volume
        self.volume = 1.0  # 0.0 to 1.0
        
        # Callbacks
        self.position_callback: Optional[Callable[[int], None]] = None
        self.duration_callback: Optional[Callable[[int], None]] = None
        self.finished_callback: Optional[Callable[[], None]] = None
    
    def _design_peaking_eq(self, center_freq: float, gain_db: float, q: float = 1.0):
        """Design a parametric peaking EQ filter.
        
        Args:
            center_freq: Center frequency in Hz
            gain_db: Gain in dB (positive = boost, negative = cut)
            q: Q factor (bandwidth), typically 0.7-1.4
        
        Returns:
            (b, a): Filter coefficients
        """
        # Convert gain from dB to linear
        A = 10 ** (gain_db / 40)
        
        # Calculate angular frequency
        w0 = 2 * np.pi * center_freq / self.sample_rate
        
        # Calculate alpha (bandwidth parameter)
        alpha = np.sin(w0) / (2 * q)
        
        # Peaking EQ filter coefficients
        b0 = 1 + alpha * A
        b1 = -2 * np.cos(w0)
        b2 = 1 - alpha * A
        a0 = 1 + alpha / A
        a1 = -2 * np.cos(w0)
        a2 = 1 - alpha / A
        
        # Normalize by a0
        b = np.array([b0, b1, b2]) / a0
        a = np.array([1, a1, a2]) / a0
        
        return b, a
    
    def _update_eq_filters(self):
        """Update EQ filter coefficients based on current gains."""
        self.eq_filters = []
        self.eq_filter_states = []
        
        # Reset channel states when EQ changes
        if hasattr(self, '_channel_states'):
            self._channel_states = {}
        
        for freq, gain in zip(EQ_BANDS, self.eq_gains):
            if abs(gain) < 0.1:  # Skip if gain is basically flat
                self.eq_filters.append(None)
                self.eq_filter_states.append(None)
            else:
                b, a = self._design_peaking_eq(freq, gain)
                self.eq_filters.append((b, a))
                # Initialize filter state - will be populated per-channel on first use
                self.eq_filter_states.append(None)
    
    def _apply_eq(self, audio: np.ndarray) -> np.ndarray:
        """Apply EQ filters to audio buffer with state continuity.
        
        Args:
            audio: Audio samples (frames x channels)
        
        Returns:
            Filtered audio (same shape)
        """
        if audio.size == 0:
            return audio
        
        # Initialize channel states if needed
        if not hasattr(self, '_channel_states'):
            self._channel_states = {}
        
        # Process each channel separately
        if audio.ndim == 2:
            filtered = audio.copy()
            for ch in range(audio.shape[1]):
                channel_data = audio[:, ch]
                
                # Apply each EQ band in cascade
                for band_idx, filter_coeffs in enumerate(self.eq_filters):
                    if filter_coeffs is not None:
                        b, a = filter_coeffs
                        
                        # Get or initialize state for this channel and band
                        state_key = (ch, band_idx)
                        if state_key not in self._channel_states:
                            self._channel_states[state_key] = signal.lfilter_zi(b, a) * channel_data[0]
                        
                        # Apply filter with state
                        channel_data, self._channel_states[state_key] = signal.lfilter(
                            b, a, channel_data, zi=self._channel_states[state_key]
                        )
                
                filtered[:, ch] = channel_data
        else:
            # Mono
            filtered = audio.copy()
            for band_idx, filter_coeffs in enumerate(self.eq_filters):
                if filter_coeffs is not None:
                    b, a = filter_coeffs
                    
                    # Get or initialize state
                    state_key = (0, band_idx)
                    if state_key not in self._channel_states:
                        self._channel_states[state_key] = signal.lfilter_zi(b, a) * filtered[0]
                    
                    # Apply filter with state
                    filtered, self._channel_states[state_key] = signal.lfilter(
                        b, a, filtered, zi=self._channel_states[state_key]
                    )
        
        return filtered
    
    def _normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """Normalize audio to prevent clipping.
        
        Args:
            audio: Audio samples
        
        Returns:
            Normalized audio
        """
        peak = np.abs(audio).max()
        if peak > 1.0:
            return audio / peak
        return audio
    
    def load_file(self, filepath: str) -> bool:
        """Load audio file.
        
        Args:
            filepath: Path to audio file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Stop current playback
            self.stop()
            
            # Load audio using soundfile
            if SOUNDFILE_AVAILABLE:
                audio, sample_rate = sf.read(filepath, dtype='float32')
            else:
                # Fallback - would need librosa or other library
                raise ImportError("soundfile required for loading audio files")
            
            with self.state_lock:
                self.audio_data = audio
                self.sample_rate = sample_rate
                self.channels = audio.shape[1] if audio.ndim == 2 else 1
                self.playback_position = 0
                
                # Update EQ filters for new sample rate
                self._update_eq_filters()
            
            # Notify duration
            if self.duration_callback:
                duration_ms = int((len(audio) / sample_rate) * 1000)
                self.duration_callback(duration_ms)
            
            print(f"✅ Loaded: {Path(filepath).name}")
            print(f"   {sample_rate} Hz, {self.channels} channels, {len(audio)/sample_rate:.1f}s")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to load {filepath}: {e}")
            return False
    
    def _playback_loop(self):
        """Main playback loop (runs in separate thread)."""
        CHUNK_SIZE = 1024  # Frames per buffer
        
        try:
            # Open PyAudio stream
            self.stream = self.pyaudio.open(
                format=pyaudio.paFloat32,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=CHUNK_SIZE,
                stream_callback=None  # We'll write manually for better control
            )
            
            while not self.stop_event.is_set():
                # Check if paused
                if self.is_paused:
                    time.sleep(0.01)
                    continue
                
                with self.state_lock:
                    # Check if we've reached the end
                    if self.playback_position >= len(self.audio_data):
                        self.is_playing = False
                        if self.finished_callback:
                            self.finished_callback()
                        break
                    
                    # Get next chunk
                    start = self.playback_position
                    end = min(start + CHUNK_SIZE, len(self.audio_data))
                    
                    # Extract audio chunk
                    if self.audio_data.ndim == 2:
                        chunk = self.audio_data[start:end, :]
                    else:
                        chunk = self.audio_data[start:end]
                    
                    # Apply EQ
                    chunk = self._apply_eq(chunk)
                    
                    # Apply volume
                    chunk = chunk * self.volume
                    
                    # Normalize to prevent clipping
                    chunk = self._normalize_audio(chunk)
                    
                    # Update position
                    self.playback_position = end
                
                # Write to stream
                try:
                    self.stream.write(chunk.astype(np.float32).tobytes())
                except Exception as e:
                    print(f"⚠️  Stream write error: {e}")
                    break
                
                # Notify position (every ~100ms)
                if self.position_callback and self.playback_position % (self.sample_rate // 10) < CHUNK_SIZE:
                    position_ms = int((self.playback_position / self.sample_rate) * 1000)
                    self.position_callback(position_ms)
        
        finally:
            # Clean up stream
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
    
    def play(self) -> bool:
        """Start or resume playback.
        
        Returns:
            True if playback started, False otherwise
        """
        if self.audio_data is None:
            print("⚠️  No audio loaded")
            return False
        
        with self.state_lock:
            if self.is_playing and not self.is_paused:
                return True  # Already playing
            
            self.is_playing = True
            self.is_paused = False
            
            # Start playback thread if not running
            if self.playback_thread is None or not self.playback_thread.is_alive():
                self.stop_event.clear()
                self.playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
                self.playback_thread.start()
        
        return True
    
    def pause(self):
        """Pause playback."""
        with self.state_lock:
            if self.is_playing:
                self.is_paused = True
    
    def stop(self):
        """Stop playback and reset position."""
        with self.state_lock:
            self.is_playing = False
            self.is_paused = False
            self.playback_position = 0
        
        # Signal thread to stop
        self.stop_event.set()
        
        # Wait for thread to finish
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=1.0)
    
    def seek(self, position_ms: int):
        """Seek to position.
        
        Args:
            position_ms: Position in milliseconds
        """
        if self.audio_data is None:
            return
        
        position_samples = int((position_ms / 1000.0) * self.sample_rate)
        
        with self.state_lock:
            self.playback_position = max(0, min(position_samples, len(self.audio_data)))
    
    def set_volume(self, volume: float):
        """Set playback volume.
        
        Args:
            volume: Volume level (0.0 to 1.0)
        """
        with self.state_lock:
            self.volume = max(0.0, min(1.0, volume))
    
    def set_eq_band(self, band_index: int, gain_db: float):
        """Set EQ gain for a specific band.
        
        Args:
            band_index: Band index (0-6)
            gain_db: Gain in dB (-12 to +12 recommended)
        """
        if 0 <= band_index < len(EQ_BANDS):
            with self.state_lock:
                self.eq_gains[band_index] = gain_db
                self._update_eq_filters()
    
    def get_position_ms(self) -> int:
        """Get current playback position in milliseconds."""
        with self.state_lock:
            if self.audio_data is None:
                return 0
            return int((self.playback_position / self.sample_rate) * 1000)
    
    def get_duration_ms(self) -> int:
        """Get total duration in milliseconds."""
        with self.state_lock:
            if self.audio_data is None:
                return 0
            return int((len(self.audio_data) / self.sample_rate) * 1000)
    
    def cleanup(self):
        """Clean up resources."""
        self.stop()
        if self.pyaudio:
            self.pyaudio.terminate()
