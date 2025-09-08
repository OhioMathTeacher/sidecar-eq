from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtMultimedia import QMediaPlayer

class Player(QObject):
    positionChanged = Signal(object)
    durationChanged = Signal(object)
    mediaStatusChanged = Signal(int)  # QMediaPlayer.MediaStatus as int

    def __init__(self):
        super().__init__()
        self._player = QMediaPlayer()
        self._player.positionChanged.connect(self.positionChanged)
        self._player.durationChanged.connect(self.durationChanged)
        self._player.mediaStatusChanged.connect(self.mediaStatusChanged)

    def setSource(self, path: str):
        url = QUrl.fromLocalFile(path)
        self._player.setSource(url)

    def play(self):
        self._player.play()

    def pause(self):
        self._player.pause()

    def stop(self):
        self._player.stop()

    def is_playing(self):
        return self._player.playbackState() == QMediaPlayer.PlayingState
