"""EQ management for Sidecar EQ.

This module handles all EQ-related functionality including:
- Loading/saving EQ settings per track
- Applying EQ settings to sliders
- Converting between dB and slider values
- Auto-saving EQ changes
"""

from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QSlider, QLabel


class EQManager:
    """Manages EQ settings and persistence."""
    
    # 7-band EQ frequencies
    EQ_BANDS_HZ = [60, 150, 400, 1000, 2400, 6000, 15000]
    EQ_BAND_LABELS = ["60 Hz", "150 Hz", "400 Hz", "1 kHz", "2.4 kHz", "6 kHz", "15 kHz"]
    
    def __init__(self, sliders: List, value_labels: List, store_module):
        """Initialize EQ manager.
        
        Args:
            sliders: List of 7 EQ slider widgets (BeamSlider instances)
            value_labels: List of 7 QLabel widgets for displaying dB values
            store_module: Reference to the store module for persistence
        """
        self.sliders = sliders
        self.value_labels = value_labels
        self.store = store_module
        
    def db_to_slider_value(self, db: float) -> int:
        """Convert dB value to BeamSlider 0-100 scale.
        
        Args:
            db: Decibel value (-12 to +12)
            
        Returns:
            Slider value (0 to 100)
        """
        # -12dB -> 0, 0dB -> 50, +12dB -> 100
        db_clamped = max(-12, min(12, db))
        return int(round(((db_clamped + 12) / 24.0) * 100))
    
    def slider_value_to_db(self, slider_value: int) -> float:
        """Convert BeamSlider 0-100 value to dB.
        
        Args:
            slider_value: Slider position (0 to 100)
            
        Returns:
            Decibel value (-12 to +12)
        """
        # 0 -> -12dB, 50 -> 0dB, 100 -> +12dB
        value_clamped = max(0, min(100, slider_value))
        return (value_clamped / 100.0) * 24 - 12
    
    def apply_eq_settings(self, gains_db: List[float]):
        """Apply EQ settings to the sliders and update value labels.
        
        Args:
            gains_db: List of EQ gains in dB (-12 to +12 range)
        """
        try:
            if len(gains_db) < len(self.sliders):
                print(f"[EQManager] Warning: Expected {len(self.sliders)} EQ values, got {len(gains_db)}")
                return
                
            for i, slider in enumerate(self.sliders):
                if i < len(gains_db):
                    db_value = max(-12, min(12, float(gains_db[i])))
                    slider_value = self.db_to_slider_value(db_value)
                    
                    # Block signals to prevent saving during load
                    slider.blockSignals(True)
                    slider.setValue(slider_value)
                    slider.blockSignals(False)
                    
                    # Update the value label
                    if i < len(self.value_labels):
                        self.value_labels[i].setText(f"{int(db_value):+d}")
                        
            print(f"[EQManager] Applied EQ: {[f'{g:+.1f}dB' for g in gains_db[:len(self.sliders)]]}")
        except Exception as e:
            print(f"[EQManager] Failed to apply EQ: {e}")
    
    def get_current_eq_values(self) -> List[float]:
        """Get current EQ values from sliders in dB.
        
        Returns:
            List of 7 dB values
        """
        return [self.slider_value_to_db(slider.value()) for slider in self.sliders]
    
    def update_value_label(self, slider_index: int, db_value: float):
        """Update a single EQ value label.
        
        Args:
            slider_index: Index of the slider (0-6)
            db_value: Decibel value to display
        """
        if 0 <= slider_index < len(self.value_labels):
            self.value_labels[slider_index].setText(f"{int(db_value):+d}")
    
    def save_eq_for_track(self, track_path: str, eq_values_db: List[float]) -> bool:
        """Save EQ settings for a specific track.
        
        Args:
            track_path: Path to the audio file
            eq_values_db: List of 7 EQ values in dB
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Load existing data or create new
            existing_data = self.store.get_record(track_path) or {}
            
            # Update EQ data
            existing_data['eq_data'] = eq_values_db
            
            # Save back
            self.store.put_record(track_path, existing_data)
            print(f"[EQManager] 💾 Saved EQ for track: {track_path}")
            return True
        except Exception as e:
            print(f"[EQManager] Failed to save EQ: {e}")
            return False
    
    def load_eq_for_track(self, track_path: str) -> Optional[List[float]]:
        """Load EQ settings for a specific track.
        
        Args:
            track_path: Path to the audio file
            
        Returns:
            List of 7 EQ values in dB, or None if not found
        """
        try:
            data = self.store.get_record(track_path)
            if data and 'eq_data' in data:
                eq_data = data['eq_data']
                if isinstance(eq_data, list) and len(eq_data) >= 7:
                    return eq_data[:7]
            return None
        except Exception as e:
            print(f"[EQManager] Failed to load EQ: {e}")
            return None
    
    def set_neutral_eq(self):
        """Set all EQ sliders to 0 dB (neutral/flat)."""
        neutral_db = [0.0] * 7
        self.apply_eq_settings(neutral_db)
    
    def set_default_eq(self, db_value: float = 4.8):
        """Set all EQ sliders to a default boost value.
        
        Args:
            db_value: Default dB value (default +4.8dB for 80% slider position)
        """
        default_db = [db_value] * 7
        self.apply_eq_settings(default_db)
