from PySide6.QtWidgets import (
    QApplication,
    QPushButton,
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QLabel,
    QSlider,
    QHBoxLayout,
)
from PySide6.QtCore import Qt
import sys
from sidecar_eq.player import Player
from sidecar_eq.yt_helper import resolve_or_download
import atexit
import os
 
import shutil
import threading
import subprocess

tmp_files = []


def main():
    app = QApplication(sys.argv)

    player = Player()

    win = QWidget()
    win.setWindowTitle("Player UI Test")
    layout = QVBoxLayout(win)

    # yt-dlp status + install button
    top_row = QHBoxLayout()
    ytdlp_label = QLabel("")
    ytdlp_btn = QPushButton("Install/Update yt-dlp")
    top_row.addWidget(ytdlp_label)
    top_row.addWidget(ytdlp_btn)
    layout.addLayout(top_row)

    def check_ytdlp():
        ytdlp = shutil.which("yt-dlp") or shutil.which("youtube-dl")
        if not ytdlp:
            ytdlp_label.setText("yt-dlp: not installed")
            return False
        try:
            out = subprocess.run([ytdlp, "--version"], capture_output=True, text=True, check=True)
            ytdlp_label.setText(f"yt-dlp: {out.stdout.strip()}")
            return True
        except Exception:
            ytdlp_label.setText("yt-dlp: unknown version")
            return True

    def install_ytdlp():
        # run pip install in the project venv
        def run():
            # try to infer project venv python; fall back to system python
            venv_python = os.path.join(os.getcwd(), ".venv", "bin", "python")
            if not os.path.exists(venv_python):
                venv_python = shutil.which("python")
            if venv_python is None:
                print("No python found to install yt-dlp")
                return
            cmd = [venv_python, "-m", "pip", "install", "--upgrade", "yt-dlp"]
            print("Running:", " ".join(cmd))
            subprocess.run(cmd)
            check_ytdlp()
        threading.Thread(target=run, daemon=True).start()

    ytdlp_btn.clicked.connect(lambda: install_ytdlp())
    check_ytdlp()

    # source entry
    src_layout = QHBoxLayout()
    src_label = QLabel("Path/URL:")
    src_entry = QLineEdit()
    src_entry.setPlaceholderText("/path/to/file.mp3 or https://...")
    src_layout.addWidget(src_label)
    src_layout.addWidget(src_entry)
    layout.addLayout(src_layout)

    # diagnostic button to check the entered path/URL
    diag_btn = QPushButton("Check Source")
    layout.addWidget(diag_btn)

    # play button
    btn = QPushButton("Play")
    btn.setCheckable(True)
    layout.addWidget(btn)

    # status label
    status_label = QLabel("")
    layout.addWidget(status_label)

    # position slider + labels
    seek_row = QHBoxLayout()
    pos_label = QLabel("00:00")
    slider = QSlider()
    slider.setOrientation(Qt.Horizontal)
    slider.setRange(0, 0)
    dur_label = QLabel("00:00")
    seek_row.addWidget(pos_label)
    seek_row.addWidget(slider)
    seek_row.addWidget(dur_label)
    layout.addLayout(seek_row)

    # wire: when toggled, use set_playing; when toggled on and the
    # entry has text, call play(...) to load and play that source.
    def on_toggled(checked: bool):
        if checked:
            text = src_entry.text().strip()
            if text:
                # If this looks like a YouTube page URL, try to resolve it
                if "youtube.com/watch" in text or "youtu.be/" in text:
                    success, source, msg = resolve_or_download(text, download_if_needed=True)
                    if not success:
                        status_label.setText(f"yt-dlp: {msg}")
                        print("yt-dlp ->", msg)
                        btn.setChecked(False)
                        return
                    # if source is a temp file, remember it for cleanup
                    if os.path.exists(source):
                        tmp_files.append(source)
                    player.play(source)
                else:
                    player.play(text)
            else:
                player.set_playing(True)
        else:
            player.set_playing(False)

    btn.toggled.connect(on_toggled)

    def check_source():
        text = src_entry.text().strip()
        if not text:
            status_label.setText("No path provided")
            return
        p = text.replace("\\ ", " ")
        p = os.path.expanduser(p)
        p = os.path.normpath(p)
        exists = os.path.exists(p)
        readable = os.access(p, os.R_OK)
        short = p if len(p) < 120 else p[:120] + "..."
        status_label.setText(f"exists: {exists}, readable: {readable}, path: {short}")
        print("diag ->", p, "exists:", exists, "readable:", readable)
        ffprobe = shutil.which("ffprobe")
        if exists and ffprobe:
            try:
                res = subprocess.run([ffprobe, "-v", "error", "-show_format", "-show_streams", p], capture_output=True, text=True, check=False, timeout=10)
                print("ffprobe output:\n", res.stdout or res.stderr)
                if res.returncode == 0:
                    status_label.setText(status_label.text() + "; ffprobe OK")
                else:
                    status_label.setText(status_label.text() + "; ffprobe error")
            except Exception as e:
                print("ffprobe exception:", e)
                status_label.setText(status_label.text() + "; ffprobe failed")
        elif exists:
            status_label.setText(status_label.text() + "; ffprobe not found")

    diag_btn.clicked.connect(lambda: check_source())

    # keep button in sync with player state
    player.playingChanged.connect(lambda playing: btn.setChecked(playing))

    # show media status updates
    def on_media_status(st):
        # st is a QMediaPlayer.MediaStatus enum value; show numeric + repr
        try:
            status_label.setText(f"mediaStatus: {int(st)}")
        except Exception:
            status_label.setText(f"mediaStatus: {st}")
        print("mediaStatus ->", st)

    player.mediaStatusChanged.connect(on_media_status)

    # helper to format milliseconds to H:MM:SS or MM:SS
    def _ms_to_hms(ms: int) -> str:
        if ms is None:
            return "00:00"
        s = int(ms // 1000)
        h, s = divmod(s, 3600)
        m, s = divmod(s, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    # seeking state to avoid feedback while user is dragging
    _user_seeking = {"val": False}

    def on_duration_changed(d):
        try:
            dur = int(d)
        except Exception:
            dur = 0
        slider.setRange(0, max(0, dur))
        dur_label.setText(_ms_to_hms(dur))

    def on_position_changed(p):
        try:
            pos = int(p)
        except Exception:
            pos = 0
        if not _user_seeking["val"]:
            slider.setValue(pos)
            pos_label.setText(_ms_to_hms(pos))

    player.durationChanged.connect(on_duration_changed)
    player.positionChanged.connect(on_position_changed)

    # slider interactions
    def _on_slider_pressed():
        _user_seeking["val"] = True

    def _on_slider_released():
        _user_seeking["val"] = False
        v = int(slider.value())
        try:
            # set position on the underlying QMediaPlayer
            player._player.setPosition(v)
        except Exception as e:
            print("seek failed:", e)

    def _on_slider_moved(val):
        pos_label.setText(_ms_to_hms(int(val)))

    slider.sliderPressed.connect(_on_slider_pressed)
    slider.sliderReleased.connect(_on_slider_released)
    slider.sliderMoved.connect(_on_slider_moved)

    # connect to low-level errorOccurred if available (Qt 6.6+)
    if hasattr(player._player, "errorOccurred"):
        try:
            player._player.errorOccurred.connect(lambda e, msg: (
                status_label.setText(f"error: {e} {msg}"), print("errorOccurred ->", e, msg)
            ))
        except Exception:
            pass
    else:
        # fallback: poll for mediaStatus changes and print available info
        pass

    win.show()
    # remove temp files on exit
    def _cleanup():
        for f in list(tmp_files):
            try:
                os.unlink(f)
                print("removed temp file", f)
            except Exception:
                pass

    atexit.register(_cleanup)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
