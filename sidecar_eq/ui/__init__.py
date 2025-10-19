"""UI Widgets for Sidecar EQ application."""

# Standard library imports
import math
from pathlib import Path

# Third-party imports
from PySide6.QtCore import Qt, Signal, QSize, QRect
from PySide6.QtGui import QIcon, QKeyEvent, QPainter, QPen, QColor, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QTableView
from .beam_slider import BeamSlider
from .led_meter import LEDMeter


class QueueTableView(QTableView):
    """Custom table view that handles Delete key for removing selected items.

    This enhanced QTableView intercepts Delete and Backspace key presses
    and emits a signal to notify the parent window, which can then handle
    the removal of selected items from the queue.

    Signals:
        delete_key_pressed: Emitted when Delete or Backspace is pressed.

    Args:
        parent: Parent widget (optional).
    """

    # Signal to notify parent about delete key press
    delete_key_pressed = Signal()

    def __init__(self, parent=None):
        """Initialize the queue table view.

        Args:
            parent: Parent widget, defaults to None.
        """
        super().__init__(parent)
        # Preference: whether to paint stripes/hint when empty
        self._show_empty_stripes = True

    def setShowEmptyStripes(self, enabled: bool):
        """Enable/disable empty-state stripes and hint text.

        Args:
            enabled: True to show stripes/hint when the queue is empty.
        """
        self._show_empty_stripes = bool(enabled)
        try:
            self.viewport().update()
        except Exception:
            pass

    def sizeHint(self):
        """Return a height based on a fixed number of visible rows."""
        hint = super().sizeHint()
        try:
            header_height = self.horizontalHeader().height()
        except Exception:
            header_height = 24
        try:
            row_height = self.verticalHeader().defaultSectionSize()
        except Exception:
            row_height = 24
        model = self.model()
        row_count = model.rowCount() if model is not None else 0
        visible_rows = max(1, min(row_count, 6))
        frame = self.frameWidth() * 2
        height = header_height + (row_height * visible_rows) + frame
        return QSize(hint.width(), height)

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events, specifically the Delete key.

        Intercepts Delete and Backspace keys and emits delete_key_pressed
        signal. All other keys are passed to the parent handler.

        Args:
            event: The key event to process.
        """
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            # Emit signal so MainWindow can handle the removal
            self.delete_key_pressed.emit()
            event.accept()
        else:
            # Pass other keys to parent handler
            super().keyPressEvent(event)

    def paintEvent(self, event):
        """Paint subtle background stripes when there are no rows.

        This mimics classic media apps by suggesting list rows even when empty,
        making the drop target and empty state more understandable at a glance.
        """
        super().paintEvent(event)
        model = self.model()
        if not self._show_empty_stripes or model is None or model.rowCount() > 0:
            return

        # Draw alternating translucent stripes across the viewport
        vp = self.viewport()
        painter = QPainter(vp)
        painter.setRenderHint(QPainter.Antialiasing, False)
        stripe_h = max(20, self.verticalHeader().defaultSectionSize())
        y = 0
        toggle = False
        c1 = QColor(255, 255, 255, 10)  # very subtle
        c2 = QColor(255, 255, 255, 0)
        while y < vp.height():
            painter.fillRect(0, y, vp.width(), stripe_h, c1 if toggle else c2)
            toggle = not toggle
            y += stripe_h

        # Hint text in the top-left
        painter.setPen(QColor(255, 255, 255, 120))
        painter.drawText(12, 18, "Drop songs here or click Add")
        painter.end()


class IconButton(QPushButton):
    """Custom button with hover and pressed icon states.

    A flat QPushButton that displays different icons for default, hover,
    and pressed states, providing visual feedback for user interactions.
    Supports an "active" state to keep the pressed icon displayed (useful
    for toggle buttons like Play/Pause).

    Args:
        icon_default: Path to the default state icon.
        icon_hover: Path to the hover state icon.
        icon_pressed: Path to the pressed state icon.
        tooltip: Tooltip text to display on hover, defaults to empty string.
        parent: Parent widget (optional).

    Attributes:
        icon_default (QIcon): Icon displayed in default state.
        icon_hover (QIcon): Icon displayed on mouse hover.
        icon_pressed (QIcon): Icon displayed when button is pressed.
    """

    def __init__(self, icon_default, icon_hover, icon_pressed, tooltip="", parent=None):
        """Initialize the icon button with three state icons.

        Args:
            icon_default: Path to the default state icon.
            icon_hover: Path to the hover state icon.
            icon_pressed: Path to the pressed state icon.
            tooltip: Tooltip text, defaults to empty string.
            parent: Parent widget, defaults to None.
        """
        super().__init__(parent)
        self.icon_default = QIcon(icon_default)
        self.icon_hover = QIcon(icon_hover)
        self.icon_pressed = QIcon(icon_pressed)
        self.setIcon(self.icon_default)
        self.setIconSize(QSize(32, 32))
        self.setFlat(True)
        self.setToolTip(tooltip)
        self.setFixedSize(40, 40)
        self._active = False  # Only used for play

    def enterEvent(self, event):
        """Handle mouse enter event - show hover icon.

        Args:
            event: The enter event.
        """
        if not self._active:
            self.setIcon(self.icon_hover)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave event - restore default icon.

        Args:
            event: The leave event.
        """
        if not self._active:
            self.setIcon(self.icon_default)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Handle mouse press event - show pressed icon.

        Args:
            event: The mouse press event.
        """
        self.setIcon(self.icon_pressed)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release event - restore appropriate icon.

        If active, stays in pressed state. Otherwise returns to hover state.

        Args:
            event: The mouse release event.
        """
        # For Play: stay pressed if active, else go to hover/default
        if self._active:
            self.setIcon(self.icon_pressed)
        else:
            self.setIcon(self.icon_hover)
        super().mouseReleaseEvent(event)

    def setActive(self, active):
        """Set the active state of the button.

        When active, the button displays the pressed icon regardless of
        mouse state. Used for toggle buttons like Play to show playing state.

        Args:
            active: True to activate (show pressed icon), False to deactivate.
        """
        self._active = active
        if active:
            self.setIcon(self.icon_pressed)
        else:
            self.setIcon(self.icon_default)


