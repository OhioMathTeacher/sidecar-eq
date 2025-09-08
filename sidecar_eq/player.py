from PySide6.QtCore import QObject, QProcess, Signal, Qt

class Player(QObject):
    finished = Signal(int, QProcess.ExitStatus)   # arguments match QProcess.finished

    def __init__(self):
        super().__init__()
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.finished.connect(self.finished)

    def play(self, path: str, volume: float | None = None):
        if sys.platform != "darwin":
            raise RuntimeError("Playback backend only supports macOS afplay.")
        args = []
        if volume is not None:
            args += ["-v", str(max(0.0, min(1.0, volume)))]
        args.append(path)
        self.proc.start("afplay", args)

    def stop(self):
        if self.proc.state() != QProcess.NotRunning:
            self.proc.kill()
        self.proc.waitForFinished(1000)

    def is_playing(self) -> bool:
        return self.proc.state() == QProcess.Running

