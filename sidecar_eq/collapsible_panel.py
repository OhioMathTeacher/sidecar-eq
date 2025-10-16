"""Collapsible panel widget for Sidecar EQ.

Provides a reusable panel with a clickable title bar that expands/collapses
the content area with smooth animations. Uses modern system fonts and colors.
"""

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QSizePolicy
)

try:
    from .modern_ui import SystemFonts, ModernColors
    USE_MODERN_UI = True
except ImportError:
    USE_MODERN_UI = False


class CollapsiblePanel(QWidget):
    """A panel with a clickable title bar that shows/hides content.
    
    The panel consists of:
    - Title bar: Clickable header with arrow indicator and title text
    - Content area: Any widget that can be shown/hidden
    
    Signals:
        collapsed: Emitted when panel is collapsed (bool is_collapsed)
    
    Attributes:
        title: Panel title text
        is_collapsed: Current collapse state
    """
    
    # Signal emitted when collapse state changes
    collapsed = Signal(bool)  # True = collapsed, False = expanded
    
    def __init__(self, title: str = "Panel", parent=None):
        """Initialize the collapsible panel.
        
        Args:
            title: Title text to display in header
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.title = title
        self.is_collapsed = False
        self._content_widget = None
        self._animation = None
        self._setup_ui()
        
    def _setup_ui(self):
        """Build the panel UI components."""
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Title bar (clickable header)
        self.title_frame = QFrame()
        self.title_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.title_frame.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # Modern styling with system colors
        if USE_MODERN_UI:
            hover_bg = ModernColors.with_opacity(ModernColors.TEXT_PRIMARY, 0.03)
            self.title_frame.setStyleSheet(f"""
                QFrame {{
                    background: transparent;
                    border: none;
                    padding: 2px 0px;
                }}
                QFrame:hover {{
                    background: {hover_bg};
                }}
            """)
        else:
            # Fallback styling
            self.title_frame.setStyleSheet("""
                QFrame {
                    background: transparent;
                    border: none;
                    padding: 2px 0px;
                }
                QFrame:hover {
                    background: rgba(255,255,255,0.02);
                }
            """)
        
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(8, 2, 8, 2)  # Minimal padding - 2px vertical
        title_layout.setSpacing(6)
        
        # Arrow indicator (▼ expanded, ▶ collapsed)
        self.arrow_label = QLabel("▼")
        if USE_MODERN_UI:
            self.arrow_label.setStyleSheet(f"""
                QLabel {{
                    color: {ModernColors.TEXT_TERTIARY};
                    font-size: 9px;
                    font-weight: bold;
                    background: transparent;
                    border: none;
                }}
            """)
        else:
            self.arrow_label.setStyleSheet("""
                QLabel {
                    color: #888888;
                    font-size: 9px;
                    font-weight: bold;
                    background: transparent;
                    border: none;
                }
            """)
        title_layout.addWidget(self.arrow_label)
        
        # Title text
        self.title_label = QLabel(self.title)
        if USE_MODERN_UI:
            # Use system font for professional look
            title_font = SystemFonts.get_system_font(size=9, weight="Semibold")
            self.title_label.setFont(title_font)
            self.title_label.setStyleSheet(f"""
                QLabel {{
                    color: {ModernColors.TEXT_SECONDARY};
                    letter-spacing: 0.5px;
                    background: transparent;
                    border: none;
                }}
            """)
        else:
            # Fallback styling
            title_font = QFont("Helvetica", 9)
            title_font.setBold(True)
            self.title_label.setFont(title_font)
            self.title_label.setStyleSheet("""
                QLabel {
                    color: #d0d0d0;
                    font-family: 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif;
                    letter-spacing: 0.5px;
                    background: transparent;
                    border: none;
                }
            """)
        title_layout.addWidget(self.title_label, stretch=1)
        
        self.title_frame.setLayout(title_layout)
        
        # Make title bar clickable
        self.title_frame.mousePressEvent = lambda e: self.toggle_collapse()
        
        layout.addWidget(self.title_frame)
        
        # Content container (will hold user's content widget)
        self.content_container = QFrame()
        self.content_container.setFrameShape(QFrame.Shape.StyledPanel)
        
        if USE_MODERN_UI:
            self.content_container.setStyleSheet(f"""
                QFrame {{
                    background: {ModernColors.BACKGROUND_PRIMARY};
                    border: 1px solid {ModernColors.SEPARATOR};
                    border-top: none;
                }}
            """)
        else:
            self.content_container.setStyleSheet("""
                QFrame {
                    background: #1e1e1e;
                    border: 1px solid #404040;
                    border-top: none;
                }
            """)
        
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.content_container.setLayout(self.content_layout)
        
        layout.addWidget(self.content_container)
        
        self.setLayout(layout)
        
    def set_content(self, widget: QWidget):
        """Set the content widget to be shown/hidden.
        
        Args:
            widget: The widget to display in the content area
        """
        # Remove old content if exists
        if self._content_widget:
            self.content_layout.removeWidget(self._content_widget)
            self._content_widget.setParent(None)
        
        # Add new content
        self._content_widget = widget
        self.content_layout.addWidget(widget)
        
        # Set size policy for accordion behavior
        # Content should size naturally, not stretch to fill space
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        
    def toggle_collapse(self):
        """Toggle between collapsed and expanded states."""
        self.set_collapsed(not self.is_collapsed)
        
    def set_collapsed(self, collapsed: bool):
        """Set the collapse state with smooth animation.
        
        Args:
            collapsed: True to collapse, False to expand
        """
        if self.is_collapsed == collapsed:
            return
            
        self.is_collapsed = collapsed
        
        # Update arrow indicator
        self.arrow_label.setText("▶" if collapsed else "▼")
        
        # Cancel any existing animation
        if self._animation:
            self._animation.stop()
        
        # Get current and target heights
        if collapsed:
            start_height = self.content_container.height()
            end_height = 0
        else:
            # Ensure widget is visible to measure its size
            self.content_container.setMaximumHeight(16777215)  # Qt max height
            self.content_container.show()
            self.content_container.adjustSize()
            start_height = 0 if self.content_container.height() == 0 else self.content_container.height()
            end_height = self.content_container.sizeHint().height()
        
        # Create smooth height animation
        self._animation = QPropertyAnimation(self.content_container, b"maximumHeight")
        self._animation.setDuration(250)  # 250ms - feels natural
        self._animation.setStartValue(start_height)
        self._animation.setEndValue(end_height)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)  # Smooth ease
        
        # When collapsing finishes, actually hide the widget
        if collapsed:
            self._animation.finished.connect(lambda: self.content_container.hide())
        
        self._animation.start()
            
        # Emit signal
        self.collapsed.emit(collapsed)
        
    def set_title(self, title: str):
        """Update the panel title.
        
        Args:
            title: New title text
        """
        self.title = title
        self.title_label.setText(title)