class KnobWidget(QLabel):
    """A rotary knob control with visual feedback and multiple input methods.

    An image-backed knob widget that provides a value from 0-100. Supports
    mouse dragging (angular), mouse wheel, keyboard arrows, and double-click
    to mute/unmute. Displays a colored arc indicator showing the current value
    and rotates the knob image accordingly.

    Signals:
        valueChanged(int): Emitted when the value changes (0-100).

    Args:
        image_path: Optional path to knob image (SVG or raster).
        parent: Parent widget (optional).

    Attributes:
        valueChanged: Qt signal emitted on value change.
    """

    valueChanged = Signal(int)

    def __init__(self, image_path: str = None, parent=None):
        """Initialize the knob widget.

        Args:
            image_path: Path to knob image file, defaults to None.
            parent: Parent widget, defaults to None.
        """
        super().__init__(parent)
        self._value = 100
        self._last_nonzero = 100
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(96, 96)
        # Only get focus when clicked so wheel doesn't steal focus
        self.setFocusPolicy(Qt.ClickFocus)
        # Rendering and interaction state
        self._base_pixmap = None  # unrotated knob image (scaled)
        self._press_pos = None  # for tap detection
        self._tap_increments = False  # if True, a tap will bump value
        self._center = None  # center point cache for angular dragging
        self._image_path = None
        if image_path:
            p = Path(image_path)
            if p.exists():
                self._image_path = str(p)
                self._update_pixmap()

        # internal drag state
        self._dragging = False
        self._last_y = 0

    def setValue(self, v: int):
        v = max(0, min(100, int(v)))
        if v != self._value:
            self._value = v
            if v > 0:
                self._last_nonzero = v
            self.valueChanged.emit(self._value)
            # trigger repaint (for rotation)
            try:
                self.update()
            except Exception:
                pass

    def value(self) -> int:
        return self._value

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Focus so wheel/arrow keys work after click
            self.setFocus()
            self._dragging = True
            self._last_y = (
                event.position().y() if hasattr(event, "position") else event.y()
            )
            try:
                self._press_pos = (
                    event.position() if hasattr(event, "position") else None
                )
            except Exception:
                self._press_pos = None
            event.accept()

    def resizeEvent(self, event):
        try:
            self._update_pixmap()
        except Exception:
            pass
        return super().resizeEvent(event)

    def _update_pixmap(self):
        if not self._image_path:
            return
        size = int(min(max(64, self.width()), max(64, self.height())))
        if size <= 0:
            return
        try:
            if self._image_path.lower().endswith(".svg"):
                from PySide6.QtSvg import QSvgRenderer

                pm = QPixmap(size, size)
                pm.fill(Qt.transparent)
                painter = QPainter(pm)
                renderer = QSvgRenderer(self._image_path)
                renderer.render(painter)
                painter.end()
            else:
                src = QPixmap(self._image_path)
                pm = src.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._base_pixmap = pm
        except Exception:
            # fallback using QIcon
            self._base_pixmap = QIcon(self._image_path).pixmap(size, size)
        try:
            self.update()
        except Exception:
            pass

    def _angle_for_event(self, event):
        pos = event.position() if hasattr(event, "position") else None
        if pos is None:
            return None
        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        dx = pos.x() - cx
        dy = pos.y() - cy
        # y down → invert for traditional angle
        ang = math.degrees(math.atan2(-(dy), dx))  # -180..180, 0 at right
        # Clamp to knob sweep [-135, 135]
        if ang < -135:
            ang = -135
        if ang > 135:
            ang = 135
        return ang

    def mouseMoveEvent(self, event):
        if not self._dragging:
            return super().mouseMoveEvent(event)
        ang = self._angle_for_event(event)
        if ang is None:
            return
        # Map angle [-135..135] → 0..100
        val = int(round(((ang + 135.0) / 270.0) * 100.0))
        self.setValue(val)
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            # Treat tiny motion as a tap
            try:
                if (
                    self._tap_increments
                    and self._press_pos is not None
                    and hasattr(event, "position")
                ):
                    if (event.position() - self._press_pos).manhattanLength() < 3:
                        self.setValue(min(100, self._value + 5))
                        event.accept()
                        return
            except Exception:
                pass
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        # Custom paint: draw a red arc indicator and rotate the knob art
        pm = self._base_pixmap
        if pm is None:
            try:
                self._update_pixmap()
                pm = self._base_pixmap
            except Exception:
                pm = None
        if pm is None:
            return super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        size = min(w, h)
        # Map 0..100 to -135..+135 degrees
        start_deg = -135.0
        span_deg = (self._value / 100.0) * 270.0
        # Draw thin red arc around the knob (concentric)
        arc_margin = max(2, int(size * 0.06))
        rect = self.rect().adjusted(arc_margin, arc_margin, -arc_margin, -arc_margin)
        pen = QPen(QColor(220, 60, 60))
        pen.setWidth(max(2, int(size * 0.04)))
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, int(start_deg * 16), int(span_deg * 16))
        # Draw rotated knob image
        angle = start_deg + span_deg
        painter.translate(w / 2.0, h / 2.0)
        painter.rotate(angle)
        if pm.width() != size or pm.height() != size:
            pm = pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter.drawPixmap(int(-pm.width() / 2), int(-pm.height() / 2), pm)
        painter.end()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            # toggle mute/unmute
            if self._value > 0:
                self.setValue(0)
            else:
                self.setValue(self._last_nonzero or 100)
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        # Scroll to change value
        delta = 0
        try:
            delta = event.angleDelta().y()
        except Exception:
            pass
        if delta == 0:
            return super().wheelEvent(event)
        step = 5
        mods = QApplication.keyboardModifiers()
        if mods & Qt.ShiftModifier:
            step = 20
        elif mods & Qt.ControlModifier:
            step = 10
        self.setValue(self._value + (step if delta > 0 else -step))
        event.accept()

    def keyPressEvent(self, event):
        step = 5
        if event.modifiers() & Qt.ShiftModifier:
            step = 20
        elif event.modifiers() & Qt.ControlModifier:
            step = 10
        if event.key() in (Qt.Key_Up, Qt.Key_Right):
            self.setValue(self._value + step)
            event.accept()
            return
        if event.key() in (Qt.Key_Down, Qt.Key_Left):
            self.setValue(self._value - step)
            event.accept()
            return
        super().keyPressEvent(event)


