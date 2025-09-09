import sys, os
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTableView, QFileDialog, QToolBar, QMessageBox, QHeaderView
)
from PySide6.QtGui import QAction, QKeySequence, QIcon
from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtWidgets import QSlider, QLabel, QStyle, QProgressBar, QApplication, QPushButton
from PySide6.QtMultimediaWidgets import QVideoWidget  # ensures multimedia backend loads
from PySide6.QtMultimedia import QMediaPlayer

from .queue_model import QueueModel
from . import playlist
from .player import Player

AUDIO_EXTS = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}

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

        # Make “Title” column stretch
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)

        # Optional: Auto-size Artist/Album columns to contents
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        # Fix “Play Count” column width
        hdr.setSectionResizeMode(3, QHeaderView.Fixed)
        fm = self.table.fontMetrics()
        six_zeroes = fm.horizontalAdvance("0" * 8)  # Try 8 digits unless you expect 100 trillion plays!
        self.table.setColumnWidth(3, six_zeroes)


    def _build_status_bar(self):
        sb = self.statusBar()
        sb.showMessage("Ready")
       
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 1)    # 0/0 until we know the duration
        sb.addPermanentWidget(self.progress)

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
        self.player.durationChanged.connect(self.progress.setMaximum)
        self.player.positionChanged.connect(self.progress.setValue)

        # position & duration → UI updates
        self.player.positionChanged.connect(self._on_position)
        self.player.durationChanged.connect(self._on_duration)

    def _build_toolbar(self):
        tb = QToolBar("Main"); tb.setMovable(False); self.addToolBar(tb)

        actPlay = QAction(QIcon("icons/play.svg"), "", self)
        actPlay.setShortcut(QKeySequence(Qt.Key_Space))
        actPlay.triggered.connect(self.on_play); tb.addAction(actPlay)

        actStop = QAction(QIcon("icons/stop.svg"), "", self)
        actStop.triggered.connect(self.on_stop); tb.addAction(actStop)
        
        actNext = QAction(QIcon("icons/next.svg"), "", self)
        actNext.setShortcut("Ctrl+Right")
        actNext.triggered.connect(self.on_next); tb.addAction(actNext)

        tb.addSeparator()
        actAddFiles = QAction(QIcon("icons/addfiles.svg"), "", self)
        actAddFiles.triggered.connect(self.on_add_files)
        tb.addAction(actAddFiles)
        
        actAddFolder = QAction(QIcon("icons/addfolder.svg"), "", self)
        actAddFolder.triggered.connect(self.on_add_folder)
        tb.addAction(actAddFolder)

        tb.addSeparator()
        actSave = QAction(QIcon("icons/download.svg"), "", self)
        actSave.triggered.connect(self.on_save_playlist)
        tb.addAction(actSave)
        
        actLoad = QAction(QIcon("icons/upload.svg"), "", self)
        actLoad.triggered.connect(self.on_load_playlist)
        tb.addAction(actLoad)

        tb.addSeparator()
        actRemove = QAction(QIcon("icons/trash.svg"), "", self)
        actRemove.setShortcut(QKeySequence.Delete)
        actRemove.triggered.connect(self.on_remove_selected); tb.addAction(actRemove)

    # --- Playback helpers ---
    def _play_row(self, row: int):
        paths = self.model.paths()
        if not paths or row is None or row < 0 or row >= len(paths):
            return
        self.current_row = row
        path = paths[row]
        try:
            self.player.play(path)                 # <-- Don't remove this line!
            self.table.selectRow(row)
            title = self.model.data(self.model.index(row, 0))
            self.statusBar().showMessage(f"Playing: {title}")
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

    def _on_table_play(self, index: QModelIndex):
        # store current row so metadata updates land in the right place
        self.current_row = index.row()
        # get the file path from your model—replace FilePathRole with your actual role
        path = self.model.data(index, role=QueueModel.FilePathRole)
        if path:
            self.player.play(path)

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

def main():
    app = QApplication(sys.argv)
    w = MainWindow(); w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
