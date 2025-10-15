"""Volume management for Sidecar EQ.

This module handles volume control, persistence, and analysis-based suggestions.
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..player import Player


class VolumeManager:
    """Manages volume settings and persistence."""
    
    def __init__(self, volume_slider, volume_label, player, store_module):
        """Initialize volume manager.
        
        Args:
            volume_slider: BeamSlider widget for volume control
            volume_label: QLabel widget for displaying volume value
            player: Player instance for audio playback
            store_module: Reference to the store module for persistence
        """
        self.slider = volume_slider
        self.label = volume_label
        self.player = player
        self.store = store_module
        
    def set_volume(self, volume_percent: int, apply_to_player: bool = True, save: bool = False):
        """Set volume level.
        
        Args:
            volume_percent: Volume level (0-100)
            apply_to_player: Whether to apply to audio player
            save: Whether to trigger save (should be False when loading)
        """
        try:
            volume = max(0, min(100, volume_percent))
            
            # Update slider
            if not save:
                self.slider.blockSignals(True)
            self.slider.setValue(volume)
            if not save:
                self.slider.blockSignals(False)
            
            # Update label (0-10 scale for display)
            self.label.setText(f"{(volume / 10.0):.1f}")
            
            # Apply to player
            if apply_to_player and hasattr(self.player, 'set_volume'):
                self.player.set_volume(volume / 100.0)
                
            print(f"[VolumeManager] Set volume to {volume}%")
        except Exception as e:
            print(f"[VolumeManager] Failed to set volume: {e}")
    
    def get_volume(self) -> int:
        """Get current volume level.
        
        Returns:
            Current volume (0-100)
        """
        return self.slider.value()
    
    def save_volume_for_track(self, track_path: str, volume_value: int) -> bool:
        """Save volume setting for a specific track.
        
        Args:
            track_path: Path to the audio file
            volume_value: Volume level (0-100)
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Load existing data or create new
            existing_data = self.store.get_record(track_path) or {}
            
            # Update volume setting
            existing_data['suggested_volume'] = volume_value
            
            # Save back
            self.store.put_record(track_path, existing_data)
            print(f"[VolumeManager] 💾 Saved volume {volume_value}% for: {track_path}")
            return True
        except Exception as e:
            print(f"[VolumeManager] Failed to save volume: {e}")
            return False
    
    def load_volume_for_track(self, track_path: str) -> Optional[int]:
        """Load volume setting for a specific track.
        
        Args:
            track_path: Path to the audio file
            
        Returns:
            Volume level (0-100), or None if not found
        """
        try:
            data = self.store.get_record(track_path)
            if data and 'suggested_volume' in data:
                volume = data['suggested_volume']
                if volume is not None and isinstance(volume, (int, float)):
                    return int(max(0, min(100, volume)))
            return None
        except Exception as e:
            print(f"[VolumeManager] Failed to load volume: {e}")
            return None
