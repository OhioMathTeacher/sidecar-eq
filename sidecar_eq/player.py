from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

class Player(QObject):
    # forward QMediaPlayer’s 64-bit positionChanged out
    positionChanged    = Signal("qint64")
    durationChanged    = Signal("qint64")
    mediaStatusChanged = Signal(QMediaPlayer.MediaStatus)

    def __init__(self):
        super().__init__()
        self._audio_output = QAudioOutput()
        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._audio_output)

        # now this will connect cleanly
        self._player.positionChanged.connect(self.positionChanged)
        self._player.durationChanged.connect(self.durationChanged)
        self._player.mediaStatusChanged.connect(self.mediaStatusChanged)
        
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
