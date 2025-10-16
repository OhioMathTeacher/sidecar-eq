"""Star rating delegate for interactive 5-star ratings in table cells.

Provides a custom item delegate that displays and allows editing of ratings
using a 5-star visual interface. Users can click to set ratings, hover to
preview, and the display shows filled/unfilled stars.
"""

from PySide6.QtCore import Qt, QSize, QModelIndex
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import QStyledItemDelegate, QStyle, QStyleOptionViewItem


class StarRatingDelegate(QStyledItemDelegate):
    """Delegate for rendering and editing star ratings in table cells.
    
    Displays ratings as 5 stars (★ filled, ☆ empty). Clicking on a star
    sets the rating to that value (1-5). Hovering shows preview.
    
    The rating value is stored as an integer 0-5 in the model:
    - 0 = no rating (all empty stars)
    - 1-5 = rating (that many filled stars)
    """
    
    def __init__(self, parent=None):
        """Initialize the delegate.
        
        Args:
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self._hover_row = -1
        self._hover_rating = 0
        
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        """Render the star rating in the table cell.
        
        Args:
            painter: QPainter to use for drawing
            option: Style options for the cell
            index: Model index being painted
        """
        # Get rating value (0-5)
        rating = index.data(Qt.ItemDataRole.DisplayRole)
        if rating is None or rating == "":
            rating = 0
        else:
            try:
                rating = int(rating)
            except (ValueError, TypeError):
                rating = 0
        
        # Clamp to valid range
        rating = max(0, min(5, rating))
        
        # Use hover rating if this is the hover row
        if index.row() == self._hover_row and self._hover_rating > 0:
            rating = self._hover_rating
        
        # Draw background if selected
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        
        # Calculate star positions
        star_size = 14
        star_spacing = 2
        total_width = (star_size * 5) + (star_spacing * 4)
        start_x = option.rect.left() + (option.rect.width() - total_width) // 2
        start_y = option.rect.top() + (option.rect.height() - star_size) // 2
        
        # Draw stars
        painter.save()
        
        # Set colors
        filled_color = QColor("#ffd700")  # Gold
        empty_color = QColor("#555555")   # Dark gray
        
        for i in range(5):
            x = start_x + (i * (star_size + star_spacing))
            y = start_y
            
            # Choose filled or empty star
            if i < rating:
                painter.setPen(QPen(filled_color))
                painter.setBrush(filled_color)
                star_char = "★"
            else:
                painter.setPen(QPen(empty_color))
                painter.setBrush(empty_color)
                star_char = "☆"
            
            # Draw star character
            font = painter.font()
            font.setPixelSize(star_size)
            painter.setFont(font)
            painter.drawText(x, y + star_size, star_char)
        
        painter.restore()
    
    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Return the size needed for the star rating display.
        
        Args:
            option: Style options for the cell
            index: Model index
            
        Returns:
            QSize with width/height needed
        """
        # 5 stars at 14px each + 4 gaps at 2px each = 78px wide
        return QSize(78, 20)
    
    def editorEvent(self, event, model, option: QStyleOptionViewItem, index: QModelIndex) -> bool:
        """Handle mouse events for interactive rating.
        
        Args:
            event: Mouse event (click, move, etc.)
            model: Data model
            option: Style options
            index: Model index being interacted with
            
        Returns:
            True if event was handled
        """
        if event.type() == event.Type.MouseButtonPress:
            # Calculate which star was clicked
            star_size = 14
            star_spacing = 2
            total_width = (star_size * 5) + (star_spacing * 4)
            start_x = option.rect.left() + (option.rect.width() - total_width) // 2
            
            click_x = event.pos().x()
            
            if click_x < start_x:
                return False
            
            # Determine which star (0-4)
            relative_x = click_x - start_x
            star_index = relative_x // (star_size + star_spacing)
            
            if star_index >= 0 and star_index < 5:
                # Set rating (1-5) immediately
                new_rating = star_index + 1
                model.setData(index, new_rating, Qt.ItemDataRole.EditRole)
                self._hover_row = -1
                self._hover_rating = 0
                
                # Force immediate repaint
                if hasattr(self.parent(), 'viewport'):
                    self.parent().viewport().update()
                
                return True
        
        elif event.type() == event.Type.MouseMove:
            # Show hover preview
            star_size = 14
            star_spacing = 2
            total_width = (star_size * 5) + (star_spacing * 4)
            start_x = option.rect.left() + (option.rect.width() - total_width) // 2
            
            hover_x = event.pos().x()
            
            if hover_x >= start_x:
                relative_x = hover_x - start_x
                star_index = relative_x // (star_size + star_spacing)
                
                if star_index >= 0 and star_index < 5:
                    old_hover = self._hover_rating
                    self._hover_row = index.row()
                    self._hover_rating = star_index + 1
                    
                    # Only repaint if hover changed
                    if old_hover != self._hover_rating:
                        # Force immediate repaint
                        if hasattr(self.parent(), 'viewport'):
                            self.parent().viewport().update()
                    return True
            else:
                # Mouse left star area
                if self._hover_row == index.row():
                    self._hover_row = -1
                    self._hover_rating = 0
                    if hasattr(self.parent(), 'viewport'):
                        self.parent().viewport().update()
        
        return False
    
    def resetHover(self):
        """Reset hover state (call when mouse leaves table)."""
        self._hover_row = -1
        self._hover_rating = 0
