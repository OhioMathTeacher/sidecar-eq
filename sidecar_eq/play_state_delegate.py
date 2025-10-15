"""Custom delegate for drawing play state radio buttons in queue table."""

from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush


class PlayStateDelegate(QStyledItemDelegate):
    """
    Custom delegate for column 0 that draws radio button indicators:
    - Solid green filled (●) - Currently playing
    - Red outline (○) - Not playing  
    - Blinking green outline (◐) - Paused (alternates between filled and outline)
    """
    
    PLAY_STATE_STOPPED = 0
    PLAY_STATE_PLAYING = 1
    PLAY_STATE_PAUSED = 2
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._play_state_row = None  # Track which row is playing/paused
        self._play_state = self.PLAY_STATE_STOPPED
        self._blink_state = False  # For paused animation
        
        # Setup blink timer for paused state
        self._blink_timer = QTimer()
        self._blink_timer.timeout.connect(self._on_blink)
        self._blink_timer.setInterval(500)  # Blink every 500ms
    
    def set_play_state(self, row, state):
        """
        Set the play state for a specific row.
        
        Args:
            row: Row index (or None to clear)
            state: PLAY_STATE_STOPPED, PLAY_STATE_PLAYING, or PLAY_STATE_PAUSED
        """
        self._play_state_row = row
        self._play_state = state
        
        # Start/stop blink timer based on state
        if state == self.PLAY_STATE_PAUSED:
            if not self._blink_timer.isActive():
                self._blink_timer.start()
        else:
            if self._blink_timer.isActive():
                self._blink_timer.stop()
            self._blink_state = False
        
        # Trigger repaint
        if self.parent():
            self.parent().viewport().update()
    
    def _on_blink(self):
        """Toggle blink state for paused indicator."""
        self._blink_state = not self._blink_state
        if self.parent():
            self.parent().viewport().update()
    
    def paint(self, painter, option, index):
        """
        Custom paint method to draw play state indicators:
        - Playing: Solid green filled play triangle (►)
        - Paused: Blinking green play triangle (filled <-> outline)
        - Stopped: Red filled stop square (■)
        """
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Get the cell rectangle
        rect = option.rect
        center_x = rect.x() + rect.width() // 2
        center_y = rect.y() + rect.height() // 2
        
        # Determine if this row is the currently playing/paused row
        is_current_row = (index.row() == self._play_state_row)
        
        if is_current_row:
            if self._play_state == self.PLAY_STATE_PLAYING:
                # Playing: Solid green filled play triangle (►)
                painter.setPen(QPen(QColor(0, 200, 0), 2))
                painter.setBrush(QBrush(QColor(0, 200, 0)))
                # Draw triangle pointing right
                from PySide6.QtCore import QPointF
                triangle = [
                    QPointF(center_x - 6, center_y - 8),  # Top left
                    QPointF(center_x - 6, center_y + 8),  # Bottom left
                    QPointF(center_x + 8, center_y)       # Right point
                ]
                painter.drawPolygon(triangle)
                
            elif self._play_state == self.PLAY_STATE_PAUSED:
                # Paused: Blinking green play triangle (alternates between filled and outline)
                painter.setPen(QPen(QColor(0, 200, 0), 2))
                if self._blink_state:
                    # Filled triangle
                    painter.setBrush(QBrush(QColor(0, 200, 0)))
                else:
                    # Outline only
                    painter.setBrush(QBrush(Qt.transparent))
                from PySide6.QtCore import QPointF
                triangle = [
                    QPointF(center_x - 6, center_y - 8),  # Top left
                    QPointF(center_x - 6, center_y + 8),  # Bottom left
                    QPointF(center_x + 8, center_y)       # Right point
                ]
                painter.drawPolygon(triangle)
                
            else:  # PLAY_STATE_STOPPED
                # Stopped: Red filled stop square (■)
                painter.setPen(QPen(QColor(220, 60, 60), 2))
                painter.setBrush(QBrush(QColor(220, 60, 60)))
                painter.drawRect(center_x - 7, center_y - 7, 14, 14)
        else:
            # Not the current row: Red filled stop square (■)
            painter.setPen(QPen(QColor(220, 60, 60), 2))
            painter.setBrush(QBrush(QColor(220, 60, 60)))
            painter.drawRect(center_x - 7, center_y - 7, 14, 14)
        
        painter.restore()
    
    def sizeHint(self, option, index):
        """Return size hint for the play state column."""
        if index.column() == 0:
            # Small fixed width for play state indicator
            return QStyle.sizeFromContents(QStyle.CT_ItemViewItem, option, 
                                          option.rect.size(), self.parent())
        return super().sizeHint(option, index)
