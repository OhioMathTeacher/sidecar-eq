# Minimal macOS player using the built-in `afplay` command.
import subprocess, sys, shutil

class Player:
    def __init__(self):
        self.proc = None
        self.ok = sys.platform == "darwin" and shutil.which("afplay") is not None

    def play(self, path: str, volume: float | None = None):
        if not self.ok:
            raise RuntimeError("No playback backend available (afplay not found).")
        self.stop()
        cmd = ["afplay"]
        if volume is not None:
            # 0.0 .. 1.0
            cmd += ["-v", str(max(0.0, min(1.0, volume)))]
        cmd += [path]
        self.proc = subprocess.Popen(cmd)

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=1)
            except Exception:
                self.proc.kill()
        self.proc = None

    def is_playing(self) -> bool:
        return self.proc is not None and self.proc.poll() is None