class SnapKnobWidget(KnobWidget):
    """Stepped knob that quantizes to discrete positions.

    A KnobWidget variant that snaps to a fixed number of evenly-spaced
    positions (steps). For example, with 3 steps, the knob will snap to
    positions at 0%, 50%, and 100%. Useful for switches and selectors.

    Supports tap-to-cycle: clicking without dragging advances to the next step.

    Args:
        image_path: Optional path to knob image (SVG or raster).
        steps: Number of discrete positions (minimum 2), defaults to 3.
        parent: Parent widget (optional).
    """

    def __init__(self, image_path: str = None, steps: int = 3, parent=None):
        """Initialize the snap knob with discrete steps.

        Args:
            image_path: Path to knob image file, defaults to None.
            steps: Number of snap positions, defaults to 3.
            parent: Parent widget, defaults to None.
        """
        super().__init__(image_path, parent)
        self._steps = max(2, int(steps))

    # Wrap value so the source knob can rotate infinitely
    def setValue(self, v: int):
        """Set the knob value with wrapping support.

        Values outside 0-100 are wrapped (modulo 101) to allow
        infinite rotation.

        Args:
            v: Target value (wraps if outside 0-100).
        """
        try:
            v = int(v)
        except Exception:
            v = 0
        if v < 0 or v > 100:
            v = v % 101
        super().setValue(v)

    def mouseReleaseEvent(self, event):
        # Handle tap-to-cycle and quantize on release
        if event.button() == Qt.LeftButton and getattr(self, "_dragging", False):
            self._dragging = False
            try:
                if hasattr(event, "position") and self._press_pos is not None:
                    if (event.position() - self._press_pos).manhattanLength() < 3:
                        self._set_index(self._step_index() + 1)
                        event.accept()
                        return
            except Exception:
                pass
            event.accept()
        else:
            super().mouseReleaseEvent(event)
        # Quantize to nearest step after release (if not a tap)
        try:
            n = self._steps - 1
            idx = int(round((self._value / 100.0) * n))
            target = int(round((idx / n) * 100))
            self.setValue(target)
        except Exception:
            pass

    def _step_index(self) -> int:
        """Current 0-based step index."""
        n = self._steps - 1
        return int(round((self._value / 100.0) * n))

    def _set_index(self, idx: int):
        """Set knob to a particular step index (wraps around)."""
        idx = idx % self._steps
        n = self._steps - 1
        target = int(round((idx / n) * 100))
        self.setValue(target)


