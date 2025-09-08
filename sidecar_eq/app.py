import sys, os
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTableView, QFileDialog, QToolBar, QMessageBox
)
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtWidgets import QSlider, QLabel, QStyle, QProgressBar, QApplication
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

        self.player = Player()
        self.current_row = None

        self.table = QTableView()
        self.model = QueueModel(self)
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.ExtendedSelection)
        self.setCentralWidget(self.table)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        self.table.setAlternatingRowColors(False)

        self._build_toolbar()
        self.statusBar().showMessage("Ready")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setEnabled(False)
        self.statusBar().addPermanentWidget(self.slider)
        self.timeLabel = QLabel("00:00 / 00:00")
        self.statusBar().addPermanentWidget(self.timeLabel)
        self.slider.sliderMoved.connect(self.player._player.setPosition)
        p = self.player._player
        p.mediaStatusChanged.connect(lambda status: status == QMediaPlayer.EndOfMedia and self.on_next())
        self.player.positionChanged.connect(self._on_position)
        self.player.durationChanged.connect(self._on_duration)  
        self.player.positionChanged.connect(self.slider.setValue)
        self.player.durationChanged.connect(self.slider.setMaximum)

    def _build_toolbar(self):
        tb = QToolBar("Main"); tb.setMovable(False); self.addToolBar(tb)

        actPlay = QAction("Play", self)
        actPlay.setShortcut(QKeySequence(Qt.Key_Space))
        actPlay.triggered.connect(self.on_play); tb.addAction(actPlay)

        actStop = QAction("Stop", self)
        actStop.triggered.connect(self.on_stop); tb.addAction(actStop)

        actNext = QAction("Next", self)
        actNext.setShortcut("Ctrl+Right")
        actNext.triggered.connect(self.on_next); tb.addAction(actNext)

        tb.addSeparator()
        actAddFiles = QAction("+ Files", self); actAddFiles.triggered.connect(self.on_add_files); tb.addAction(actAddFiles)
        actAddFolder = QAction("+ Folder", self); actAddFolder.triggered.connect(self.on_add_folder); tb.addAction(actAddFolder)

        tb.addSeparator()
        actSave = QAction("Save", self); actSave.triggered.connect(self.on_save_playlist); tb.addAction(actSave)
        actLoad = QAction("Load", self); actLoad.triggered.connect(self.on_load_playlist); tb.addAction(actLoad)

        tb.addSeparator()
        actRemove = QAction("Remove", self)
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
            self.player.play(path)
            self.table.selectRow(row)
            self.statusBar().showMessage(f"Playing: {Path(path).name}")
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

    def _on_duration(self, ms: int):
        """Called when the track duration is known; set slider range."""
        self.slider.setRange(0, ms)

    def _on_position(self, ms: int):
        """Called as playback position changes; update slider + label."""
        self.slider.setValue(ms)
        total = self.player._player.duration() or 0
        # format mm:ss
        elapsed = f"{ms//60000:02d}:{(ms//1000)%60:02d}"
        length  = f"{total//60000:02d}:{(total//1000)%60:02d}"
        self.timeLabel.setText(f"{elapsed} / {length}")


def main():
    app = QApplication(sys.argv)
    w = MainWindow(); w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
