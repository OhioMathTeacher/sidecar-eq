import sys, os
from pathlib import Path
import json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTableView, QFileDialog, QToolBar, QMessageBox, QHeaderView, QInputDialog, QListWidgetItem, QLabel
)
from PySide6.QtGui import QAction, QKeySequence, QIcon
from PySide6.QtCore import Qt, QModelIndex, QSize, Signal, QTimer
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
from .player import Player

AUDIO_EXTS = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}

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
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(120, 120)
        self._img = None
        if image_path:
            p = Path(image_path)
            if p.exists():
                self._img = QIcon(str(p)).pixmap(140, 140)
                self.setPixmap(self._img)

        # internal drag state
        self._dragging = False
        self._last_y = 0

    def setValue(self, v: int):
        v = max(0, min(100, int(v)))
        if v != self._value:
            self._value = v
            self.valueChanged.emit(self._value)

    def value(self) -> int:
        return self._value

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._last_y = event.position().y() if hasattr(event, 'position') else event.y()
            event.accept()
        # click begins drag for knob; other UI adjustments belong to MainWindow

class MainWindow(QMainWindow):
    """Main application window: builds toolbar, queue table, side panel and wires signals."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Basic state
        self.current_row = None
        self._current_position = "00:00"
        self._current_duration = "00:00"

        # Model / table
        try:
            self.model = QueueModel()
            self.table = QTableView()
            self.table.setModel(self.model)
            self.table.setSelectionBehavior(QTableView.SelectRows)
            self.table.setEditTriggers(QTableView.NoEditTriggers)
            self.table.clicked.connect(self._on_table_play)

            # Make the table the central widget; the side panel is added as a dock
            self.setCentralWidget(self.table)
        except Exception:
            # defensive: ensure attributes exist even if model init fails
            self.model = None
            self.table = None

        # Player wrapper
        try:
            self.player = Player()
        except Exception:
            self.player = None

        # Build UI sections (safe-call)
        try: self._build_toolbar()
        except Exception: pass
        try: self._build_side_panel()
        except Exception: pass
        try: self._build_status_bar()
        except Exception: pass

        # Wire signals last (player and widgets should exist)
        try: self._wire_signals()
        except Exception: pass

        self.setWindowTitle('Sidecar EQ')
        self.resize(1000, 640)
        # Apply preferred dock sizing after layout settles
        try:
            self._apply_dock_sizes()
        except Exception:
            pass

    def _apply_dock_sizes(self):
        """Set the right dock to approximately 35% width (min 320px) and prevent collapse."""
        from PySide6.QtWidgets import QDockWidget
        docks = [w for w in self.findChildren(QDockWidget)]
        if not docks:
            return
        right = docks[0]
        total_w = max(800, self.width())
        desired = int(max(320, total_w * 0.35))
        # set a fixed width for the dock's widget
        try:
            right.widget().setMinimumWidth(desired)
            right.widget().setMaximumWidth(desired * 2)
        except Exception:
            pass
        # also ensure it's visible
        right.show()

    def _on_table_play(self, index):
        row = index.row()
        self._play_row(row)

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
        tb = QToolBar("Main"); tb.setMovable(False); self.addToolBar(tb)

        self.play_btn = IconButton(
            "icons/play.svg",
            "icons/play_hover.svg",
            "icons/play_active.svg",
            tooltip="Play"
        )
        self.play_btn.clicked.connect(self.on_play)
        self.play_btn.setShortcut(QKeySequence(Qt.Key_Space))  # Optional: shortcut support with QPushButton
        tb.addWidget(self.play_btn)

        actStop = QAction(QIcon("icons/stop.svg"), "", self)
        actStop.triggered.connect(self.on_stop); tb.addAction(actStop)
        
    # Removed Next button per UX request (seeking handled via time slider)

        tb.addSeparator()

        # Single Add button — prefer a provided 'addsongs.jpg' image if the user drops it into icons/
        # Prefer SVG if present (crisper), then jpg, then fallback
        # Build an IconButton for Add so hover/pressed states feel the same as Play
        add_svg = Path('icons/addsongs.svg')
        add_jpg = Path('icons/addsongs.jpg')
        from PySide6.QtGui import QPixmap, QPainter, QColor
        if add_svg.exists():
            pm = QPixmap(str(add_svg)).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            hover_svg = Path('icons/addsongs_hover.svg')
            pressed_svg = Path('icons/addsongs_pressed.svg')
            if hover_svg.exists():
                hpm = QPixmap(str(hover_svg)).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            else:
                hpm = QPixmap(pm)
                p = QPainter(hpm)
                p.setCompositionMode(QPainter.CompositionMode_SourceAtop)
                p.fillRect(hpm.rect(), QColor(255, 255, 255, 45))
                p.end()
            if pressed_svg.exists():
                ppm = QPixmap(str(pressed_svg)).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            else:
                ppm = QPixmap(pm)
                p = QPainter(ppm)
                p.setCompositionMode(QPainter.CompositionMode_SourceAtop)
                p.fillRect(ppm.rect(), QColor(0, 0, 0, 70))
                p.end()
            add_btn = IconButton(pm, hpm, ppm, tooltip="Add")
        elif add_jpg.exists():
            pm = QPixmap(str(add_jpg)).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            # simple hover/pressed variations
            hpm = QPixmap(pm)
            p = QPainter(hpm)
            p.setCompositionMode(QPainter.CompositionMode_SourceAtop)
            p.fillRect(hpm.rect(), QColor(255, 255, 255, 45))
            p.end()
            ppm = QPixmap(pm)
            p = QPainter(ppm)
            p.setCompositionMode(QPainter.CompositionMode_SourceAtop)
            p.fillRect(ppm.rect(), QColor(0, 0, 0, 70))
            p.end()
            add_btn = IconButton(pm, hpm, ppm, tooltip="Add")
        else:
            # fallback to simple icon paths
            add_btn = IconButton('icons/fileplus_pressed.svg', 'icons/fileplus_hover.svg', 'icons/fileplus_pressed.svg', tooltip='Add')
        add_btn.clicked.connect(self.on_add_based_on_source)
        tb.addWidget(add_btn)

        tb.addSeparator()
        # Download icon will now invoke the Add behavior (download into queue)
        actDownload = QAction(QIcon("icons/download.svg"), "", self)
        actDownload.triggered.connect(self.on_add_based_on_source)
        tb.addAction(actDownload)

        # Upload icon will perform the previous save action (upload/save playlist)
        upload_svg = Path('icons/upload.svg')
        if upload_svg.exists():
            upload_icon = QIcon(str(upload_svg))
        else:
            # fallback to a neutral icon when upload.svg isn't provided
            upload_icon = QIcon('icons/fileplus_pressed.svg')
        actUpload = QAction(upload_icon, "", self)
        actUpload.triggered.connect(self.on_save_playlist)
        tb.addAction(actUpload)

        # small label to clarify the purpose of the three icons
        tb.addWidget(QLabel('Source:'))

        # Source toggle buttons: Local / URL / Plex — moved into toolbar for easier access
        from PySide6.QtWidgets import QToolButton, QWidget, QHBoxLayout
        src_row = QWidget()
        src_layout = QHBoxLayout()
        src_layout.setContentsMargins(0, 0, 0, 0)
        src_row.setLayout(src_layout)

        self._src_local = QToolButton()
        self._src_local.setCheckable(True)
        self._src_local.setIcon(QIcon('icons/fileplus_hover.svg'))
        self._src_local.setToolTip('Local Files')

        self._src_url = QToolButton()
        self._src_url.setCheckable(True)
        # use addfolder icon to visually distinguish from Local icon
        self._src_url.setIcon(QIcon('icons/addfolder.svg'))
        self._src_url.setToolTip('Website URL')

        self._src_plex = QToolButton()
        self._src_plex.setCheckable(True)
        self._src_plex.setIcon(QIcon('icons/playlist.svg'))
        self._src_plex.setToolTip('Plex Server')

        src_layout.addWidget(self._src_local)
        src_layout.addWidget(self._src_url)
        src_layout.addWidget(self._src_plex)
        tb.addWidget(src_row)

        # default selection
        self._src_local.setChecked(True)
        self._source_mode = 'Local Files'

        def _set_mode_local():
            self._src_local.setChecked(True); self._src_url.setChecked(False); self._src_plex.setChecked(False)
            self._source_mode = 'Local Files'

        def _set_mode_url():
            self._src_local.setChecked(False); self._src_url.setChecked(True); self._src_plex.setChecked(False)
            self._source_mode = 'Website URL'

        def _set_mode_plex():
            self._src_local.setChecked(False); self._src_url.setChecked(False); self._src_plex.setChecked(True)
            self._source_mode = 'Plex Server'

        self._src_local.clicked.connect(_set_mode_local)
        self._src_url.clicked.connect(_set_mode_url)
        self._src_plex.clicked.connect(_set_mode_plex)

    # Playlist import is available via the Plex source toggle — no separate toolbar button

        tb.addSeparator()
        actRemove = QAction(QIcon("icons/trash.svg"), "", self)
        actRemove.setShortcut(QKeySequence.Delete)
        actRemove.triggered.connect(self.on_remove_selected); tb.addAction(actRemove)

    def _build_side_panel(self):
        from PySide6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QLabel

        dock = QDockWidget("", self)
        # hide title bar if we don't want the word "Controls"
        dock.setTitleBarWidget(QWidget())
        dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        cont = QWidget()
        layout = QVBoxLayout()

    # Decorative woodgrain image if present, show small above knob
        wood = Path("icons/woodgrain.png")
        if wood.exists():
            wlbl = QLabel()
            pix = QIcon(str(wood)).pixmap(120, 120)
            wlbl.setPixmap(pix)
            wlbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(wlbl)

    # 'Volume' label (sans-serif, minimal)
        vlabel = QLabel("Volume")
        font = vlabel.font()
        font.setFamily("Helvetica")
        font.setPointSize(10)
        vlabel.setFont(font)
        vlabel.setAlignment(Qt.AlignCenter)
        layout.addWidget(vlabel)

        # Knob image-based widget
        knob = KnobWidget(str(wood) if wood.exists() else None)
        layout.addWidget(knob, alignment=Qt.AlignCenter)

        # (Source toggles were moved to the toolbar for quick access.)
        layout.addWidget(QLabel('Source (toolbar)'))


        # EQ faders area (10 vertical faders with subtle blue glow)
        from PySide6.QtWidgets import QHBoxLayout
        eq_widget = QWidget()
        eq_layout = QHBoxLayout()
        eq_layout.setContentsMargins(10, 10, 10, 10)
        eq_layout.setSpacing(8)
        eq_widget.setLayout(eq_layout)

        self._eq_sliders = []
        # base stylesheet template for sliders; {color} will be filled with current glow color
        slider_css = (
            "QSlider::groove:vertical {{ background: #111; width: 12px; border-radius:6px; }}"
            "QSlider::handle:vertical {{ background: {color}; border: 1px solid #666; width: 16px; height: 14px; margin: -6px 0; border-radius:7px; }}"
        )

        for i in range(10):
            s = QSlider(Qt.Vertical)
            s.setRange(-12, 12)
            s.setValue(0)
            s.setFixedHeight(180)
            s.setStyleSheet(slider_css.format(color='rgba(30,150,255,0.50)'))
            eq_layout.addWidget(s)
            self._eq_sliders.append(s)

        # create a blurred backdrop and stack the eq_widget on top for a subtle blur
        from PySide6.QtWidgets import QStackedLayout, QLabel
        from PySide6.QtGui import QPixmap, QColor
        from PySide6.QtWidgets import QGraphicsBlurEffect

        stack = QWidget()
        stack_layout = QStackedLayout()
        stack.setLayout(stack_layout)

        bg = QLabel()
        bg_pix = QPixmap(360, 220)
        bg_pix.fill(QColor(40, 40, 40, 200))
        bg.setPixmap(bg_pix)
        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(10)
        bg.setGraphicsEffect(blur)

        stack_layout.addWidget(bg)
        stack_layout.addWidget(eq_widget)

        layout.addWidget(stack)

        # Save EQ button: persist current slider settings per-path
        save_eq_btn = QPushButton('Save EQ for Track')
        def _on_save_eq():
            try:
                self.save_eq_for_current_track()
                self.statusBar().showMessage('EQ saved')
            except Exception as e:
                QMessageBox.warning(self, 'Save EQ', str(e))
        save_eq_btn.clicked.connect(_on_save_eq)
        layout.addWidget(save_eq_btn)

        # Recently played: show last 3 tracks and make them clickable (Title / Artist)
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
        self._recent_table = QTableWidget(0, 2)
        self._recent_table.setMaximumHeight(120)
        self._recent_table.setToolTip('Recently played')
        self._recent_table.setHorizontalHeaderLabels(['Title', 'Artist'])
        self._recent_table.verticalHeader().setVisible(False)
        self._recent_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._recent_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._recent_table.setColumnWidth(0, 160)
        self._recent_table.setColumnWidth(1, 120)
        layout.addWidget(QLabel('Recently Played'))
        layout.addWidget(self._recent_table)

        def _on_recent_clicked_table():
            r = self._recent_table.currentRow()
            if r < 0:
                return
            item = self._recent_table.item(r, 0)
            if item is None:
                return
            path = item.data(Qt.UserRole)
            if path not in self.model.paths():
                self.model.add_paths([path])
            idx = self.model.paths().index(path)
            self._play_row(idx)

        self._recent_table.cellClicked.connect(lambda r, c: _on_recent_clicked_table())

        # load recent on startup
        def _load_recent():
            p = Path.home() / '.sidecar_eq_recent.json'
            if not p.exists():
                return []
            try:
                data = json.loads(p.read_text())
                return data.get('recent', [])[:3]
            except Exception:
                return []

        def _write_recent(lst):
            p = Path.home() / '.sidecar_eq_recent.json'
            data = {'recent': lst[:3]}
            try:
                p.write_text(json.dumps(data, indent=2))
            except Exception:
                pass

        # populate table now
        for entry in _load_recent():
            # entry may be a string path (legacy) or a dict {path,title,artist}
            if isinstance(entry, str):
                path = entry
                title = Path(path).name
                artist = ''
            else:
                path = entry.get('path')
                title = entry.get('title', Path(path).name)
                artist = entry.get('artist', '')
            row = self._recent_table.rowCount()
            self._recent_table.insertRow(row)
            ti = QTableWidgetItem(title)
            ti.setData(Qt.UserRole, path)
            self._recent_table.setItem(row, 0, ti)
            self._recent_table.setItem(row, 1, QTableWidgetItem(artist))

        # start a timer to animate glow (oscillate alpha)
        self._eq_phase = 0.0
        def _update_eq_glow():
            self._eq_phase += 0.18
            alpha = (math.sin(self._eq_phase) + 1) / 2 * 0.55 + 0.2  # 0.2..0.75
            color = f'rgba(30,150,255,{alpha:.3f})'
            css = slider_css.format(color=color)
            for sl in self._eq_sliders:
                sl.setStyleSheet(css)

        self._eq_timer = QTimer(self)
        self._eq_timer.timeout.connect(_update_eq_glow)
        self._eq_timer.start(90)

        cont.setLayout(layout)
        dock.setWidget(cont)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        # Wire knob to player.set_volume when available (safe check)
        def _on_knob(val):
            try:
                if hasattr(self.player, 'set_volume'):
                    self.player.set_volume(val / 100.0)
            except Exception:
                pass

        knob.valueChanged.connect(_on_knob)

    # --- Playback helpers ---
    def _play_row(self, row: int):
        paths = self.model.paths()
        if not paths or row is None or row < 0 or row >= len(paths):
            return
        self.current_row = row
        path = paths[row]
        try:
            self.player.play(path)
            self.play_btn.setActive(True)  # <--- Add this line!
            self.table.selectRow(row)
            title = self.model.data(self.model.index(row, 0))
            self.statusBar().showMessage(f"Playing: {title}")
            # attempt to load EQ for this track if present
            try:
                self.load_eq_for_track(path)
            except Exception:
                pass
            # update recent list (persist to file)
            try:
                p = Path.home() / '.sidecar_eq_recent.json'
                recent = []
                if p.exists():
                    try:
                        recent = json.loads(p.read_text()).get('recent', [])
                    except Exception:
                        recent = []
                # move path to front
                if path in recent:
                    recent.remove(path)
                recent.insert(0, path)
                # keep up to 3
                recent = recent[:3]
                p.write_text(json.dumps({'recent': recent}, indent=2))
                # refresh UI list
                if hasattr(self, '_recent_list'):
                    self._recent_list.clear()
                    for rp in recent:
                        it = QListWidgetItem(Path(rp).name)
                        it.setData(Qt.UserRole, rp)
                        self._recent_list.addItem(it)
            except Exception:
                pass
        except Exception as e:
            QMessageBox.warning(self, "Play error", str(e))

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
            self, "Add Audio Files", "", "Audio Files (*.wav *.flac *.mp3 *.ogg *.m4a)"
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
                if Path(name).suffix.lower() in AUDIO_EXTS:
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
        # Save current EQ slider values keyed by current track path
        if self.current_row is None:
            raise RuntimeError('No current track to save EQ for')
        paths = self.model.paths()
        if not paths or self.current_row >= len(paths):
            raise RuntimeError('Invalid current row')
        key = paths[self.current_row]
        vals = [int(s.value()) for s in getattr(self, '_eq_sliders', [])]
        p = self._eq_store_path()
        data = {}
        if p.exists():
            try:
                data = json.loads(p.read_text())
            except Exception:
                data = {}
        data[key] = vals
        p.write_text(json.dumps(data, indent=2))

    def load_eq_for_track(self, path):
        p = self._eq_store_path()
        if not p.exists():
            return
        try:
            data = json.loads(p.read_text())
        except Exception:
            return
        vals = data.get(path)
        if not vals:
            return
        for s, v in zip(getattr(self, '_eq_sliders', []), vals):
            s.setValue(int(v))

    def _on_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Add Audio Files",
            "",
            "Audio Files (*.mp3 *.flac *.ogg *.wav)"
        )
        # drop any macOS “._” sidecar files
        real_files = [
            f for f in files
            if not os.path.basename(f).startswith("._")
        ]
        self.model.add_paths(real_files)

    def import_plex_playlist(self):
        playlists = get_playlist_titles()  # list of (title, id)
        if not playlists:
            QMessageBox.warning(self, "No Playlists", "No Plex playlists found.")
            return

        playlist_names = [t for t, _ in playlists]
        name, ok = QInputDialog.getItem(self, "Choose Playlist", "Playlist:", playlist_names, 0, False)
        if not ok or not name:
            return

        # Find the ratingKey
        rating_key = dict(playlists)[name]
        tracks = get_tracks_for_playlist(rating_key)
        if not tracks:
            QMessageBox.warning(self, "Empty Playlist", "Playlist is empty.")
            return

        # Now add tracks to your queue/table model
        for track in tracks:
            self.model.add_track(track)  # You will need to define this method

def main():
    app = QApplication(sys.argv)
    w = MainWindow(); w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
