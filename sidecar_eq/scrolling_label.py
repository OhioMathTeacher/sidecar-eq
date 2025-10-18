"""Scrolling label widget for Sidecar EQ.

Provides a label that automatically scrolls text horizontally when it's too long
to fit in the available space. Perfect for song metadata displays.
"""

from PySide6.QtCore import Qt, QTimer, QRect
from PySide6.QtGui import QPainter, QFontMetrics
from PySide6.QtWidgets import QWidget, QSizePolicy


class ScrollingLabel(QWidget):
    """A label that scrolls text horizontally when it overflows.
    
    Features:
    - Auto-detects when text is too long
    - Smooth horizontal scrolling animation
    - Configurable scroll speed and pause duration
    - Supports custom fonts and colors via stylesheet
    
    Attributes:
        text: Current display text
        scroll_speed: Pixels to scroll per update (default: 1)
        pause_duration: Milliseconds to pause before restarting scroll (default: 1000)
    """
    
    def __init__(self, text: str = "", parent=None):
        """Initialize the scrolling label.
        
        Args:
            text: Initial text to display
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self._text = text
        self._scroll_offset = 0
        self._text_width = 0
        self._is_scrolling = False
        self._scroll_speed = 1  # pixels per update
        self._pause_duration = 1500  # ms to pause at start/end
        
        # Timer for smooth scrolling animation
        self._scroll_timer = QTimer(self)
        self._scroll_timer.timeout.connect(self._update_scroll)
        self._scroll_timer.setInterval(30)  # ~33 FPS
        
        # Timer for pause at start/end
        self._pause_timer = QTimer(self)
        self._pause_timer.timeout.connect(self._resume_scrolling)
        self._pause_timer.setSingleShot(True)
        
        # Size policy - expand horizontally, fixed height
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # Minimum size
        self.setMinimumHeight(30)
        
    def setText(self, text: str):
        """Set the text to display.
        
        Args:
            text: New text to display
        """
        self._text = text
        self._scroll_offset = 0
        self._calculate_text_width()
        self._start_or_stop_scrolling()
        self.update()
        
    def text(self) -> str:
        """Get the current text.
        
        Returns:
            Current display text
        """
        return self._text
    
    def setScrollSpeed(self, speed: int):
        """Set the scroll speed in pixels per update.
        
        Args:
            speed: Pixels to scroll per update (default: 1)
        """
        self._scroll_speed = speed
        
    def setPauseDuration(self, duration: int):
        """Set the pause duration in milliseconds.
        
        Args:
            duration: Milliseconds to pause before restarting (default: 1500)
        """
        self._pause_duration = duration
    
    def _calculate_text_width(self):
        """Calculate the width of the text in pixels."""
        font_metrics = QFontMetrics(self.font())
        self._text_width = font_metrics.horizontalAdvance(self._text)
    
    def _start_or_stop_scrolling(self):
        """Start or stop scrolling based on text width."""
        if self._text_width > self.width():
            # Text is too long - start scrolling
            if not self._is_scrolling:
                self._is_scrolling = True
                # Pause before starting scroll
                self._pause_timer.start(self._pause_duration)
        else:
            # Text fits - stop scrolling
            self._is_scrolling = False
            self._scroll_timer.stop()
            self._pause_timer.stop()
            self._scroll_offset = 0
    
    def _resume_scrolling(self):
        """Resume scrolling after pause."""
        if self._is_scrolling:
            self._scroll_timer.start()
    
    def _update_scroll(self):
        """Update scroll position and trigger repaint."""
        if not self._is_scrolling:
            return
        
        # Calculate how far we need to scroll
        # We want to scroll until the end of the text reaches the left edge,
        # then reset to show the beginning again
        max_scroll = self._text_width + 50  # Add some padding before restart
        
        # Increment scroll offset
        self._scroll_offset += self._scroll_speed
        
        # Check if we've scrolled all the way
        if self._scroll_offset >= max_scroll:
            # Reset to beginning and pause
            self._scroll_offset = 0
            self._scroll_timer.stop()
            self._pause_timer.start(self._pause_duration)
        
        # Trigger repaint
        self.update()
    
    def paintEvent(self, event):
        """Custom paint to draw scrolling text."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get widget dimensions
        rect = self.rect()
        
        # Draw background (use widget's background from stylesheet)
        painter.fillRect(rect, self.palette().window())
        
        # Set text color from stylesheet
        painter.setPen(self.palette().windowText().color())
        painter.setFont(self.font())
        
        # Calculate text position
        if self._is_scrolling or self._text_width > rect.width():
            # Scrolling mode - draw text offset to the left
            x = -self._scroll_offset
            y = rect.height() // 2 + QFontMetrics(self.font()).ascent() // 2
            painter.drawText(x, y, self._text)
            
            # Also draw text again at the end to create seamless loop
            # (but only if we're scrolled far enough)
            if self._scroll_offset > 50:
                x2 = self._text_width + 50 - self._scroll_offset
                painter.drawText(x2, y, self._text)
        else:
            # Static mode - center text
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._text)
    
    def resizeEvent(self, event):
        """Handle widget resize - recalculate if scrolling is needed."""
        super().resizeEvent(event)
        self._start_or_stop_scrolling()
