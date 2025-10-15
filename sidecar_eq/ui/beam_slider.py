from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget


class BeamSlider(QWidget):
    """A slim, beam-like slider prototype.

    - Draws a thin rail and a glowing beam from the minimum (bottom) up to
      the draggable handle. Intended as a lightweight visual replacement
      for bulky faders. Works in vertical orientation by default.

    Signals:
        valueChanged(int): emitted when the value changes 0..100
    """

    valueChanged = Signal(int)

    def __init__(self, parent=None, vertical: bool = True, *, core_color=None, glow_color=None, handle_color=None):
        super().__init__(parent)
        self._value = 0
        self._vertical = vertical
        self.setMinimumSize(24, 120) if vertical else self.setMinimumSize(120, 24)
        self.setFocusPolicy(Qt.StrongFocus)
        self._dragging = False
        # Colors (allow customization)
        self._core_color = QColor(30, 140, 255) if core_color is None else (
            QColor(*core_color) if isinstance(core_color, (tuple, list)) else core_color
        )
        self._glow_color = QColor(30, 140, 255, 120) if glow_color is None else (
            QColor(*glow_color) if isinstance(glow_color, (tuple, list)) else glow_color
        )
        self._handle_color = QColor(200, 220, 230) if handle_color is None else (
            QColor(*handle_color) if isinstance(handle_color, (tuple, list)) else handle_color
        )

    # Emit when mouse released
    released = Signal()

    def sizeHint(self) -> QSize:
        return QSize(24, 140) if self._vertical else QSize(200, 24)

    def setValue(self, v: int):
        v = max(0, min(100, int(v)))
        if v != self._value:
            self._value = v
            try:
                self.update()
                self.valueChanged.emit(self._value)
            except Exception as e:
                print(f"[BeamSlider] ERROR in setValue: {e}")
                import traceback
                traceback.print_exc()

    def value(self) -> int:
        return self._value

    def paintEvent(self, event):
        """Paint the slider with beam and glow effects."""
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            w = self.width()
            h = self.height()

            # Colors for recessed LED look
            rail_col = QColor(40, 40, 40)
            beam_core = self._core_color
            beam_glow = self._glow_color
            handle_col = self._handle_color

            if self._vertical:
                cx = w // 2
                rail_y1 = 8
                rail_y2 = h - 8

                # Draw a very thin recessed groove (slightly darker)
                pen = QPen(rail_col)
                pen.setWidth(2)
                painter.setPen(pen)
                painter.drawLine(cx, rail_y1, cx, rail_y2)

                # Beam glow (drawn as multiple translucent strokes for soft glow)
                handle_pos = rail_y2 - int((self._value / 100.0) * (rail_y2 - rail_y1))
                for glow_width, alpha in ((14, 40), (8, 70), (4, 140)):
                    col = QColor(beam_glow.red(), beam_glow.green(), beam_glow.blue(), alpha)
                    pen = QPen(col)
                    pen.setWidth(glow_width)
                    pen.setCapStyle(Qt.RoundCap)
                    painter.setPen(pen)
                    painter.drawLine(cx, rail_y2, cx, handle_pos)

                # Core beam thin line
                pen = QPen(beam_core)
                pen.setWidth(2)
                pen.setCapStyle(Qt.RoundCap)
                painter.setPen(pen)
                painter.drawLine(cx, rail_y2, cx, handle_pos)

                # Handle as a slim dash (minimal, sexy)
                pen = QPen(handle_col)
                pen.setWidth(2)
                painter.setPen(pen)
                painter.setBrush(handle_col)
                hw = max(2, int(w * 0.2))
                hh = 2
                painter.drawRoundedRect(cx - hw // 2, handle_pos - hh // 2, hw, hh, 2, 2)
            else:
                cy = h // 2
                rail_x1 = 6
                rail_x2 = w - 6
                pen = QPen(rail_col)
                pen.setWidth(2)
                painter.setPen(pen)
                painter.drawLine(rail_x1, cy, rail_x2, cy)

                handle_pos = rail_x1 + int((self._value / 100.0) * (rail_x2 - rail_x1))
                for glow_width, alpha in ((14, 40), (8, 70), (4, 140)):
                    col = QColor(beam_glow.red(), beam_glow.green(), beam_glow.blue(), alpha)
                    pen = QPen(col)
                    pen.setWidth(glow_width)
                    pen.setCapStyle(Qt.RoundCap)
                    painter.setPen(pen)
                    painter.drawLine(rail_x1, cy, handle_pos, cy)

                pen = QPen(beam_core)
                pen.setWidth(2)
                pen.setCapStyle(Qt.RoundCap)
                painter.setPen(pen)
                painter.drawLine(rail_x1, cy, handle_pos, cy)

                pen = QPen(handle_col)
                pen.setWidth(2)
                painter.setPen(pen)
                painter.setBrush(handle_col)
                hh = max(2, int(h * 0.35))
                hw = 2
                painter.drawRoundedRect(handle_pos - hw // 2, cy - hh // 2, hw, hh, 2, 2)
        except Exception as e:
            print(f"[BeamSlider] PAINT ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            painter.end()

    def _pos_to_value(self, x, y):
        w = self.width()
        h = self.height()
        if self._vertical:
            rail_y1 = 6
            rail_y2 = h - 6
            v = (rail_y2 - y) / (rail_y2 - rail_y1)
        else:
            rail_x1 = 6
            rail_x2 = w - 6
            v = (x - rail_x1) / (rail_x2 - rail_x1)
        return max(0, min(100, int(round(v * 100))))

    def mousePressEvent(self, event):
        print(f"[BeamSlider] Mouse press at ({event.position().x() if hasattr(event, 'position') else event.x()}, {event.position().y() if hasattr(event, 'position') else event.y()})")
        self.setFocus()
        self._dragging = True
        v = self._pos_to_value(event.position().x() if hasattr(event, 'position') else event.x(),
                               event.position().y() if hasattr(event, 'position') else event.y())
        print(f"[BeamSlider] Setting value to {v}")
        self.setValue(v)

    def mouseMoveEvent(self, event):
        if not self._dragging:
            return
        v = self._pos_to_value(event.position().x() if hasattr(event, 'position') else event.x(),
                               event.position().y() if hasattr(event, 'position') else event.y())
        self.setValue(v)

    def mouseReleaseEvent(self, event):
        print(f"[BeamSlider] Mouse released")
        self._dragging = False
        try:
            self.released.emit()
        except Exception as e:
            print(f"[BeamSlider] Error emitting released signal: {e}")

    def keyPressEvent(self, event):
        step = 5
        if event.key() in (Qt.Key_Up, Qt.Key_Right):
            self.setValue(self._value + step)
            event.accept()
            return
        if event.key() in (Qt.Key_Down, Qt.Key_Left):
            self.setValue(self._value - step)
            event.accept()
            return
        super().keyPressEvent(event)
