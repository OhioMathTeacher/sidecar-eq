"""Collapsible panel widget for Sidecar EQ.

Provides a reusable panel with a clickable title bar that expands/collapses
the content area with smooth animations. Uses modern system fonts and colors.
"""

from PySide6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, QTimer, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QSizePolicy
)

try:
    from .modern_ui import SystemFonts, ModernColors
    USE_MODERN_UI = True
except ImportError:
    USE_MODERN_UI = False

HEADER_HEIGHT = 21


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
    
    def __init__(self, title: str = "Panel", parent=None, start_collapsed: bool = False):
        """Initialize the collapsible panel.
        
        Args:
            title: Title text to display in header
            parent: Parent widget (optional)
            start_collapsed: Whether to start in collapsed state
        """
        super().__init__(parent)
        self.title = title
        self.is_collapsed = start_collapsed
        self._content_widget = None
        self._animation = None
        self._setup_ui()
        self._lock_content_height = False
        self._header_widgets = {self.title_frame, self.title_label, self.arrow_label}
        for widget in self._header_widgets:
            widget.setCursor(Qt.CursorShape.PointingHandCursor)
            widget.installEventFilter(self)

        header_height = max(1, self.title_frame.maximumHeight() or HEADER_HEIGHT)
        
        # Set initial size policy based on start state
        if start_collapsed:
            # Collapsed: Fixed height (just tab bar) - completely locked
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.setMinimumHeight(header_height)
            self.setMaximumHeight(header_height)
            self.arrow_label.setText("▶")
            self.content_container.hide()  # Hide content initially
            self.content_container.setMaximumHeight(0)
            self.content_container.setMinimumHeight(0)
        else:
            # Expanded: Minimum (size to content, resizable)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            self.setMinimumHeight(header_height)
            self.setMaximumHeight(16777215)
            self.arrow_label.setText("▼")
        
    def _setup_ui(self):
        """Build the panel UI components."""
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Title bar (static label, not clickable - layout controlled by dropdown)
        self.title_frame = QFrame()
        self.title_frame.setFrameShape(QFrame.Shape.StyledPanel)
        
        # Fixed height - 175% of font size (9pt * 1.75 ≈ 21px)
        # Use both setFixedHeight and size policy to prevent expansion
        self.title_frame.setFixedHeight(HEADER_HEIGHT)
        self.title_frame.setMinimumHeight(HEADER_HEIGHT)
        self.title_frame.setMaximumHeight(HEADER_HEIGHT)
        self.title_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Modern styling with system colors (no hover since not interactive)
        if USE_MODERN_UI:
            self.title_frame.setStyleSheet(
                """
                QFrame {
                    background: transparent;
                    border: none;
                    padding: 2px 0px;
                }
                """
            )
        else:
            # Fallback styling
            self.title_frame.setStyleSheet("""
                QFrame {
                    background: transparent;
                    border: none;
                    padding: 2px 0px;
                }
            """)
        
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(8, 2, 8, 2)  # Minimal padding - 2px vertical
        title_layout.setSpacing(6)
        
        # Arrow status indicator (▼ visible, ▶ hidden) - NOT clickable, just shows state
        self.arrow_label = QLabel("▼")
        self.arrow_label.setFixedSize(10, HEADER_HEIGHT - 4)  # Lock arrow size to prevent expansion
        self.arrow_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
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
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.title_label.setMaximumHeight(HEADER_HEIGHT - 4)  # Lock title label height
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
        
        layout.addWidget(self.title_frame)
        
        # Content container (will hold user's content widget)
        self.content_container = QFrame()
        self.content_container.setFrameShape(QFrame.Shape.StyledPanel)
        
        # Size policy: expand horizontally, fit content vertically (no extra space)
        self.content_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
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
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # Align content to top, not center
        self.content_container.setLayout(self.content_layout)
        
        layout.addWidget(self.content_container, stretch=0)  # No stretch - size to content
        
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

        # Track new content widget for geometry updates
        widget.installEventFilter(self)

        self.content_layout.addWidget(widget)

        # Apply current locking preference to the new content
        self._apply_size_policies()
        self._schedule_geometry_update()
        
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
        
        # Update arrow status indicator (▶ = hidden, ▼ = visible)
        self.arrow_label.setText("▶" if collapsed else "▼")
        
        header_height = max(1, self.title_frame.maximumHeight() or HEADER_HEIGHT)

        # Cancel any existing animation
        if self._animation:
            self._animation.stop()
            self._animation = None

        # Update size policy based on collapse state
        if collapsed:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.setMinimumHeight(header_height)
            self.setMaximumHeight(header_height)
            self.content_container.setMinimumHeight(0)
            self.content_container.setMaximumHeight(0)
            start_height = self.content_container.height()
            end_height = 0
        else:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            self.setMinimumHeight(header_height)
            self.setMaximumHeight(16777215)
            self.content_container.setMinimumHeight(0)
            self.content_container.setMaximumHeight(16777215)
            self.content_container.show()
            self.content_container.adjustSize()
            current_height = self.content_container.height()
            start_height = current_height if current_height > 0 else 0
            end_height = self.content_container.sizeHint().height()

        # Apply locking preferences to updated state
        self._apply_size_policies()

        # If we're already collapsed (height 0), skip the animation entirely
        if collapsed and start_height == 0:
            self.content_container.hide()
            self.collapsed.emit(True)
            self._schedule_geometry_update()
            return

        # Create smooth height animation
        self._animation = QPropertyAnimation(self.content_container, b"maximumHeight")
        self._animation.setDuration(250)  # 250ms - feels natural
        self._animation.setStartValue(start_height)
        self._animation.setEndValue(end_height)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)  # Smooth ease

        if collapsed:
            self._animation.finished.connect(lambda: self.content_container.hide())
        else:
            self._animation.finished.connect(self._schedule_geometry_update)

        self._animation.start()

        # Emit signal for listeners (MainWindow saves state, resizes, etc.)
        self.collapsed.emit(collapsed)
        if not collapsed:
            self._schedule_geometry_update()
        
    def set_title(self, title: str):
        """Update the panel title.
        
        Args:
            title: New title text
        """
        self.title = title
        self.title_label.setText(title)

    def lock_content_height(self, lock: bool = True):
        """Lock the panel height to the content height when expanded."""
        if self._lock_content_height == lock:
            return
        self._lock_content_height = lock
        self._apply_size_policies()
        self._schedule_geometry_update()

    def refresh_geometry(self):
        """Reapply height constraints based on current content size."""
        self._schedule_geometry_update()

    def eventFilter(self, obj, event):
        if obj is self._content_widget and self._lock_content_height:
            if event.type() in (QEvent.Type.LayoutRequest, QEvent.Type.Resize):
                self._schedule_geometry_update()
        elif obj in getattr(self, "_header_widgets", set()):
            if event.type() in (QEvent.Type.MouseButtonRelease, QEvent.Type.MouseButtonDblClick) and event.button() == Qt.LeftButton:
                self.toggle_collapse()
                return True
            if event.type() == QEvent.Type.MouseButtonPress:
                return True
        return super().eventFilter(obj, event)

    def _apply_size_policies(self):
        """Apply size policies according to the lock preference."""
        if self._content_widget is None:
            return
        vertical_policy = QSizePolicy.Policy.Fixed if self._lock_content_height else QSizePolicy.Policy.Minimum
        self._content_widget.setSizePolicy(QSizePolicy.Policy.Expanding, vertical_policy)
        container_policy = QSizePolicy.Policy.Fixed if self._lock_content_height else QSizePolicy.Policy.Minimum
        self.content_container.setSizePolicy(QSizePolicy.Policy.Expanding, container_policy)

    def _schedule_geometry_update(self):
        if self.is_collapsed or not self._lock_content_height or self._content_widget is None:
            if not self.is_collapsed and not self._lock_content_height:
                self.content_container.setMaximumHeight(16777215)
                self.content_container.setMinimumHeight(0)
                self.setMaximumHeight(16777215)
                self.setMinimumHeight(0)
            return

        def _apply():
            if self._content_widget is None or self.is_collapsed:
                return
            hint = self._content_widget.sizeHint().height()
            self.content_container.setMaximumHeight(hint)
            self.content_container.setMinimumHeight(hint)
            total = hint + self.title_frame.height()
            self.setMinimumHeight(total)
            self.setMaximumHeight(total)
            self.updateGeometry()

        QTimer.singleShot(0, _apply)
