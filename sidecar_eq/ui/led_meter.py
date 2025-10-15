"""LED-style meter visualization for frequency bands."""

import random
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QLinearGradient
from PySide6.QtWidgets import QWidget


class LEDMeter(QWidget):
    """LED-style vertical meter showing frequency band levels.
    
    Displays a vertical bar graph with LED segments, similar to classic
    audio equipment. Can be driven by real-time audio analysis or simulated.
    
    Args:
        parent: Parent widget (optional).
        num_segments: Number of LED segments (default 20).
        color_scheme: Color scheme - 'green', 'blue', 'rainbow' (default 'green').
    """
    
    def __init__(self, parent=None, num_segments=20, color_scheme='green'):
        super().__init__(parent)
        self._num_segments = num_segments
        self._level = 0.0  # Current level 0.0 to 1.0
        self._peak_level = 0.0  # Peak hold level
        self._peak_decay = 0.02  # Peak decay per frame
        self._color_scheme = color_scheme
        
        # Simulation mode for demo
        self._simulation_enabled = False
        self._sim_timer = QTimer()
        self._sim_timer.timeout.connect(self._simulate_update)
        
        self.setMinimumHeight(100)
        self.setMaximumWidth(20)
    
    def set_level(self, level: float):
        """Set the current meter level.
        
        Args:
            level: Level from 0.0 (silent) to 1.0 (peak).
        """
        self._level = max(0.0, min(1.0, level))
        
        # Update peak hold
        if self._level > self._peak_level:
            self._peak_level = self._level
        else:
            # Decay peak slowly
            self._peak_level = max(self._level, self._peak_level - self._peak_decay)
        
        self.update()
    
    def enable_simulation(self, enabled: bool):
        """Enable/disable simulation mode for demo purposes.
        
        Args:
            enabled: True to enable simulation, False to disable.
        """
        self._simulation_enabled = enabled
        if enabled:
            self._sim_timer.start(50)  # 20 FPS
        else:
            self._sim_timer.stop()
            # Clear the meter when stopping
            self.clear()
    
    def clear(self):
        """Clear the meter to zero (reset level and peak)."""
        self._level = 0.0
        self._peak_level = 0.0
        self.update()
    
    def _simulate_update(self):
        """Simulate meter movement for demo."""
        # Random walk simulation
        change = random.uniform(-0.15, 0.15)
        self._level = max(0.0, min(1.0, self._level + change))
        
        # Update peak
        if self._level > self._peak_level:
            self._peak_level = self._level
        else:
            self._peak_level = max(self._level, self._peak_level - self._peak_decay)
        
        self.update()
    
    def paintEvent(self, event):
        """Paint the LED meter segments."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Background - subtle recessed look
        painter.fillRect(0, 0, width, height, QColor(15, 15, 15))
        
        # Calculate segment dimensions
        segment_height = (height - (self._num_segments - 1)) / self._num_segments
        segment_gap = 1
        
        # Calculate how many segments to light up
        lit_segments = int(self._level * self._num_segments)
        peak_segment = int(self._peak_level * self._num_segments)
        
        # Draw segments from bottom to top
        for i in range(self._num_segments):
            # Calculate position (bottom = 0, top = max)
            y = height - ((i + 1) * (segment_height + segment_gap))
            
            # Determine segment color based on position and scheme
            if i < lit_segments:
                # Lit segment
                color = self._get_segment_color(i)
                # Add glow effect
                glow_color = QColor(color)
                glow_color.setAlpha(80)
                painter.fillRect(int(-1), int(y - 1), int(width + 2), int(segment_height + 2), glow_color)
            elif i == peak_segment and peak_segment > lit_segments:
                # Peak hold segment (brighter)
                color = self._get_segment_color(i).lighter(150)
            else:
                # Unlit segment (dim)
                color = QColor(40, 40, 40)
            
            # Draw segment
            painter.fillRect(int(1), int(y), int(width - 2), int(segment_height), color)
        
        painter.end()
    
    def _get_segment_color(self, segment_index: int) -> QColor:
        """Get color for a segment based on position and color scheme.
        
        Args:
            segment_index: Segment index (0 = bottom, num_segments-1 = top).
            
        Returns:
            QColor for the segment.
        """
        # Calculate position ratio (0.0 = bottom, 1.0 = top)
        ratio = segment_index / max(1, self._num_segments - 1)
        
        if self._color_scheme == 'green':
            # Classic green meter: green at bottom, yellow mid, red top
            if ratio < 0.6:
                # Green zone
                return QColor(0, 255, 0)
            elif ratio < 0.85:
                # Yellow zone
                return QColor(255, 255, 0)
            else:
                # Red zone (hot)
                return QColor(255, 0, 0)
        
        elif self._color_scheme == 'blue':
            # Blue meter: dark blue at bottom, cyan at top
            blue = int(100 + 155 * (1.0 - ratio))
            green = int(100 + 155 * ratio)
            return QColor(50, green, blue)
        
        elif self._color_scheme == 'rainbow':
            # Rainbow spectrum
            if ratio < 0.25:
                # Blue to cyan
                return QColor(0, int(ratio * 4 * 255), 255)
            elif ratio < 0.5:
                # Cyan to green
                return QColor(0, 255, int((0.5 - ratio) * 4 * 255))
            elif ratio < 0.75:
                # Green to yellow
                return QColor(int((ratio - 0.5) * 4 * 255), 255, 0)
            else:
                # Yellow to red
                return QColor(255, int((1.0 - ratio) * 4 * 255), 0)
        
        # Fallback: white
        return QColor(255, 255, 255)
