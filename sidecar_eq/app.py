import sys, os, shutil
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTableView, QFileDialog, QToolBar, QMessageBox, QHeaderView, QInputDialog
)
from PySide6.QtGui import QAction, QKeySequence, QIcon
from PySide6.QtCore import Qt, QModelIndex, QSize
from PySide6.QtWidgets import QSlider, QLabel, QStyle, QProgressBar, QApplication, QPushButton
from PySide6.QtWidgets import QDial
from PySide6.QtMultimediaWidgets import QVideoWidget  # ensures multimedia backend loads
from PySide6.QtMultimedia import QMediaPlayer

# Optional imports: keep app importable when these developer dependencies
# are not installed in the test environment.
try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

try:
    from plexapi.server import PlexServer
except Exception:
    PlexServer = None

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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sidecar EQ — Preview")
        self.resize(900, 520)

        self._build_toolbar()
        self.player = Player()
        self.current_row = None

        self._build_queue_table()
        # now self.table exists, so it’s safe to hook this
        self.table.doubleClicked.connect(self._on_table_play)

        self._build_status_bar()
        self._current_position = "00:00"
        self._current_duration = "00:00"
        self._wire_signals()
        # Now that central widget and signals are ready, create the side panel
        try:
            self._build_side_panel()
        except Exception:
            pass

    def _build_queue_table(self):
        self.table = QTableView()
        self.model = QueueModel(self)
        self.table.doubleClicked.connect(self._on_table_play)
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.ExtendedSelection)
        self.setCentralWidget(self.table)
        self.table.setAlternatingRowColors(False)

        from PySide6.QtWidgets import QHeaderView
        hdr = self.table.horizontalHeader()

        # Title column: auto-size to contents, with extra padding
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(0, 220)  # Set minimum width for Title at startup

        # Artist and Album: auto-size to contents
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        # Play Count: fixed width, enough for up to 8 digits
        hdr.setSectionResizeMode(3, QHeaderView.Fixed)
        fm = self.table.fontMetrics()
        play_count_width = fm.horizontalAdvance("0" * 8)
        self.table.setColumnWidth(3, play_count_width)

        # Minimum column width for all columns (optional, but helps empty table look better)
        hdr.setMinimumSectionSize(100)

    def _on_table_play(self, index):
        row = index.row()
        self._play_row(row)

    def _build_status_bar(self):
        sb = self.statusBar()
        sb.showMessage("Ready")
        # Replace the old gradient/progress look with a darker, flatter
        # style so toolbar icons pop and the seek slider is obvious.
        try:
            self.setStyleSheet("QToolBar { background: #2b2b2b; border: none; }")
        except Exception:
            pass

        # seek slider in status bar (draggable; replaces the previous progress bar)
        self.seek_slider = QSlider()
        self.seek_slider.setOrientation(Qt.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.setFixedWidth(300)
        sb.addPermanentWidget(self.seek_slider)

        # playback state label (left of timeLabel)
        self.stateLabel = QLabel("")
        sb.addPermanentWidget(self.stateLabel)

        self.timeLabel = QLabel("00:00 / 00:00")
        sb.addPermanentWidget(self.timeLabel)

        # time “knob
        # self.progress = QProgressBar()
        # self.progress.setTextVisible(False)
        # sb.addPermanentWidget(self.progress)


    def _wire_signals(self):
        # play-end → next track
        self.player.mediaStatusChanged.connect(
            lambda st: st == QMediaPlayer.EndOfMedia and self.on_next()
        )
        # prevent UI feedback while user drags
        self._seeking = False

        def _on_slider_pressed():
            self._seeking = True

        def _on_slider_released():
            self._seeking = False
            pos = int(self.seek_slider.value())
            try:
                self.player.seek(pos)
            except Exception:
                pass

        def _on_slider_moved(val):
            # update timeLabel preview while dragging
            mins, secs = divmod(int(val) // 1000, 60)
            cur = f"{mins:02d}:{secs:02d}"
            parts = self.timeLabel.text().split("/")
            dur = parts[1].strip() if len(parts) > 1 else self._current_duration
            self.timeLabel.setText(f"{cur} / {dur}")

        self.seek_slider.sliderPressed.connect(_on_slider_pressed)
        self.seek_slider.sliderReleased.connect(_on_slider_released)
        self.seek_slider.sliderMoved.connect(_on_slider_moved)

        # position & duration → UI updates (avoid updating slider while user drags)
        self.player.positionChanged.connect(lambda p: (self.seek_slider.setValue(int(p)) if not self._seeking else None))
        self.player.durationChanged.connect(lambda d: self.seek_slider.setRange(0, int(d) if d else 0))
        self.player.positionChanged.connect(self._on_position)
        self.player.durationChanged.connect(self._on_duration)

        # reflect play state in the icon toolbar
        try:
            self.player.playingChanged.connect(self.play_btn.setActive)
        except Exception:
            pass

        # update textual playback state
        def _on_playing_changed(is_playing: bool):
            self.stateLabel.setText("Playing" if is_playing else "Paused")

        def _on_media_status(st):
            # map common statuses to a short label
            try:
                if st == QMediaPlayer.EndOfMedia:
                    self.stateLabel.setText("Stopped")
                # leave other statuses alone; mediaStatus prints via existing handler
            except Exception:
                pass

        try:
            self.player.playingChanged.connect(_on_playing_changed)
            self.player.mediaStatusChanged.connect(_on_media_status)
        except Exception:
            pass

    def _build_toolbar(self):
        tb = QToolBar("Main"); tb.setMovable(False); self.addToolBar(tb)
        # Make the toolbar darker so icons pop
        try:
            tb.setStyleSheet("background: #2b2b2b;")
        except Exception:
            pass

        self.play_btn = IconButton(
            "icons/play.svg",
            "icons/play_hover.svg",
            "icons/play_active.svg",
            tooltip="Play"
        )
        self.play_btn.clicked.connect(self.on_play)
        self.play_btn.setShortcut(QKeySequence(Qt.Key_Space))  # Optional: shortcut support with QPushButton
        tb.addWidget(self.play_btn)

        # Volume dial + numeric readout
        # small volume icon to the left of the dial to stabilize layout
        vol_icon = QLabel()
        vol_icon.setPixmap(QIcon("icons/volume_grey.svg").pixmap(20, 20))
        tb.addWidget(vol_icon)

        self.volume_dial = QDial()
        self.volume_dial.setRange(0, 100)
        self.volume_dial.setValue(100)
        self.volume_dial.setFixedSize(40, 40)
        tb.addWidget(self.volume_dial)

        # connect dial changes
        try:
            self.volume_dial.valueChanged.connect(self._on_volume_dial_changed)
        except Exception:
            pass

        self.volume_label = QLabel("100")
        # fixed size to avoid toolbar reflow when value changes
        self.volume_label.setFixedWidth(28)
        self.volume_label.setAlignment(Qt.AlignCenter)
        self.volume_label.setStyleSheet("color: #eee;")
        tb.addWidget(self.volume_label)

        # Mute toggle
        self.mute_action = QAction(QIcon("icons/mute.svg"), "Mute", self)
        self.mute_action.setCheckable(True)
        self.mute_action.triggered.connect(lambda checked: self.player.set_muted(checked))
        tb.addAction(self.mute_action)

        # reflect player's volume/mute changes in UI
        try:
            self.player.volumeChanged.connect(lambda f: self.volume_dial.setValue(int(f * 100)))
            self.player.volumeChanged.connect(lambda f: self.volume_label.setText(str(int(f * 100))))
            self.player.mutedChanged.connect(lambda m: self.mute_action.setChecked(bool(m)))
        except Exception:
            pass

        actStop = QAction(QIcon("icons/stop.svg"), "", self)
        actStop.triggered.connect(self.on_stop); tb.addAction(actStop)
        
        actNext = QAction(QIcon("icons/next.svg"), "", self)
        actNext.setShortcut("Ctrl+Right")
        actNext.triggered.connect(self.on_next); tb.addAction(actNext)

        tb.addSeparator()
        actAddFiles = QAction(QIcon("icons/addfiles.svg"), "", self)
        actAddFiles.triggered.connect(self.on_add_files)
        tb.addAction(actAddFiles)
        # direct-path play action (enter local path or URL)
        actOpenPath = QAction(QIcon("icons/link.svg"), "Open Path/URL", self)
        actOpenPath.triggered.connect(self.on_open_path)
        tb.addAction(actOpenPath)

    # Use the woodgrain background by default (if present)
        
        actAddFolder = QAction(QIcon("icons/addfolder.svg"), "", self)
        actAddFolder.triggered.connect(self.on_add_folder)

        tb.addAction(actAddFolder)

        tb.addSeparator()

        # Keyboard shortcuts for volume
        vol_up = QAction("Vol+")
        vol_up.setShortcut(QKeySequence("Ctrl+="))
        vol_up.triggered.connect(lambda: self._change_volume_by(5))
        self.addAction(vol_up)

        vol_dn = QAction("Vol-")
        vol_dn.setShortcut(QKeySequence("Ctrl+-"))
        vol_dn.triggered.connect(lambda: self._change_volume_by(-5))
        self.addAction(vol_dn)

        actSave = QAction(QIcon("icons/download.svg"), "", self)
        actSave.triggered.connect(self.on_save_playlist)
        tb.addAction(actSave)
        
        actLoad = QAction(QIcon("icons/playlist.svg"), "", self)
        actLoad.triggered.connect(self.import_plex_playlist)
        tb.addAction(actLoad)

        tb.addSeparator()
        actRemove = QAction(QIcon("icons/trash.svg"), "", self)
        actRemove.setShortcut(QKeySequence.Delete)
        actRemove.triggered.connect(self.on_remove_selected); tb.addAction(actRemove)

    # Build right-side analog control panel (created later once central widget exists)
    # self._build_side_panel() will be called from __init__ after the central widget is set.

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
        except Exception as e:
            QMessageBox.warning(self, "Play error", str(e))

    def _build_side_panel(self):
        """Create a right-docked woodgrain-style control panel with large dials.

        This panel contains Volume, Bass, and Treble QDials (UI-only for bass/treble)
        and a retro numeric display for the current volume. The Volume dial is
        kept in sync with the toolbar volume dial and the Player via signals.
        """
        from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout
        from PySide6.QtWidgets import QSizePolicy

        self.side_panel = QFrame()
        self.side_panel.setObjectName("sidePanel")
        self.side_panel.setFixedWidth(340)
        # Prefer a woodgrain image if available, otherwise use a warm gradient
        wood_path = os.path.join(os.path.dirname(__file__), '..', 'icons', 'woodgrain.png')
        if os.path.exists(os.path.normpath(wood_path)):
            # Use CSS to set a background image (repeat) and add a semi-opaque overlay for contrast
            # Use absolute path to avoid issues with relative CSS resolution
            abspath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'icons', 'woodgrain.png'))
            self.side_panel.setStyleSheet(
                f"#sidePanel {{ background-image: url(file://{abspath}); background-repeat: repeat; background-position: center; background-attachment: scroll; border-left: 2px solid #3b2b1a; }}"
            )
        else:
            self.side_panel.setStyleSheet(
                "#sidePanel { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #6b3f1e, stop:0.3 #8b5a2b, stop:0.6 #a66f3a, stop:1 #6b3f1e); border-left: 2px solid #3b2b1a; }"
            )

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # 7-segment style numeric display using QLCDNumber
        from PySide6.QtWidgets import QLCDNumber
        self.retro_display = QLCDNumber()
        self.retro_display.setDigitCount(3)
        self.retro_display.setSegmentStyle(QLCDNumber.Filled)
        self.retro_display.display(self.volume_dial.value())
        self.retro_display.setStyleSheet("background: #200b00; color: #ffb86b; border-radius: 6px;")
        self.retro_display.setFixedHeight(64)
        layout.addWidget(self.retro_display)
        try:
            from PySide6.QtWidgets import QGraphicsDropShadowEffect
            from PySide6.QtGui import QColor
            glow = QGraphicsDropShadowEffect(self.retro_display)
            glow.setBlurRadius(24)
            glow.setOffset(0, 0)
            glow.setColor(QColor(255, 184, 107, 200))
            self.retro_display.setGraphicsEffect(glow)
        except Exception:
            pass

        # Large dials row with circular bezels and shadows
        dial_row = QHBoxLayout()

        from PySide6.QtWidgets import QFrame, QVBoxLayout
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor

        # Helper to create a bezel frame that holds a dial
        def _bezel_with_dial(dial: QDial, size: int):
            frame = QFrame()
            frame.setFixedSize(size + 28, size + 28)
            frame.setStyleSheet(
                "background: qradialgradient(cx:0.5, cy:0.4, radius:1.0, stop:0 #e9d6bd, stop:0.6 #c89b6a, stop:1 #7a4b24);"
                "border-radius: %dpx; border: 2px solid #5a3b22;"
                % ((size + 28) // 2)
            )
            v = QVBoxLayout()
            v.setContentsMargins(8, 8, 8, 8)
            v.addWidget(dial, alignment=Qt.AlignCenter)
            frame.setLayout(v)
            # shadow
            effect = QGraphicsDropShadowEffect()
            effect.setBlurRadius(30)
            effect.setOffset(0, 6)
            effect.setColor(QColor(0, 0, 0, 160))
            frame.setGraphicsEffect(effect)
            return frame

        self.side_vol_dial = QDial()
        self.side_vol_dial.setRange(0, 100)
        self.side_vol_dial.setValue(self.volume_dial.value())
        self.side_vol_dial.setNotchesVisible(True)
        self.side_vol_dial.setFixedSize(160, 160)
        dial_row.addWidget(_bezel_with_dial(self.side_vol_dial, 160))

        self.side_bass_dial = QDial()
        self.side_bass_dial.setRange(-12, 12)
        self.side_bass_dial.setValue(0)
        self.side_bass_dial.setFixedSize(120, 120)
        dial_row.addWidget(_bezel_with_dial(self.side_bass_dial, 120))

        self.side_treble_dial = QDial()
        self.side_treble_dial.setRange(-12, 12)
        self.side_treble_dial.setValue(0)
        self.side_treble_dial.setFixedSize(120, 120)
        dial_row.addWidget(_bezel_with_dial(self.side_treble_dial, 120))

        layout.addLayout(dial_row)

        # Labels under dials
        lbl_row = QHBoxLayout()
        lbl_row.addWidget(QLabel("Volume"))
        lbl_row.addWidget(QLabel("Bass"))
        lbl_row.addWidget(QLabel("Treble"))
        layout.addLayout(lbl_row)

        # Placeholder buttons for repeat/loudness/mute (non-blocking)
        btn_row = QHBoxLayout()
        from PySide6.QtWidgets import QPushButton
        self.btn_repeat = QPushButton("Repeat")
        self.btn_loud = QPushButton("Loud")
        self.btn_mini_mute = QPushButton("Mute")
        # style buttons to fit the vintage panel
        for b in (self.btn_repeat, self.btn_loud, self.btn_mini_mute):
            b.setStyleSheet("background: rgba(255,255,255,0.08); color: #fff; border: 1px solid #6b4a2b; padding: 6px; border-radius: 4px;")
        btn_row.addWidget(self.btn_repeat)
        btn_row.addWidget(self.btn_loud)
        btn_row.addWidget(self.btn_mini_mute)
        layout.addLayout(btn_row)

        self.side_panel.setLayout(layout)

        # Add an overlay widget on top of the side panel for contrast (semi-opaque)
        overlay = QLabel(self.side_panel)
        overlay.setObjectName("sideOverlay")
        overlay.setStyleSheet("background: rgba(0,0,0,0.25); border: none;")
        overlay.setGeometry(0, 0, self.side_panel.width(), self.side_panel.height())
        overlay.lower()  # put under the controls we add later

        # Add the side panel as a dock-like widget on the right by using a layout
        # around the central widget: make a container widget to hold table + panel
        try:
            central = self.centralWidget()
            from PySide6.QtWidgets import QWidget, QHBoxLayout
            container = QWidget()
            h = QHBoxLayout()
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(0)
            h.addWidget(central)
            h.addWidget(self.side_panel)
            container.setLayout(h)
            self.setCentralWidget(container)
        except Exception:
            # If central widget is not ready, ignore — caller may add later
            pass

        # Wire volume sync: toolbar dial <-> side dial -> player
        def _side_to_toolbar(val: int):
            # update toolbar dial without triggering recursive calls
            if self.volume_dial.value() != val:
                self.volume_dial.blockSignals(True)
                self.volume_dial.setValue(val)
                self.volume_dial.blockSignals(False)
            # update retro display and tell the player
            try:
                self.retro_display.display(int(val))
            except Exception:
                # fallback for older widget types
                try:
                    self.retro_display.setText(str(val)
                    )
                except Exception:
                    pass
            try:
                self.player.set_volume(float(val) / 100.0)
            except Exception:
                pass

        def _toolbar_to_side(val: int):
            if self.side_vol_dial.value() != val:
                self.side_vol_dial.blockSignals(True)
                self.side_vol_dial.setValue(val)
                self.side_vol_dial.blockSignals(False)
            try:
                self.retro_display.display(int(val))
            except Exception:
                try:
                    self.retro_display.setText(str(val))
                except Exception:
                    pass

        try:
            self.side_vol_dial.valueChanged.connect(_side_to_toolbar)
            self.volume_dial.valueChanged.connect(_toolbar_to_side)
            # initialize display
            self.retro_display.display(self.volume_dial.value())
        except Exception:
            pass

        # Wire bass/treble dials to player (UI-only EQ)
        try:
            self.side_bass_dial.valueChanged.connect(lambda v: self.player.set_bass(int(v)))
            self.side_treble_dial.valueChanged.connect(lambda v: self.player.set_treble(int(v)))
            # optional: reflect player-side changes back to UI if other code modifies them
            self.player.bassChanged.connect(lambda db: self.side_bass_dial.setValue(int(db)))
            self.player.trebleChanged.connect(lambda db: self.side_treble_dial.setValue(int(db)))
        except Exception:
            pass

    # --- Volume helpers ---
    def _on_volume_dial_changed(self, val: int):
        # dial gives 0..100; player expects 0.0..1.0
        f = float(val) / 100.0
        try:
            self.player.set_volume(f)
        except Exception:
            pass
        # update numeric readout in toolbar
        try:
            self.volume_label.setText(str(val))
        except Exception:
            pass

    def _change_volume_by(self, delta: int):
        v = max(0, min(100, self.volume_dial.value() + delta))
        self.volume_dial.setValue(v)
        self._on_volume_dial_changed(v)

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

    def on_set_panel_background(self):
        """Open a file dialog, copy the chosen image into icons/panel_background.png
        and update the side panel stylesheet live."""
        # No-op: panel background is hardcoded to woodgrain for now.
        return

    def on_open_path(self):
        """Prompt the user for a local path or URL and play it directly."""
        text, ok = QInputDialog.getText(self, "Open Path or URL", "Path or URL:")
        if not ok or not text:
            return
        p = text.strip().replace("\\ ", " ")
        p = os.path.expanduser(p)
        p = os.path.normpath(p)

        # If this is a local file, add to queue (if not already present)
        try:
            if os.path.exists(p):
                # add_paths returns number added; if zero it was duplicate
                _ = self.model.add_paths([p])
                # find the row index for the path and select it
                try:
                    idx = self.model.paths().index(os.path.abspath(p))
                except ValueError:
                    idx = None
                if idx is not None:
                    self.current_row = idx
                    self.table.selectRow(idx)
                # play the added file
                self.player.play(p)
                self.play_btn.setActive(True)
                self.statusBar().showMessage(f"Playing: {os.path.basename(p)}")
                return
            else:
                # Not a local file — treat as URL and attempt to play directly
                self.player.play(p)
                self.play_btn.setActive(True)
                self.statusBar().showMessage(f"Playing: {p}")
                return
        except Exception as e:
            QMessageBox.warning(self, "Play error", str(e))

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
