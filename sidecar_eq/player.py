from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtMultimedia import QMediaPlayer

class Player(QObject):
    def __init__(self):
        super().__init__()
        self._player = QMediaPlayer()
        
    def setSource(self, path: str):
        url = QUrl.fromLocalFile(path)
        self._player.setSource(url)

    def play(self, path: str):
    """Load & play a new file in one call."""
    self.setSource(path)
    self._player.play()


    def pause(self):
        self._player.pause()

    def stop(self):
        self._player.stop()

    def is_playing(self):
        return self._player.playbackState() == QMediaPlayer.PlayingState
