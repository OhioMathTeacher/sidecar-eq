"""Collapsible panel widget for Sidecar EQ.

Provides a reusable panel with a clickable title bar that expands/collapses
the content area. Used to organize the main UI into three sections:
- Song Queue & Info
- EQ & Waveform
- Search

Each panel can be independently collapsed to just show the title bar,
giving users control over their workspace layout.
"""

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QFont, QCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy
)


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
        self.title_frame.setFrameShape(QFrame.StyledPanel)
        self.title_frame.setCursor(QCursor(Qt.PointingHandCursor))
        self.title_frame.setStyleSheet("""
            QFrame {
                background: #2a2a2a;
                border: 1px solid #404040;
                border-radius: 0px;
            }
            QFrame:hover {
                background: #323232;
            }
        """)
        
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(12, 8, 12, 8)
        title_layout.setSpacing(10)
        
        # Arrow indicator (▼ expanded, ▶ collapsed)
        self.arrow_label = QLabel("▼")
        self.arrow_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        title_layout.addWidget(self.arrow_label)
        
        # Title text
        self.title_label = QLabel(self.title)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #d0d0d0;
            }
        """)
        title_layout.addWidget(self.title_label, stretch=1)
        
        self.title_frame.setLayout(title_layout)
        
        # Make title bar clickable
        self.title_frame.mousePressEvent = lambda e: self.toggle_collapse()
        
        layout.addWidget(self.title_frame)
        
        # Content container (will hold user's content widget)
        self.content_container = QFrame()
        self.content_container.setFrameShape(QFrame.StyledPanel)
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
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        
    def toggle_collapse(self):
        """Toggle between collapsed and expanded states."""
        self.set_collapsed(not self.is_collapsed)
        
    def set_collapsed(self, collapsed: bool):
        """Set the collapse state.
        
        Args:
            collapsed: True to collapse, False to expand
        """
        if self.is_collapsed == collapsed:
            return
            
        self.is_collapsed = collapsed
        
        # Update arrow indicator
        self.arrow_label.setText("▶" if collapsed else "▼")
        
        # Show/hide content
        if collapsed:
            self.content_container.hide()
        else:
            self.content_container.show()
            
        # Emit signal
        self.collapsed.emit(collapsed)
        
    def set_title(self, title: str):
        """Update the panel title.
        
        Args:
            title: New title text
        """
        self.title = title
        self.title_label.setText(title)
