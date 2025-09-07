import sys, os
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTableView, QFileDialog, QToolBar, QMessageBox
)
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import Qt

# we'll add this file next
from .queue_model import QueueModel
from . import playlist

AUDIO_EXTS = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sidecar EQ — Preview")
        self.resize(900, 520)

        self.table = QTableView()
        self.model = QueueModel(self)
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.ExtendedSelection)
        self.setCentralWidget(self.table)

        self._build_toolbar()
        self.statusBar().showMessage("Ready")

    def _build_toolbar(self):
        tb = QToolBar("Main"); tb.setMovable(False); self.addToolBar(tb)

        actPlay = QAction("Play", self); actPlay.setShortcut(QKeySequence(Qt.Key_Space))
        actPlay.triggered.connect(self.on_play); tb.addAction(actPlay)

        actPause = QAction("Pause", self); actPause.triggered.connect(self.on_pause)
        tb.addAction(actPause)

        actNext = QAction("Next", self); actNext.setShortcut("Ctrl+Right")
        actNext.triggered.connect(self.on_next); tb.addAction(actNext)

        tb.addSeparator()
        actAddFiles = QAction("+ Files", self); actAddFiles.triggered.connect(self.on_add_files); tb.addAction(actAddFiles)
        actAddFolder = QAction("+ Folder", self); actAddFolder.triggered.connect(self.on_add_folder); tb.addAction(actAddFolder)

        tb.addSeparator()
        actSave = QAction("Save", self); actSave.triggered.connect(self.on_save_playlist); tb.addAction(actSave)
        actLoad = QAction("Load", self); actLoad.triggered.connect(self.on_load_playlist); tb.addAction(actLoad)

        tb.addSeparator()
        actRemove = QAction("Remove", self); actRemove.setShortcut(QKeySequence.Delete)
        actRemove.triggered.connect(self.on_remove_selected); tb.addAction(actRemove)

    # --- stubs for now ---
    def on_play(self):   self.statusBar().showMessage("Play (stub)")
    def on_pause(self):  self.statusBar().showMessage("Pause (stub)")
    def on_next(self):   self.statusBar().showMessage("Next (stub)")

    def on_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Add Audio Files", "",
                    "Audio Files (*.wav *.flac *.mp3 *.ogg *.m4a)")
        if files:
            count = self.model.add_paths(files)
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
        inp, _ = QFileDialog.getOpenFileName(self, "Load Playlist (JSON or M3U)", "",
                                             "Playlists (*.json *.m3u *.m3u8)")
        if not inp: return
        suffix = Path(inp).suffix.lower()
        if suffix == ".json":
            paths = playlist.load_json(inp)
        else:
            lines = Path(inp).read_text(errors="ignore").splitlines()
            paths = [ln for ln in lines if ln and not ln.startswith("#")]
        if paths:
            count = self.model.add_paths(paths)
            self.statusBar().showMessage(f"Loaded {count} items")
        else:
            QMessageBox.information(self, "Load Playlist", "No paths found in playlist.")

def main():
    app = QApplication(sys.argv)
    w = MainWindow(); w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