class WaveformProgress(QLabel):
    """A waveform-style progress bar that supports click-to-seek.

    Displays a visual waveform/level meter that fills with color as playback
    progresses. Supports clicking anywhere to seek to that position. Similar
    to SoundCloud's waveform player.

    The waveform is simulated using random bar heights for visual interest.
    The played portion shows in blue/cyan, unplayed in dark gray.

    Signals:
        seekRequested(int): Emitted when user clicks to seek (position in ms).

    Args:
        parent: Parent widget (optional).

    Attributes:
        seekRequested: Qt signal emitted on click-to-seek.
    """

    seekRequested = Signal(int)

    def __init__(self, parent=None):
        """Initialize the waveform progress widget.

        Args:
            parent: Parent widget, defaults to None.
        """
        super().__init__(parent)
        self._duration = 0  # Total duration in milliseconds
        self._position = 0  # Current position in milliseconds
        self._current_time_str = "00:00"  # Current position formatted
        self._total_time_str = "00:00"    # Total duration formatted
        self.setMinimumHeight(60)
        self.setMinimumWidth(200)
        self.setCursor(Qt.PointingHandCursor)
        # Generate simulated waveform data (bar heights 0.0-1.0)
        import random
        self._waveform = [random.uniform(0.3, 1.0) for _ in range(200)]

    def setDuration(self, duration_ms: int):
        """Set the total duration.

        Args:
            duration_ms: Duration in milliseconds.
        """
        self._duration = max(0, duration_ms)
        # Format as MM:SS
        mins, secs = divmod(duration_ms // 1000, 60)
        self._total_time_str = f"{mins:02d}:{secs:02d}"
        self.update()

    def setPosition(self, position_ms: int):
        """Set the current playback position.

        Args:
            position_ms: Position in milliseconds.
        """
        self._position = max(0, position_ms)
        # Format as MM:SS
        mins, secs = divmod(position_ms // 1000, 60)
        new_time_str = f"{mins:02d}:{secs:02d}"
        
        # Only update if the displayed second changed (avoid excessive repaints)
        if new_time_str != self._current_time_str:
            self._current_time_str = new_time_str
            self.update()

    def mousePressEvent(self, event):
        """Handle click-to-seek.

        Calculate the seek position based on where the user clicked
        and emit seekRequested signal.

        Args:
            event: The mouse press event.
        """
        if event.button() == Qt.LeftButton and self._duration > 0:
            x = event.position().x() if hasattr(event, "position") else event.x()
            width = self.width()
            if width > 0:
                fraction = max(0.0, min(1.0, x / width))
                seek_ms = int(fraction * self._duration)
                self.seekRequested.emit(seek_ms)
                event.accept()
                return
        super().mousePressEvent(event)

    def paintEvent(self, event):
        """Custom paint: draw waveform bars with color fill based on progress.

        Args:
            event: The paint event.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

    # Background: keep transparent so the widget blends with the main window
    # (do not paint a solid rect). This lets the main window background show
    # through and makes the waveform appear as floating bars only.
    # painter.fillRect(0, 0, width, height, QColor(20, 20, 20))

        # Calculate progress fraction
        progress = 0.0
        if self._duration > 0:
            progress = min(1.0, self._position / self._duration)

        # Draw waveform bars with enhanced glow effect
        bar_count = len(self._waveform)
        bar_width = max(1, width / bar_count)

        for i, amp in enumerate(self._waveform):
            x = i * bar_width
            bar_height = int(amp * height * 0.8)  # 80% max height
            y = (height - bar_height) // 2

            # Determine color: played = blue/cyan, unplayed = dark gray
            bar_progress = (i + 0.5) / bar_count  # Center of bar
            if bar_progress <= progress:
                # Played portion - gradient from blue to cyan
                blue_val = int(100 + (155 * (1.0 - bar_progress)))
                color = QColor(50, 150 + int(50 * amp), blue_val)
                
                # Add multi-layer glow effect with increased radius and blur
                # Outermost glow (most diffuse, largest radius)
                glow_outer3 = QColor(color)
                glow_outer3.setAlpha(15)
                painter.fillRect(int(x - 4), y - 4, max(1, int(bar_width + 7)), bar_height + 8, glow_outer3)
                
                # Outer glow layer 2
                glow_outer2 = QColor(color)
                glow_outer2.setAlpha(25)
                painter.fillRect(int(x - 3), y - 3, max(1, int(bar_width + 5)), bar_height + 6, glow_outer2)
                
                # Outer glow layer 1
                glow_outer = QColor(color)
                glow_outer.setAlpha(40)
                painter.fillRect(int(x - 2), y - 2, max(1, int(bar_width + 3)), bar_height + 4, glow_outer)
                
                # Middle glow
                glow_mid = QColor(color)
                glow_mid.setAlpha(70)
                painter.fillRect(int(x - 1), y - 1, max(1, int(bar_width + 1)), bar_height + 2, glow_mid)
                
                # Inner glow (brightest)
                glow_inner = QColor(color.lighter(150))
                glow_inner.setAlpha(140)
                painter.fillRect(int(x), y, max(1, int(bar_width - 1)), bar_height, glow_inner)
            else:
                # Unplayed portion - dark gray (no glow)
                gray_val = int(60 + (40 * amp))
                color = QColor(gray_val, gray_val, gray_val)

            # Draw main bar
            painter.fillRect(int(x), y, max(1, int(bar_width - 1)), bar_height, color)

        # Draw time overlay in bottom-right corner
        time_text = f"{self._current_time_str} / {self._total_time_str}"
        font = painter.font()
        font.setFamily("Helvetica")
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        
        # Measure text size
        fm = painter.fontMetrics()
        text_width = fm.horizontalAdvance(time_text)
        text_height = fm.height()
        
        # Position in bottom-right with padding
        padding = 8
        text_x = width - text_width - padding
        text_y = height - padding
        
        # Draw semi-transparent background for readability
        bg_rect = QRect(text_x - 4, text_y - text_height - 2, text_width + 8, text_height + 4)
        bg_color = QColor(0, 0, 0, 160)  # Semi-transparent black
        painter.fillRect(bg_rect, bg_color)
        
        # Draw text with subtle glow/shadow
        # Shadow
        painter.setPen(QColor(0, 0, 0, 200))
        painter.drawText(text_x + 1, text_y + 1, time_text)
        
        # Main text in light gray/white
        painter.setPen(QColor(220, 220, 220))
        painter.drawText(text_x, text_y, time_text)

        painter.end()
