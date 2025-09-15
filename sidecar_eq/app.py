import sys, os
from pathlib import Path
import json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTableView, QFileDialog, QToolBar, QMessageBox, QHeaderView, QInputDialog, QListWidgetItem, QLabel, QWidget
)
from PySide6.QtGui import QAction, QKeySequence, QIcon, QPixmap, QPainter, QKeyEvent
from PySide6.QtCore import Qt, QModelIndex, QSize, Signal, QTimer, QObject, QDateTime, QThread
import math
from PySide6.QtWidgets import QSlider, QLabel, QStyle, QProgressBar, QApplication, QPushButton, QDial
from PySide6.QtWidgets import QSplitter
from PySide6.QtMultimediaWidgets import QVideoWidget  # ensures multimedia backend loads
from PySide6.QtMultimedia import QMediaPlayer

from dotenv import load_dotenv
from plexapi.server import PlexServer

from sidecar_eq.plex_helpers import get_playlist_titles, get_tracks_for_playlist

from .queue_model import QueueModel
from . import playlist

class QueueTableView(QTableView):
    """Custom table view that handles Delete key for removing selected items."""
    
    # Signal to notify parent about delete key press
    delete_key_pressed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events, specifically the Delete key."""
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            # Emit signal so MainWindow can handle the removal
            self.delete_key_pressed.emit()
            event.accept()
        else:
            # Pass other keys to parent handler
            super().keyPressEvent(event)

class BackgroundAnalysisWorker(QThread):
    """Background worker for audio analysis that doesn't block the UI."""
    
    # Signals to communicate with main thread
    analysis_complete = Signal(str, dict)  # path, analysis_result
    analysis_failed = Signal(str, str)     # path, error_message
    
    def __init__(self, audio_path: str, parent=None):
        super().__init__(parent)
        self.audio_path = audio_path
        self._should_stop = False
    
    def stop_analysis(self):
        """Request the analysis to stop."""
        self._should_stop = True
    
    def run(self):
        """Run analysis in background thread."""
        try:
            if self._should_stop:
                return
                
            from .analyzer import analyze
            print(f"[BackgroundAnalysis] Starting analysis for: {Path(self.audio_path).stem}")
            
            # Run the analysis
            analysis_result = analyze(self.audio_path)
            
            if self._should_stop:
                return
                
            if analysis_result:
                self.analysis_complete.emit(self.audio_path, analysis_result)
            else:
                self.analysis_failed.emit(self.audio_path, "Analysis returned no results")
                
        except Exception as e:
            if not self._should_stop:
                self.analysis_failed.emit(self.audio_path, str(e))
from .player import Player

AUDIO_EXTS = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".flv", ".m4v", ".webm", ".wmv", ".3gp"}
MEDIA_EXTS = AUDIO_EXTS | VIDEO_EXTS  # Combined audio and video extensions

class IconButton(QPushButton):
    def __init__(self, icon_default, icon_hover, icon_pressed, tooltip="", parent=None):
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
        if not self._active:
            self.setIcon(self.icon_hover)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self._active:
            self.setIcon(self.icon_default)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self.setIcon(self.icon_pressed)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        # For Play: stay pressed if active, else go to hover/default
        if self._active:
            self.setIcon(self.icon_pressed)
        else:
            self.setIcon(self.icon_hover)
        super().mouseReleaseEvent(event)

    def setActive(self, active):
        """Call this to show Play as 'active' or not."""
        self._active = active
        if active:
            self.setIcon(self.icon_pressed)
        else:
            self.setIcon(self.icon_default)


