"""Audio analysis for automatic EQ suggestions based on spectral content."""

import numpy as np
import librosa
from pathlib import Path
from typing import Dict, List, Tuple

class AudioAnalyzer:
    """Analyzes audio files for spectral content and EQ suggestions."""
    
    # Standard 7-band EQ frequencies matching the UI display
    EQ_BANDS = [60, 150, 400, 1000, 2400, 6000, 15000]
    
    def __init__(self):
        self.sample_rate = 22050  # Lower rate for faster processing
    
    def analyze_file(self, audio_path: str) -> Dict:
        """
        Analyze an audio file and return suggested EQ settings.
        
        Returns:
            dict: {
                'eq_settings': List[int],  # -12 to +12 for each band
                'bass_energy': float,      # 0-1 representing bass content
                'treble_energy': float,    # 0-1 representing treble content
                'dynamic_range': float,    # dB of dynamic range
                'peak_frequency': float,   # Hz of dominant frequency
                'analysis_version': str    # For future compatibility
            }
        """
        try:
            print(f"[Analyzer] Analyzing {Path(audio_path).name}...")
            
            # Load audio file (librosa handles most formats)
            y, sr = librosa.load(audio_path, sr=self.sample_rate, duration=30.0)  # Analyze first 30 seconds
            
            # Compute spectral features
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            
            # Calculate frequency band energies
            stft = librosa.stft(y)
            magnitude = np.abs(stft)
            
            # Map frequency bins to our EQ bands
            freqs = librosa.fft_frequencies(sr=sr)
            eq_energies = self._calculate_band_energies(magnitude, freqs)
            
            # Analyze bass vs treble balance
            bass_energy = self._calculate_bass_energy(eq_energies)
            treble_energy = self._calculate_treble_energy(eq_energies)
            
            # Calculate dynamic range
            dynamic_range = self._calculate_dynamic_range(y)
            
            # Calculate loudness metrics (key for volume normalization!)
            loudness_data = self._calculate_loudness_metrics(y, sr)
            
            # Find peak frequency
            peak_frequency = self._find_peak_frequency(magnitude, freqs)
            
            # Generate EQ suggestions based on analysis
            eq_settings = self._generate_eq_suggestions(eq_energies, bass_energy, treble_energy)
            
            print(f"[Analyzer] Bass: {bass_energy:.2f}, Treble: {treble_energy:.2f}, Peak: {peak_frequency:.1f}Hz")
            
            return {
                'eq_settings': eq_settings,
                'bass_energy': bass_energy,
                'treble_energy': treble_energy,
                'dynamic_range': dynamic_range,
                'peak_frequency': peak_frequency,
                'band_energies': eq_energies.tolist(),
                # Loudness/Volume Analysis (NEW!)
                'rms_db': loudness_data['rms_db'],
                'peak_db': loudness_data['peak_db'], 
                'loudness_lufs': loudness_data['loudness_lufs'],
                'suggested_volume': loudness_data['suggested_volume'],
                'analysis_version': '1.1'
            }
            
        except Exception as e:
            print(f"[Analyzer] Analysis failed for {audio_path}: {e}")
            # Return neutral settings on failure
            return {
                'eq_settings': [0] * len(self.EQ_BANDS),
                'bass_energy': 0.5,
                'treble_energy': 0.5,
                'dynamic_range': 0.0,
                'peak_frequency': 1000.0,
                'band_energies': [0.1] * len(self.EQ_BANDS),
                'analysis_version': '1.0'
            }
    
    def _calculate_band_energies(self, magnitude: np.ndarray, freqs: np.ndarray) -> np.ndarray:
        """Calculate energy in each EQ frequency band."""
        band_energies = np.zeros(len(self.EQ_BANDS))
        
        for i, center_freq in enumerate(self.EQ_BANDS):
            # Define band boundaries (octave bands)
            if i == 0:
                low_freq = 0
            else:
                low_freq = (self.EQ_BANDS[i-1] + center_freq) / 2
            
            if i == len(self.EQ_BANDS) - 1:
                high_freq = freqs[-1]
            else:
                high_freq = (center_freq + self.EQ_BANDS[i+1]) / 2
            
            # Find frequency bins in this band
            band_mask = (freqs >= low_freq) & (freqs <= high_freq)
            if np.any(band_mask):
                band_energies[i] = np.mean(magnitude[band_mask])
        
        return band_energies
    
    def _calculate_bass_energy(self, band_energies: np.ndarray) -> float:
        """Calculate normalized bass energy (0-1)."""
        # Bass: roughly 31-250 Hz (first 4 bands)
        bass_bands = band_energies[:4]
        total_energy = np.sum(band_energies)
        if total_energy > 0:
            return np.sum(bass_bands) / total_energy
        return 0.5
    
    def _calculate_treble_energy(self, band_energies: np.ndarray) -> float:
        """Calculate normalized treble energy (0-1)."""
        # Treble: roughly 4kHz+ (last 3 bands)
        treble_bands = band_energies[-3:]
        total_energy = np.sum(band_energies)
        if total_energy > 0:
            return np.sum(treble_bands) / total_energy
        return 0.5
    
    def _calculate_dynamic_range(self, y: np.ndarray) -> float:
        """Calculate dynamic range in dB."""
        if len(y) == 0:
            return 0.0
        
        # Calculate RMS energy in small windows
        window_size = 2048
        rms_values = []
        for i in range(0, len(y) - window_size, window_size // 2):
            window = y[i:i + window_size]
            rms = np.sqrt(np.mean(window ** 2))
            if rms > 0:
                rms_values.append(20 * np.log10(rms))
        
        if len(rms_values) < 2:
            return 0.0
        
        return np.max(rms_values) - np.min(rms_values)
    
    def _find_peak_frequency(self, magnitude: np.ndarray, freqs: np.ndarray) -> float:
        """Find the frequency with highest average energy."""
        avg_magnitude = np.mean(magnitude, axis=1)
        peak_idx = np.argmax(avg_magnitude)
        return freqs[peak_idx]
    
    def _calculate_loudness_metrics(self, y: np.ndarray, sr: int) -> Dict:
        """
        Calculate comprehensive loudness metrics for volume normalization.
        
        Returns:
            dict: {
                'rms_db': RMS level in dB
                'peak_db': Peak level in dB  
                'loudness_lufs': Perceived loudness (LUFS approximation)
                'suggested_volume': Suggested volume (0-100) for normalization
            }
        """
        if len(y) == 0:
            return {'rms_db': -60, 'peak_db': -60, 'loudness_lufs': -23, 'suggested_volume': 70}
        
        # RMS (Root Mean Square) - average energy
        rms = np.sqrt(np.mean(y ** 2))
        rms_db = 20 * np.log10(rms + 1e-10)  # Add small value to avoid log(0)
        
        # Peak level
        peak = np.max(np.abs(y))
        peak_db = 20 * np.log10(peak + 1e-10)
        
        # Simplified LUFS calculation (perceived loudness)
        # Real LUFS requires K-weighting filter, but this approximation works well
        loudness_lufs = self._estimate_lufs(y, sr)
        
        # Suggest volume based on loudness analysis
        suggested_volume = self._calculate_suggested_volume(rms_db, peak_db, loudness_lufs)
        
        print(f"[Analyzer] Loudness: {loudness_lufs:.1f} LUFS, Peak: {peak_db:.1f}dB, Suggested vol: {suggested_volume}")
        
        return {
            'rms_db': round(rms_db, 2),
            'peak_db': round(peak_db, 2), 
            'loudness_lufs': round(loudness_lufs, 2),
            'suggested_volume': suggested_volume
        }
    
    def _estimate_lufs(self, y: np.ndarray, sr: int) -> float:
        """
        Estimate LUFS (Loudness Units relative to Full Scale).
        This is a simplified version - real LUFS needs K-weighting.
        """
        # Use overlapping windows to measure gated loudness
        window_size = int(0.4 * sr)  # 400ms windows
        hop_size = window_size // 4
        
        loudness_values = []
        for i in range(0, len(y) - window_size, hop_size):
            window = y[i:i + window_size]
            
            # Calculate mean square with simple high-pass filter (approximate K-weighting)
            # Real K-weighting is complex, this is a reasonable approximation
            filtered = self._simple_highpass(window, sr)
            mean_square = np.mean(filtered ** 2)
            
            if mean_square > 0:
                loudness_block = -0.691 + 10 * np.log10(mean_square)
                loudness_values.append(loudness_block)
        
        if not loudness_values:
            return -23.0  # Standard target loudness
        
        # Relative gating (simplified)
        loudness_values = np.array(loudness_values)
        # Remove blocks below -70 LUFS (absolute gate)
        gated = loudness_values[loudness_values > -70]
        
        if len(gated) == 0:
            return -23.0
        
        return float(np.mean(gated))
    
    def _simple_highpass(self, y: np.ndarray, sr: int, cutoff: float = 38.0) -> np.ndarray:
        """Simple high-pass filter approximation for K-weighting."""
        from scipy import signal
        
        # Simple butterworth high-pass filter
        nyquist = sr / 2
        normalized_cutoff = cutoff / nyquist
        b, a = signal.butter(2, normalized_cutoff, btype='high')
        return signal.filtfilt(b, a, y)
    
    def _calculate_suggested_volume(self, rms_db: float, peak_db: float, loudness_lufs: float) -> int:
        """
        Calculate suggested volume (0-100) based on loudness analysis.
        
        Target: -23 LUFS (broadcast standard) should map to ~75% volume
        Louder tracks get lower suggested volume, quieter tracks get higher volume
        """
        target_lufs = -23.0  # EBU R128 standard
        target_volume = 75   # Target volume for properly mastered tracks
        
        # Calculate offset from target
        loudness_offset = loudness_lufs - target_lufs
        
        # Adjust volume recommendation (roughly 2 LUFS = 10% volume change)
        suggested = target_volume - (loudness_offset * 5)
        
        # Safety limits and peak considerations
        if peak_db > -3:  # Very hot master, reduce volume more
            suggested -= 10
        elif peak_db < -12:  # Conservative master, can go louder
            suggested += 5
        
        # Clamp to reasonable range
        return max(30, min(90, int(suggested)))
    
    def _generate_eq_suggestions(self, band_energies: np.ndarray, bass_energy: float, treble_energy: float) -> List[int]:
        """
        Generate EQ suggestions based on spectral analysis.
        
        Philosophy:
        - If bass-heavy: reduce bass, boost mids/treble for balance
        - If treble-heavy: reduce harsh frequencies, boost warmth
        - Aim for pleasant, balanced sound
        """
        eq_settings = [0] * len(self.EQ_BANDS)
        
        # Normalize band energies
        if np.sum(band_energies) > 0:
            normalized_bands = band_energies / np.sum(band_energies)
        else:
            normalized_bands = np.ones(len(self.EQ_BANDS)) / len(self.EQ_BANDS)
        
        # Expected "balanced" energy distribution for 7-band EQ (slightly warm)
        # [60Hz, 150Hz, 400Hz, 1kHz, 2.4kHz, 6kHz, 15kHz]
        target_distribution = np.array([0.16, 0.15, 0.14, 0.13, 0.12, 0.15, 0.15])
        
        # Calculate how much each band deviates from target
        deviation = normalized_bands - target_distribution
        
        # Convert deviations to EQ adjustments (with limits)
        for i, dev in enumerate(deviation):
            if dev > 0.02:  # Too much energy in this band
                eq_settings[i] = max(-12, int(-dev * 200))  # Reduce
            elif dev < -0.02:  # Too little energy in this band
                eq_settings[i] = min(12, int(-dev * 200))   # Boost
        
        # Additional adjustments based on overall character
        if bass_energy > 0.4:  # Very bass-heavy
            eq_settings[0] = min(eq_settings[0], -2)  # Reduce sub-bass
            eq_settings[1] = min(eq_settings[1], -1)  # Reduce bass
        
        if treble_energy > 0.3:  # Very treble-heavy
            eq_settings[-1] = min(eq_settings[-1], -2)  # Reduce high treble
            eq_settings[-2] = min(eq_settings[-2], -1)  # Reduce upper treble
        
        return eq_settings


# Create a global analyzer instance
_analyzer = AudioAnalyzer()

def analyze(path: str) -> dict:
    """
    Analyze audio file and return EQ suggestion in the expected format.
    
    This maintains compatibility with existing code while adding real analysis.
    """
    try:
        # Get full analysis
        result = _analyzer.analyze_file(path)
        
        # Return in the expected format
        return {
            "bands_hz": _analyzer.EQ_BANDS,
            "gains_db": result['eq_settings'],
            "preamp_db": -3.0,  # Conservative preamp to avoid clipping
            "analysis_data": result  # Include full analysis for future use
        }
    except Exception as e:
        print(f"[Analyzer] Fallback to neutral EQ: {e}")
        # Fallback to neutral settings
        return {
            "bands_hz": [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000],
            "gains_db": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            "preamp_db": -3.0,
        }