class KnobWidget(QLabel):
    """A simple image-backed knob that maps vertical drag to 0-100 value.

    Emits valueChanged(int).
    """
    valueChanged = Signal(int)

    def __init__(self, image_path: str = None, parent=None):
        super().__init__(parent)
        self._value = 100
        self._last_nonzero = 100
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(96, 96)
        # Only get focus when clicked so wheel doesn’t steal focus
        self.setFocusPolicy(Qt.ClickFocus)
        # Rendering and interaction state
        self._base_pixmap = None  # unrotated knob image (scaled)
        self._press_pos = None    # for tap detection
        self._tap_increments = False  # if True, a tap will bump value
        self._center = None       # center point cache for angular dragging
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
            self._last_y = event.position().y() if hasattr(event, 'position') else event.y()
            try:
                self._press_pos = event.position() if hasattr(event, 'position') else None
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
            if self._image_path.lower().endswith('.svg'):
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
        pos = event.position() if hasattr(event, 'position') else None
        if pos is None:
            return None
        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        dx = pos.x() - cx
        dy = pos.y() - cy
        import math
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
                if self._tap_increments and self._press_pos is not None and hasattr(event, 'position'):
                    if (event.position() - self._press_pos).manhattanLength() < 3:
                        self.setValue(min(100, self._value + 5))
                        event.accept(); return
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
        w = self.width(); h = self.height()
        size = min(w, h)
        # Map 0..100 to -135..+135 degrees
        start_deg = -135.0
        span_deg = (self._value / 100.0) * 270.0
        # Draw thin red arc around the knob (concentric)
        arc_margin = max(2, int(size * 0.06))
        rect = self.rect().adjusted(arc_margin, arc_margin, -arc_margin, -arc_margin)
        from PySide6.QtGui import QPen, QColor
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
    """Knob that snaps to a given number of steps on release (e.g., 3 positions)."""
    def __init__(self, image_path: str = None, steps: int = 3, parent=None):
        super().__init__(image_path, parent)
        self._steps = max(2, int(steps))

    # Wrap value so the source knob can rotate infinitely
    def setValue(self, v: int):
        try:
            v = int(v)
        except Exception:
            v = 0
        if v < 0 or v > 100:
            v = v % 101
        super().setValue(v)

    def mouseReleaseEvent(self, event):
        # Handle tap-to-cycle and quantize on release
        if event.button() == Qt.LeftButton and getattr(self, '_dragging', False):
            self._dragging = False
            try:
                if hasattr(event, 'position') and self._press_pos is not None:
                    if (event.position() - self._press_pos).manhattanLength() < 3:
                        self._set_index(self._step_index() + 1)
                        event.accept(); return
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

    def _step_index(self):
        n = self._steps - 1
        return int(round((self._value / 100.0) * n))

    def _set_index(self, idx: int):
        n = self._steps - 1
        idx = max(0, min(n, int(idx)))
        self.setValue(int(round((idx / n) * 100)))

    def wheelEvent(self, event):
        delta = 0
        try:
            delta = event.angleDelta().y()
        except Exception:
            pass
        if delta == 0:
            return super().wheelEvent(event)
        # More responsive: step multiple indices for large wheel delta
        steps = max(1, abs(int(delta // 120)))
        self._set_index(self._step_index() + (steps if delta > 0 else -steps))
        event.accept()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Up, Qt.Key_Right):
            self._set_index(self._step_index() + 1)
            event.accept(); return
        if event.key() in (Qt.Key_Down, Qt.Key_Left):
            self._set_index(self._step_index() - 1)
            event.accept(); return
        super().keyPressEvent(event)
class MainWindow(QMainWindow):
    """Main application window: builds toolbar, queue table, side panel and wires signals."""

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            # On macOS, ensure toolbar doesn't merge into title bar invisibly
            self.setUnifiedTitleAndToolBarOnMac(False)
        except Exception:
            pass
        # Basic state
        self.current_row = None
        self._current_position = "00:00"
        self._current_duration = "00:00"
        
        # Background analysis management
        self._analysis_worker = None
        self._pending_analysis_path = None

        # Model / table
        try:
            self.model = QueueModel()
            self.table = QueueTableView()
            self.table.setModel(self.model)
            self.table.setSelectionBehavior(QTableView.SelectRows)
            self.table.setEditTriggers(QTableView.NoEditTriggers)
            self.table.clicked.connect(self._on_table_play)
            self.table.delete_key_pressed.connect(self.on_remove_selected)
            self.setCentralWidget(self.table)
            
            # Load saved queue state
            self._load_queue_state()
        except Exception:
            self.model = None
            self.table = None

        # Player wrapper
        try:
            self.player = Player()
        except Exception:
            self.player = None

        # Build UI sections (safe-call)
        try:
            self._build_menubar()
        except Exception as e:
            print(f"[SidecarEQ] Menubar failed: {e}")
        try:
            self._build_toolbar()
        except Exception as e:
            print(f"[SidecarEQ] Toolbar failed: {e}")
            import traceback
            traceback.print_exc()
        try:
            self._build_side_panel()
        except Exception as e:
            print(f"[SidecarEQ] Side panel failed: {e}")
        try:
            self._build_status_bar()
        except Exception:
            pass

        # Wire signals last (player and widgets should exist)
        try:
            self._wire_signals()
        except Exception:
            pass

        self.setWindowTitle('Sidecar EQ')
        self.resize(1000, 640)

    def _on_table_play(self, index):
        try:
            self._play_row(index.row())
        except Exception:
            pass
    def _build_status_bar(self):
        sb = self.statusBar()
        sb.showMessage("Ready")
       
    # Replace non-draggable progress bar with a draggable time slider
        self.timeSlider = QSlider(Qt.Horizontal)
        self.timeSlider.setRange(0, 0)
        self.timeSlider.setSingleStep(1000)
        sb.addPermanentWidget(self.timeSlider)

        self.timeLabel = QLabel("00:00 / 00:00")
        sb.addPermanentWidget(self.timeLabel)

        # Dragging should seek — we wire it below in _wire_signals

        # time “knob
        # self.progress = QProgressBar()
        # self.progress.setTextVisible(False)
        # sb.addPermanentWidget(self.progress)


    def _wire_signals(self):
        # play-end → next track
        self.player.mediaStatusChanged.connect(
            lambda st: st == QMediaPlayer.EndOfMedia and self.on_next()
        )
        # wire duration/position to timeSlider and labels
        def _on_duration(dur):
            try:
                self.timeSlider.setRange(0, int(dur))
            except Exception:
                pass
            self._on_duration(dur)

        def _on_position(pos):
            try:
                # if user is dragging, don't update the slider
                if not self.timeSlider.isSliderDown():
                    self.timeSlider.setValue(int(pos))
            except Exception:
                pass
            self._on_position(pos)

        self.player.durationChanged.connect(_on_duration)
        self.player.positionChanged.connect(_on_position)

        # User seeking via timeSlider → set player position
        self.timeSlider.sliderMoved.connect(lambda v: self.player.set_position(v))

    def _build_toolbar(self):
        print("[SidecarEQ] Building toolbar…")
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(QSize(32, 32))
        # Give the toolbar a subtle background so it's clearly visible
        tb.setStyleSheet("QToolBar{background:#202020; border-bottom:1px solid #333; padding:4px;}")
        self.addToolBar(tb)

        # Play button
        self.play_btn = IconButton(
            "icons/play.svg",
            "icons/play_hover.svg",
            "icons/play_active.svg",
            tooltip="Play"
        )
        self.play_btn.clicked.connect(self.on_play)
        self.play_btn.setShortcut(QKeySequence(Qt.Key_Space))
        tb.addWidget(self.play_btn)

        # Stop button
        stop_btn = IconButton(
            "icons/stop.svg",
            "icons/stop_hover.svg",
            "icons/stop_pressed.svg",
            tooltip="Stop"
        )
        stop_btn.clicked.connect(self.on_stop)
        tb.addWidget(stop_btn)

        # Add Songs button (download icon)
        tb.addSeparator()
        add_btn = IconButton(
            "icons/download.svg",
            "icons/download_hover.svg",
            "icons/download_pressed.svg",
            tooltip="Add Songs"
        )
        add_btn.clicked.connect(self.on_add_based_on_source)
        tb.addWidget(add_btn)
        # default add mode
        self._source_mode = "Local Files"

        # Trash button
        tb.addSeparator()
        trash_btn = IconButton(
            "icons/trash.svg",
            "icons/trash_hover.svg",
            "icons/trash_pressed.svg",
            tooltip="Remove Selected"
        )
        trash_btn.clicked.connect(self.on_remove_selected)
        tb.addWidget(trash_btn)

        # Right-side spacer then Save EQ button on the far right
        from PySide6.QtWidgets import QWidget as _QW, QSizePolicy as _SP
        spacer = _QW(); spacer.setSizePolicy(_SP.Expanding, _SP.Preferred)
        tb.addWidget(spacer)
        save_btn = IconButton(
            "icons/pushbutton.svg",
            "icons/pushbutton.svg",
            "icons/pushbutton.svg",
            tooltip="Save Song EQ"
        )
        save_btn.clicked.connect(self._safe_save_eq)
        tb.addWidget(save_btn)
    print("[SidecarEQ] Toolbar ready")

    def _build_side_panel(self):
        from PySide6.QtWidgets import (
            QDockWidget, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QVBoxLayout as QV, QStackedLayout
        )

        dock = QDockWidget("", self)
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        dock.setTitleBarWidget(QWidget())
        dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)

        cont = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Optional woodgrain badge
        wood = Path("icons/woodgrain.png")
        if wood.exists():
            wlbl = QLabel()
            wlbl.setPixmap(QIcon(str(wood)).pixmap(120, 120))
            wlbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(wlbl)

        # Two-knob row (Volume / Source)
        knobs_row = QHBoxLayout(); knobs_row.setContentsMargins(0, 0, 0, 0); knobs_row.setSpacing(12)

        # Volume column
        vol_col = QV(); vol_col.setSpacing(4)
        vlabel = QLabel("Volume")
        vf = vlabel.font(); vf.setFamily("Helvetica"); vf.setPointSize(10); vlabel.setFont(vf)
        vlabel.setAlignment(Qt.AlignCenter)
        vol_col.addWidget(vlabel)
        knob_src = str(Path("icons/knob.svg")) if Path("icons/knob.svg").exists() else (str(wood) if wood.exists() else None)
        vol_knob = KnobWidget(knob_src)
        # Enable tap to increment volume by a small step
        vol_knob._tap_increments = True
        vol_knob.setMinimumSize(120, 120)
        vol_knob.setMaximumSize(140, 140)
        vol_col.addWidget(vol_knob, alignment=Qt.AlignCenter)
        # Keep reference for global volume shortcuts
        self._vol_knob = vol_knob
        self._vol_led = QLabel("10")
        vledf = self._vol_led.font(); vledf.setFamily("Menlo"); vledf.setPointSize(16); self._vol_led.setFont(vledf)
        self._vol_led.setAlignment(Qt.AlignCenter)
        self._vol_led.setFixedWidth(56)
        self._vol_led.setStyleSheet("color:#ff6666;background:#1e1e1e;padding:2px 6px;border:1px solid #550000;border-radius:4px;")
        vol_col.addWidget(self._vol_led, alignment=Qt.AlignHCenter)
        knobs_row.addLayout(vol_col, 1)

        # Source column
        src_col = QV(); src_col.setSpacing(4)
        slabel = QLabel("Source")
        sf = slabel.font(); sf.setFamily("Helvetica"); sf.setPointSize(10); slabel.setFont(sf)
        slabel.setAlignment(Qt.AlignCenter)
        src_col.addWidget(slabel)
        src_knob = SnapKnobWidget(knob_src, steps=3)
        src_knob.setMinimumSize(120, 120)
        src_knob.setMaximumSize(140, 140)
        src_knob.setValue(0)  # Default to Local Files (index 0)
        src_col.addWidget(src_knob, alignment=Qt.AlignCenter)
        self._src_knob = src_knob
        self._src_names = ["Local Files","Website URL","Plex Server"]
        self._src_led = QLabel("Local Files")
        sledf = self._src_led.font(); sledf.setFamily("Menlo"); sledf.setPointSize(16); self._src_led.setFont(sledf)
        self._src_led.setAlignment(Qt.AlignCenter)
        self._src_led.setFixedWidth(140)
        self._src_led.setStyleSheet("color:#ff6666;background:#1e1e1e;padding:2px 6px;border:1px solid #550000;border-radius:4px;")
        src_col.addWidget(self._src_led, alignment=Qt.AlignHCenter)
        knobs_row.addLayout(src_col, 1)

        layout.addLayout(knobs_row)

        # EQ area with background plate
        eq_widget = QWidget(); from PySide6.QtWidgets import QHBoxLayout as HB
        # Offset to fine-tune slider alignment with background grooves for 7-band EQ  
        # Adjusted for thermometer-style sliders
        eq_x_offset = 35
        eq_layout = HB(); eq_layout.setContentsMargins(eq_x_offset, 8, eq_x_offset, 8); eq_layout.setSpacing(28)
        eq_widget.setLayout(eq_layout); eq_widget.setMinimumHeight(220); eq_widget.setStyleSheet("background:transparent;")

        self._eq_sliders = []
        # Create thermometer-style sliders with draggable top endpoints
        slider_css_fixed = (
            # The groove (thermometer tube)
            "QSlider::groove:vertical { "
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "stop:0 rgba(80,80,80,1), stop:1 rgba(120,120,120,1)); "
            "width: 12px; border: 2px solid rgba(50,50,50,1); "
            "border-radius: 8px; margin: 0px; "
            "}"
            # The filled part (thermometer liquid) - use add-page for proper bottom-to-top fill
            "QSlider::add-page:vertical { "
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "stop:0 rgba(100,200,255,0.9), stop:0.5 rgba(80,160,220,1), stop:1 rgba(60,120,180,1)); "
            "border: 2px solid rgba(40,40,40,1); "
            "border-radius: 8px; margin: 0px; "
            "}"
            # The handle (draggable endpoint)
            "QSlider::handle:vertical { "
            "background: qradialgradient(cx:0.5, cy:0.5, radius:0.8, "
            "stop:0 rgba(255,255,255,1), stop:0.3 rgba(200,230,255,1), "
            "stop:0.7 rgba(120,180,240,1), stop:1 rgba(80,140,200,1)); "
            "width: 24px; height: 16px; margin: -6px 0; "
            "border: 2px solid rgba(40,80,120,1); "
            "border-radius: 8px; "
            "}"
            # Hover state
            "QSlider::handle:vertical:hover { "
            "background: qradialgradient(cx:0.5, cy:0.5, radius:0.8, "
            "stop:0 rgba(255,255,255,1), stop:0.3 rgba(220,240,255,1), "
            "stop:0.7 rgba(140,200,255,1), stop:1 rgba(100,160,220,1)); "
            "border: 2px solid rgba(20,60,100,1); "
            "}"
            # Pressed state
            "QSlider::handle:vertical:pressed { "
            "background: qradialgradient(cx:0.5, cy:0.5, radius:0.8, "
            "stop:0 rgba(200,220,240,1), stop:0.3 rgba(160,190,220,1), "
            "stop:0.7 rgba(100,140,180,1), stop:1 rgba(60,100,140,1)); "
            "}"
        )

        # Create exactly 7 sliders for standard 7-band EQ (60Hz, 150Hz, 400Hz, 1kHz, 2.4kHz, 6kHz, 15kHz)
        for i in range(7):
            s = QSlider(Qt.Vertical)
            s.setRange(-12, 12); s.setValue(0); s.setFixedHeight(180)
            
            # Don't invert - let CSS handle the appearance properly
            
            s.setStyleSheet(slider_css_fixed)
            
            # Connect slider changes to EQ update
            s.valueChanged.connect(self._on_eq_changed)
            
            eq_layout.addWidget(s); self._eq_sliders.append(s)

        # Just add the thermometer widget directly - no background needed
        layout.addWidget(eq_widget)
        
        # Add frequency labels very close to the thermometers
        freq_layout = HB(); freq_layout.setContentsMargins(eq_x_offset, 0, eq_x_offset, 4); freq_layout.setSpacing(28)
        for freq in ["60 Hz", "150 Hz", "400 Hz", "1 kHz", "2.4 kHz", "6 kHz", "15 kHz"]:
            label = QLabel(freq)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: #cccccc; font-size: 11px; font-family: 'Helvetica'; font-weight: bold;")
            freq_layout.addWidget(label)
        layout.addLayout(freq_layout)



        # Note: Using CSS-based handles with built-in hover effects instead of animated glow

        cont.setLayout(layout); dock.setWidget(cont); self.addDockWidget(Qt.RightDockWidgetArea, dock)

        # Wire knobs
        def _on_vol(val):
            try:
                if hasattr(self.player, 'set_volume'): self.player.set_volume(val / 100.0)
            except Exception: pass
            try:
                self._vol_led.setText(f"{min(10,max(0,int(round(val/10)))):02d}")
            except Exception: pass
            # Save volume setting for current track
            try:
                self._save_volume_for_current_track(val)
            except Exception as e:
                print(f"[App] Failed to save volume: {e}")
        vol_knob.valueChanged.connect(_on_vol)

        def _on_src(val):
            try:
                idx = min(2, max(0, int(round(val/50))))
                names = getattr(self, '_src_names', ["Local Files","Website URL","Plex Server"])
                mode = names[idx]
                self._src_led.setText(mode); self._source_mode = mode
            except Exception: pass
        src_knob.valueChanged.connect(_on_src)
        # Initialize highlight
        try:
            _on_src(src_knob.value())
        except Exception:
            pass

    def _build_menubar(self):
        """Create a macOS-native menubar with File/Playback/View/Help."""
        mb = self.menuBar()

        # File menu
        m_file = mb.addMenu("File")
        act_add_files = QAction("Add Files…", self); act_add_files.triggered.connect(self.on_add_files)
        act_add_folder = QAction("Add Folder…", self); act_add_folder.triggered.connect(self.on_add_folder)
        act_save_pl = QAction("Save Playlist…", self); act_save_pl.triggered.connect(self.on_save_playlist)
        act_load_pl = QAction("Load Playlist…", self); act_load_pl.triggered.connect(self.on_load_playlist)
        act_import_plex = QAction("Import Plex Playlist…", self); act_import_plex.triggered.connect(self.import_plex_playlist)
        act_save_eq = QAction("Save Song EQ", self); act_save_eq.triggered.connect(self._safe_save_eq)
        act_quit = QAction("Quit", self); act_quit.setShortcut(QKeySequence.Quit); act_quit.triggered.connect(lambda: QApplication.instance().quit())
        for a in [act_add_files, act_add_folder, act_save_pl, act_load_pl, act_import_plex, act_save_eq]:
            m_file.addAction(a)
        m_file.addSeparator(); m_file.addAction(act_quit)

        # Playback menu
        m_play = mb.addMenu("Playback")
        act_play = QAction("Play", self); act_play.setShortcut(Qt.Key_Space); act_play.triggered.connect(self.on_play)
        act_stop = QAction("Stop", self); act_stop.triggered.connect(self.on_stop)
        act_next = QAction("Next", self); act_next.setShortcut(QKeySequence.MoveToNextWord); act_next.triggered.connect(self.on_next)
        for a in [act_play, act_stop, act_next]: m_play.addAction(a)

        # View menu (EQ Opacity)
        m_view = mb.addMenu("View")
        from PySide6.QtGui import QActionGroup
        grp = QActionGroup(self); grp.setExclusive(True)
        self._eq_opacity_actions = {}
        def _add_opc(name, val):
            act = QAction(name, self); act.setCheckable(True)
            act.triggered.connect(lambda: self._set_eq_opacity(val))
            grp.addAction(act); m_view.addAction(act); self._eq_opacity_actions[name] = act
        _add_opc("EQ Plate Opacity • Low (30%)", 0.30)
        _add_opc("EQ Plate Opacity • Medium (60%)", 0.60)
        _add_opc("EQ Plate Opacity • High (90%)", 0.90)
        # Default to Medium
        self._eq_opacity_actions["EQ Plate Opacity • Medium (60%)"].setChecked(True)
        # Apply after side panel builds (safe-call)
        QTimer.singleShot(0, lambda: self._set_eq_opacity(0.60))

        # Help menu
        m_help = mb.addMenu("Help")
        act_about = QAction("About Sidecar EQ", self)
        act_about.triggered.connect(lambda: QMessageBox.information(self, "About", "Sidecar EQ\nSimple local player with per-track EQ."))
        m_help.addAction(act_about)

    def _set_eq_opacity(self, level: float):
        """Set opacity on the EQ background plate (if present)."""
        try:
            bg = getattr(self, "_eq_bg_widget", None)
            if not bg: return
            from PySide6.QtWidgets import QGraphicsOpacityEffect
            eff = getattr(self, "_eq_opacity_effect", None)
            if eff is None:
                eff = QGraphicsOpacityEffect(self)
                self._eq_opacity_effect = eff
                bg.setGraphicsEffect(eff)
            eff.setOpacity(max(0.0, min(1.0, float(level))))
        except Exception:
            pass

    # --- Toolbar handlers ---
    def on_play(self):
        if self.current_row is None:
            # use selected row if any, else first row
            sel = self.table.selectionModel().selectedRows()
            self._play_row(sel[0].row() if sel else 0)
        else:
            self._play_row(self.current_row)

    def on_stop(self):
        self.player.stop()
        self.statusBar().showMessage("Stopped")
        self.play_btn.setActive(False)

    def on_next(self):
        if self.current_row is None:
            self._play_row(0); return
        self._play_row(self.current_row + 1)

    def on_add_based_on_source(self):
        # Use the toolbar source toggles to decide behavior
        choice = getattr(self, '_source_mode', 'Local Files')
        if choice == 'Local Files':
            return self.on_add_files()
        elif choice == 'Website URL':
            url, ok = QInputDialog.getText(self, 'Add URL', 'Enter audio URL:')
            if ok and url:
                # For now, just add the URL as a path — callers must handle network playback
                self.model.add_paths([url])
                self.statusBar().showMessage('Added URL')
        elif choice == 'Plex Server':
            # Reuse existing playlist import UX
            return self.import_plex_playlist()

    def on_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add Audio/Video Files", "", "Media Files (*.wav *.flac *.mp3 *.ogg *.m4a *.mp4 *.mov *.avi *.mkv *.flv *.m4v *.webm)"
        )
        if files:
            count = self.model.add_paths(files)
            if self.current_row is None and count > 0:
                self.table.selectRow(0)
            self.statusBar().showMessage(f"Added {count} files")

    def on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Add Folder")
        if not folder: return
        paths = []
        for root, _, files in os.walk(folder):
            for name in files:
                if name.startswith("._"):
                    continue
                if Path(name).suffix.lower() in MEDIA_EXTS:
                    paths.append(os.path.join(root, name))
        count = self.model.add_paths(paths)
        if self.current_row is None and count > 0:
            self.table.selectRow(0)
        self.statusBar().showMessage(f"Added {count} files from folder")

    def on_remove_selected(self):
        sel = self.table.selectionModel().selectedRows()
        rows = [ix.row() for ix in sel]
        self.model.remove_rows(rows)
        self.statusBar().showMessage(f"Removed {len(rows)} rows")

    def on_save_playlist(self):
        out, _ = QFileDialog.getSaveFileName(self, "Save Playlist (JSON)", "", "JSON (*.json)")
        if not out: return
        playlist.save_json(self.model.paths(), out)
        self.statusBar().showMessage(f"Saved playlist to {out}")

    def on_load_playlist(self):
        inp, _ = QFileDialog.getOpenFileName(self, "Load Playlist (JSON or M3U)", "", "Playlists (*.json *.m3u *.m3u8)")
        if not inp: return
        suffix = Path(inp).suffix.lower()
        if suffix == ".json":
            paths = playlist.load_json(inp)
        else:
            lines = Path(inp).read_text(errors="ignore").splitlines()
            paths = [ln for ln in lines if ln and not ln.startswith("#")]
        if paths:
            count = self.model.add_paths(paths)
            if self.current_row is None and count > 0:
                self.table.selectRow(0)
            self.statusBar().showMessage(f"Loaded {count} items")
        else:
            QMessageBox.information(self, "Load Playlist", "No paths found in playlist.")

    def _safe_save_eq(self):
        try:
            self.save_eq_for_current_track()
            self.statusBar().showMessage('EQ saved')
        except Exception as e:
            QMessageBox.warning(self, 'Save EQ', str(e))

    def import_plex_playlist(self):
        playlists = get_playlist_titles()  # list of (title, id)
        if not playlists:
            QMessageBox.information(self, "Plex", "No Plex playlists found.")
            return
        titles = [t for t, _ in playlists]
        title, ok = QInputDialog.getItem(self, "Import Plex Playlist", "Choose a playlist:", titles, 0, False)
        if not ok or not title:
            return
        # Find id for chosen title
        pl_id = None
        for t, pid in playlists:
            if t == title:
                pl_id = pid; break
        if not pl_id:
            QMessageBox.warning(self, "Plex", "Selected playlist not found.")
            return
        tracks = get_tracks_for_playlist(pl_id)
        if not tracks:
            QMessageBox.information(self, "Plex", "No tracks in the selected playlist.")
            return
        
        # Add tracks using the model's add_track method for Plex items
        count = 0
        for track in tracks:
            try:
                # The track already has the right format from plex_helpers.py
                added = self.model.add_track(track)
                count += added
            except Exception as e:
                print(f"[App] Failed to add Plex track: {e}")
                continue
        
        if not count:
            QMessageBox.information(self, "Plex", "No tracks could be imported from playlist.")
            return
            
        if self.current_row is None and count > 0:
            self.table.selectRow(0)
        self.statusBar().showMessage(f"Imported {count} tracks from Plex playlist: {title}")

    # --- Playback helpers ---
    def _play_row(self, row: int):
        paths = self.model.paths()
        if not paths or row is None or row < 0 or row >= len(paths):
            return
        
        # Cancel any running background analysis since we're switching tracks
        if self._analysis_worker and self._analysis_worker.isRunning():
            self._analysis_worker.stop_analysis()
            self._pending_analysis_path = None
        
        self.current_row = row
        
        # Get the track info to handle both local files, URLs, and Plex streams
        track_info = self.model._rows[row] if row < len(self.model._rows) else {}
        path = paths[row]
        
        # Determine source type and playback URL
        # Robust source detection with validation
        stream_url = track_info.get('stream_url')
        
        if stream_url and stream_url.strip() and stream_url.startswith(('http://', 'https://')):
            # Plex track - has valid stream URL
            playback_url = stream_url
            identifier = stream_url
            source_type = 'plex'
        elif path and path.startswith(('http://', 'https://')):
            # Website URL - path is HTTP/HTTPS URL
            playback_url = path
            identifier = path
            source_type = 'url'  
        elif path and path.strip():
            # Local file - could be audio or video
            from .video_extractor import is_video_file, extract_audio_from_video
            
            if is_video_file(path):
                # Video file - extract audio for playback
                print(f"[App] Video file detected: {Path(path).name}")
                extracted_audio = extract_audio_from_video(path)
                if extracted_audio:
                    playback_url = str(extracted_audio)
                    identifier = path  # Use original video path as identifier
                    source_type = 'video'
                    print(f"[App] Using extracted audio: {Path(extracted_audio).name}")
                else:
                    print(f"[App] Failed to extract audio from: {Path(path).name}")
                    raise ValueError(f"Could not extract audio from video file: '{Path(path).name}'")
            else:
                # Regular audio file
                playback_url = path
                identifier = path
                source_type = 'local'
        else:
            # Invalid/empty path - this shouldn't happen
            print(f"[Error] Invalid path/URL for row {row}: path='{path}', track_info={track_info}")
            raise ValueError(f"Invalid path for playback: '{path}'")
        
        try:
            self.player.play(playback_url)
            self.play_btn.setActive(True)
            self.table.selectRow(row)
            title = self.model.data(self.model.index(row, 0))
            
            # Show source type in status
            source_labels = {'local': '', 'url': 'from URL', 'plex': 'from Plex', 'video': 'from video'}
            source_label = source_labels.get(source_type, '')
            status_msg = f"Playing: {title}" + (f" ({source_label})" if source_label else "")
            self.statusBar().showMessage(status_msg)
            
            # Track play count using the identifier
            self._increment_play_count(identifier)
            
            # Handle EQ and analysis based on source type
            if source_type in ('plex', 'url'):
                # Streaming sources: just load saved settings (no analysis possible)
                eq_data = self.load_eq_for_track(identifier)
                if eq_data:
                    self._apply_eq_settings(eq_data.get('gains_db', [0]*7))
                    if 'suggested_volume' in eq_data:
                        self._apply_volume_setting(eq_data['suggested_volume'])
                    print(f"[App] Loaded saved EQ settings for streaming source: {Path(identifier).stem}")
                else:
                    # Reset to flat EQ for new streaming sources
                    self._apply_eq_settings([0]*7)
                    print(f"[App] No saved settings for streaming source: {Path(identifier).stem} - using flat EQ")
            elif source_type == 'video':
                # Video files: analyze extracted audio but use original video path as identifier
                print(f"[App] Analyzing extracted audio from video: {Path(identifier).name}")
                eq_data = self._get_or_analyze_eq(playback_url)  # Analyze the extracted audio file
                if eq_data:
                    # Save settings using video file path as key for consistency
                    self._apply_eq_settings(eq_data.get('gains_db', [0]*7))
                    # Store analysis under video file identifier
                    self._store_analysis_for_video(identifier, eq_data)
                else:
                    # Reset to flat EQ if no analysis available
                    self._apply_eq_settings([0]*7)
            else:
                # Regular local audio files: Check if we have saved EQ for this track, otherwise analyze
                eq_data = self._get_or_analyze_eq(identifier)
                if eq_data:
                    self._apply_eq_settings(eq_data.get('gains_db', [0]*7))
                else:
                    # Reset to flat EQ if no analysis available
                    self._apply_eq_settings([0]*7)
                
        except Exception as e:
            QMessageBox.warning(self, "Play error", str(e))
    
    def _get_or_analyze_eq(self, path: str) -> dict:
        """Get saved EQ data or start background analysis if first time playing."""
        # First check if we have saved EQ settings
        try:
            saved_data = self.load_eq_for_track(path)
            if saved_data:
                # Also apply saved volume if available
                if 'suggested_volume' in saved_data:
                    self._apply_volume_setting(saved_data['suggested_volume'])
                return saved_data
        except Exception:
            pass
        
        # No saved EQ found, start background analysis
        self._start_background_analysis(path)
        return None
    
    def _start_background_analysis(self, path: str):
        """Start background analysis for the given track."""
        try:
            # Stop any existing analysis
            if self._analysis_worker and self._analysis_worker.isRunning():
                self._analysis_worker.stop_analysis()
                self._analysis_worker.wait(1000)  # Wait up to 1 second
            
            # Start new background analysis
            self._analysis_worker = BackgroundAnalysisWorker(path, self)
            self._analysis_worker.analysis_complete.connect(self._on_analysis_complete)
            self._analysis_worker.analysis_failed.connect(self._on_analysis_failed)
            self._pending_analysis_path = path
            
            self._analysis_worker.start()
            self.statusBar().showMessage(f"Playing: {Path(path).stem} (analyzing in background...)")
            
        except Exception as e:
            print(f"[App] Failed to start background analysis: {e}")
            self.statusBar().showMessage(f"Playing: {Path(path).stem}")
    
    def _on_analysis_complete(self, path: str, analysis_result: dict):
        """Handle completed background analysis."""
        try:
            # Check if this analysis is still relevant (user might have switched tracks)
            if path != self._pending_analysis_path:
                print(f"[App] Ignoring stale analysis for: {Path(path).stem}")
                return
            
            # Save the analysis results
            self._save_analysis_data(path, analysis_result)
            
            # Apply EQ and volume suggestions in real-time
            if analysis_result:
                # Apply EQ settings
                eq_data = analysis_result.get('eq_data', {})
                if eq_data:
                    self._apply_eq_settings(eq_data)
                
                # Apply volume suggestion
                analysis_data = analysis_result.get('analysis_data', {})
                if 'suggested_volume' in analysis_data:
                    self._apply_volume_setting(analysis_data['suggested_volume'])
                
                lufs = analysis_data.get('loudness_lufs', -23)
                self.statusBar().showMessage(f"Playing: {Path(path).stem} (analyzed: {lufs:.1f} LUFS - settings applied)")
                print(f"[App] Applied real-time analysis for: {Path(path).stem}")
            
        except Exception as e:
            print(f"[App] Error applying analysis results: {e}")
        finally:
            self._pending_analysis_path = None
    
    def _on_analysis_failed(self, path: str, error_message: str):
        """Handle failed background analysis."""
        print(f"[App] Background analysis failed for {Path(path).stem}: {error_message}")
        if path == self._pending_analysis_path:
            self.statusBar().showMessage(f"Playing: {Path(path).stem} (analysis failed)")
            self._pending_analysis_path = None
    
    def _apply_volume_setting(self, suggested_volume: int):
        """Apply suggested volume to the volume knob."""
        try:
            if hasattr(self, '_vol_knob'):
                # Clamp to valid range
                volume = max(0, min(100, suggested_volume))
                self._vol_knob.setValue(volume)
                print(f"[App] Applied suggested volume: {volume}")
        except Exception as e:
            print(f"[App] Failed to apply volume: {e}")
    
    def _save_volume_for_current_track(self, volume_value: int):
        """Save volume setting for the currently playing track."""
        try:
            if not self.current_row or not self.model:
                return
            
            # Get current track path
            track_path = self.model.data(self.model.index(self.current_row, 0), Qt.UserRole)
            if not track_path:
                return
            
            # Load existing EQ data or create new
            existing_data = self.load_eq_for_track(track_path) or {}
            
            # Update volume setting
            existing_data['suggested_volume'] = volume_value
            
            # Save back to file
            self._save_analysis_data(track_path, existing_data)
            print(f"[App] Saved volume {volume_value} for track: {Path(track_path).stem}")
            
        except Exception as e:
            print(f"[App] Error saving volume: {e}")
    
    def _apply_eq_settings(self, gains_db: list):
        """Apply EQ settings to the sliders."""
        try:
            if hasattr(self, '_eq_sliders') and len(gains_db) >= len(self._eq_sliders):
                for i, slider in enumerate(self._eq_sliders):
                    if i < len(gains_db):
                        # Clamp to slider range (-12 to +12)
                        value = max(-12, min(12, int(gains_db[i])))
                        slider.setValue(value)
        except Exception as e:
            print(f"[App] Failed to apply EQ: {e}")
    
    def _on_eq_changed(self):
        """Handle EQ slider changes and apply audio effects."""
        try:
            # Get current EQ values
            eq_values = [slider.value() for slider in self._eq_sliders]
            
            # Apply EQ settings to the player
            self._apply_eq_to_player(eq_values)
            
            # Auto-save EQ settings for current track
            if self.current_row is not None:
                try:
                    self.save_eq_for_current_track()
                    print(f"[App] EQ changed and saved: {eq_values}")
                except Exception as save_error:
                    print(f"[App] EQ changed: {eq_values} (save failed: {save_error})")
            else:
                print(f"[App] EQ changed: {eq_values} (no current track to save)")
        except Exception as e:
            print(f"[App] Failed to handle EQ change: {e}")
    
    def _apply_eq_to_player(self, eq_values: list):
        """Apply EQ settings to audio playback."""
        try:
            if not hasattr(self, 'player') or not self.player:
                return
            
            # Send EQ values to player
            if hasattr(self.player, 'set_eq_values'):
                self.player.set_eq_values(eq_values)
                
            # Calculate overall volume adjustment based on EQ settings
            # This is a simplified approach - reduce volume if too many boosts
            total_boost = sum(max(0, val) for val in eq_values)
            
            # Apply a basic volume compensation to prevent clipping
            volume_compensation = 1.0
            if total_boost > 30:  # More than 30dB total boost
                volume_compensation = 0.6  # Significant reduction
            elif total_boost > 20:  # High boost
                volume_compensation = 0.75
            elif total_boost > 10:  # Moderate boost
                volume_compensation = 0.9
            
            # Get current volume setting and apply compensation
            if hasattr(self, '_vol_knob') and self._vol_knob and self._vol_knob.value() is not None:
                base_volume = self._vol_knob.value() / 100.0
                adjusted_volume = base_volume * volume_compensation
                
                # Apply to player
                if hasattr(self.player, 'set_volume'):
                    self.player.set_volume(adjusted_volume)
            else:
                # Default volume if no knob available
                if hasattr(self.player, 'set_volume'):
                    self.player.set_volume(0.7 * volume_compensation)
                    
                # Calculate frequency-specific adjustments for user feedback
                bass_adjustment = eq_values[0] + eq_values[1]  # 60Hz + 150Hz
                mid_adjustment = eq_values[2] + eq_values[3]   # 400Hz + 1kHz
                treble_adjustment = eq_values[4] + eq_values[5] + eq_values[6]  # 2.4kHz + 6kHz + 15kHz
                
                print(f"[App] EQ Applied - Bass: {bass_adjustment:+.1f}dB, Mid: {mid_adjustment:+.1f}dB, Treble: {treble_adjustment:+.1f}dB")
                if hasattr(self, '_vol_knob') and self._vol_knob and self._vol_knob.value() is not None:
                    print(f"[App] Volume compensation: {volume_compensation:.2f} (base: {base_volume:.2f} -> adjusted: {adjusted_volume:.2f})")
                else:
                    print(f"[App] Volume compensation: {volume_compensation:.2f} (default volume used)")
        
        except Exception as e:
            print(f"[App] Failed to apply EQ to player: {e}")
    
    def _increment_play_count(self, path: str):
        """Increment play count for a track using the store module."""
        try:
            from . import store
            store.increment_play_count(path)
            
            # Update the model to refresh the play count display
            self._refresh_play_count_display(path)
            
            print(f"[App] Incremented play count for: {Path(path).stem}")
        except Exception as e:
            print(f"[App] Failed to increment play count: {e}")
    
    def _refresh_play_count_display(self, path: str):
        """Refresh the play count display for a specific track."""
        try:
            paths = self.model.paths()
            for row, model_path in enumerate(paths):
                if model_path == path:
                    # Update the play count in the model's internal data
                    from . import store
                    record = store.get_record(path) or {}
                    play_count = record.get('play_count', 0)
                    
                    if row < len(self.model._rows):
                        self.model._rows[row]['play_count'] = play_count
                        # Emit data changed signal to update the display
                        index = self.model.index(row, 3)  # Play Count column
                        self.model.dataChanged.emit(index, index)
                    break
        except Exception as e:
            print(f"[App] Failed to refresh play count display: {e}")
    
    def _save_analysis_data(self, path: str, analysis_data: dict):
        """Save analysis data to our EQ store with enhanced metadata."""
        try:
            p = self._eq_store_path()
            data = {}
            if p.exists():
                try:
                    data = json.loads(p.read_text())
                except Exception:
                    data = {}
            
            # Store both EQ settings and analysis metadata
            existing_track_data = data.get(path, {})
            data[path] = {
                'eq_settings': analysis_data.get('gains_db', [0]*7),
                'suggested_volume': analysis_data.get('analysis_data', {}).get('suggested_volume'),
                'analysis_data': analysis_data.get('analysis_data', {}),
                'analyzed_at': str(QDateTime.currentDateTime().toString()),
                'play_count': existing_track_data.get('play_count', 0),  # Don't increment here
                'manual_save': existing_track_data.get('manual_save', False)  # Preserve manual save flag
            }
            
            p.write_text(json.dumps(data, indent=2))
            
        except Exception as e:
            print(f"[App] Failed to save analysis data: {e}")

    def _on_position(self, pos_ms: int):
        mins, secs = divmod(pos_ms // 1000, 60)
        self._current_position = f"{mins:02d}:{secs:02d}"
        self.timeLabel.setText(f"{self._current_position} / {self._current_duration}")

    def _on_duration(self, dur_ms: int):
        mins, secs = divmod(dur_ms // 1000, 60)
        self._current_duration = f"{mins:02d}:{secs:02d}"
        self.timeLabel.setText(f"{self._current_position} / {self._current_duration}")

    # --- EQ persistence helpers ---
    def _eq_store_path(self):
        return Path.home() / '.sidecar_eq_eqs.json'

    def save_eq_for_current_track(self):
        """Save current EQ, volume, and any existing analysis data for the current track."""
        if self.current_row is None:
            raise RuntimeError('No current track to save EQ for')
        paths = self.model.paths()
        if not paths or self.current_row >= len(paths):
            raise RuntimeError('Invalid current row')
        
        path = paths[self.current_row]
        
        # Get current EQ slider values
        eq_values = [int(s.value()) for s in getattr(self, '_eq_sliders', [])]
        
        # Get current volume
        current_volume = self._vol_knob.value() if hasattr(self, '_vol_knob') else 75
        
        # Load existing data (to preserve analysis results)
        p = self._eq_store_path()
        data = {}
        if p.exists():
            try:
                data = json.loads(p.read_text())
            except Exception:
                data = {}
        
        # Get existing track data or create new
        existing_track_data = data.get(path, {})
        
        # Update with current manual settings
        track_data = {
            'eq_settings': eq_values,
            'suggested_volume': current_volume,
            'analysis_data': existing_track_data.get('analysis_data', {}),  # Preserve existing analysis
            'analyzed_at': existing_track_data.get('analyzed_at', str(QDateTime.currentDateTime().toString())),
            'play_count': existing_track_data.get('play_count', 0),
            'manual_save': True,  # Flag to indicate user manually saved settings
            'saved_at': str(QDateTime.currentDateTime().toString())
        }
        
        # Update the data and save
        data[path] = track_data
        p.write_text(json.dumps(data, indent=2))
        
        print(f"[App] Saved EQ and volume for: {Path(path).stem} (EQ: {eq_values}, Vol: {current_volume})")

    def load_eq_for_track(self, path):
        """Load EQ and volume data for a track. Returns dict with eq_settings and volume or None."""
        p = self._eq_store_path()
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text())
        except Exception:
            return None
        
        track_data = data.get(path)
        if not track_data:
            return None
        
        # Handle both old format (just values) and new format (dict with metadata)
        if isinstance(track_data, list):
            # Old format - just EQ values
            eq_settings = track_data
            suggested_volume = None
        elif isinstance(track_data, dict):
            # New format - with metadata
            eq_settings = track_data.get('eq_settings', track_data.get('gains_db', []))
            suggested_volume = track_data.get('suggested_volume')
        else:
            return None
        
        # Apply to sliders
        for s, v in zip(getattr(self, '_eq_sliders', []), eq_settings):
            s.setValue(int(v))
        
        # Apply volume if available
        if suggested_volume is not None:
            self._apply_volume_setting(suggested_volume)
        
        print(f"[App] Loaded settings for: {Path(path).stem} (EQ: {eq_settings[:3]}..., Vol: {suggested_volume})")
        
        # Return in analyzer format for consistency
        return {
            'gains_db': eq_settings,
            'suggested_volume': suggested_volume,
            'bands_hz': [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
        }
    
    def _store_analysis_for_video(self, video_path: str, analysis_data: dict):
        """Store analysis data for a video file using the original video path as key."""
        try:
            p = self._eq_store_path()
            data = {}
            if p.exists():
                try:
                    data = json.loads(p.read_text())
                except Exception:
                    data = {}
            
            # Store under video file path with analysis from extracted audio
            track_data = {
                'eq_settings': analysis_data.get('gains_db', [0]*7),
                'suggested_volume': analysis_data.get('suggested_volume', 75),
                'analysis_data': analysis_data,
                'analyzed_at': str(QDateTime.currentDateTime().toString()),
                'play_count': data.get(video_path, {}).get('play_count', 0),
                'source_type': 'video'
            }
            
            data[video_path] = track_data
            p.write_text(json.dumps(data, indent=2))
            
            print(f"[App] Stored video analysis for: {Path(video_path).stem}")
            
        except Exception as e:
            print(f"[App] Failed to store video analysis: {e}")
    
    def closeEvent(self, event):
        """Clean up background analysis and save queue state when closing the application."""
        try:
            # Save queue state before closing
            self._save_queue_state()
            
            # Clean up background analysis
            if self._analysis_worker and self._analysis_worker.isRunning():
                print("[App] Stopping background analysis...")
                self._analysis_worker.stop_analysis()
                self._analysis_worker.wait(2000)  # Wait up to 2 seconds
        except Exception as e:
            print(f"[App] Error during cleanup: {e}")
        
        event.accept()

    def _get_queue_state_file(self):
        """Get the path to the queue state file."""
        home = Path.home()
        sidecar_dir = home / ".sidecar_eq"
        sidecar_dir.mkdir(exist_ok=True)
        return sidecar_dir / "queue_state.json"

    def _save_queue_state(self):
        """Save the current queue state to disk."""
        try:
            if self.model:
                queue_file = self._get_queue_state_file()
                self.model.save_queue_state(queue_file)
        except Exception as e:
            print(f"[App] Failed to save queue state: {e}")

    def _load_queue_state(self):
        """Load the saved queue state from disk."""
        try:
            if self.model:
                queue_file = self._get_queue_state_file()
                self.model.load_queue_state(queue_file)
        except Exception as e:
            print(f"[App] Failed to load queue state: {e}")

def main():
    """App entry point: configure environment, create QApplication, show MainWindow."""
    try:
        load_dotenv()
    except Exception:
        pass

    # High DPI before QApplication is created
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except Exception:
        pass

    app = QApplication.instance() or QApplication(sys.argv)

    # Fusion dark palette
    try:
        app.setStyle("Fusion")
        from PySide6.QtGui import QPalette, QColor
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(45, 45, 45))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Highlight, QColor(64, 128, 255))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        app.setPalette(palette)
    except Exception:
        pass

    w = MainWindow()

    # Map hardware volume keys and +/- to control the app volume by 1 unit
    def _vol_key_filter(obj, event):
        try:
            from PySide6.QtCore import QEvent
            if event.type() == QEvent.KeyPress:
                if event.key() in (Qt.Key_VolumeUp, Qt.Key_Plus, Qt.Key_Equal):
                    # Find volume knob and bump +1
                    try:
                        # We stored it on window during side panel build
                        if hasattr(w, '_vol_knob'):
                            w._vol_knob.setValue(w._vol_knob.value() + 1)
                            return True
                    except Exception:
                        pass
                if event.key() in (Qt.Key_VolumeDown, Qt.Key_Minus, Qt.Key_Underscore):
                    try:
                        if hasattr(w, '_vol_knob'):
                            w._vol_knob.setValue(w._vol_knob.value() - 1)
                            return True
                    except Exception:
                        pass
        except Exception:
            pass
        return False

    # Proper QObject-based event filter so installEventFilter receives a QObject
    class VolFilter(QObject):
        def __init__(self, handler, parent=None):
            super().__init__(parent)
            self._handler = handler
        def eventFilter(self, obj, event):
            try:
                return bool(self._handler(obj, event))
            except Exception:
                return False

    _vf = VolFilter(_vol_key_filter, app)
    app.installEventFilter(_vf)
    # Keep a Python-side ref so it isn't GC'd while the app runs
    setattr(app, "_vol_filter", _vf)
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
