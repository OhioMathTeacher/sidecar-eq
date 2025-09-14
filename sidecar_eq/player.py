from PySide6.QtCore import QObject, Signal, QUrl, Slot
import os
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
class Player(QObject):
    # forward QMediaPlayer’s 64-bit positionChanged out
    positionChanged    = Signal("qlonglong")
    durationChanged    = Signal("qlonglong")
    mediaStatusChanged = Signal(QMediaPlayer.MediaStatus)
    # emit a simple boolean for UI controls to bind to
    playingChanged = Signal(bool)
    # volume/mute signals: volume is 0.0-1.0
    volumeChanged = Signal(float)
    mutedChanged = Signal(bool)
    # EQ controls (UI-only for now): integer dB steps
    bassChanged = Signal(int)
    trebleChanged = Signal(int)
    # notify UI when the source (path/URL) changes
    sourceChanged = Signal(str)

    def __init__(self):
        super().__init__()
        self._audio_output = QAudioOutput()
        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._audio_output)
        # backend state: UI should own widgets (QPushButton) and connect to
        # the controller's slots/signals. Store current source for toggle
        # behavior.
        self._current_source: str | None = None
        # volume state
        self._volume: float = 1.0
        self._muted: bool = False
        # ensure audio output starts at default volume
        try:
            self._audio_output.setVolume(self._volume)
        except Exception:
            pass
        # forward playbackState changes so UI can keep controls in sync
        self._player.playbackStateChanged.connect(self._on_playback_state_changed)

        # now this will connect cleanly
        self._player.positionChanged.connect(self.positionChanged)
        self._player.durationChanged.connect(self.durationChanged)
        self._player.mediaStatusChanged.connect(self.mediaStatusChanged)
        
    def setSource(self, path: str):
        # Accept either local file paths or remote URLs.
        # Normalize common shell-escaped paths (e.g. "/Volumes/Music/My\ File.mp3").
        p = path.strip()
        # undo shell-style escaping of spaces
        p = p.replace("\\ ", " ")
        p = os.path.expanduser(p)
        p = os.path.normpath(p)

        # If this is an existing local file, use fromLocalFile so Qt opens it reliably
        if os.path.exists(p):
            url = QUrl.fromLocalFile(p)
            self._player.setSource(url)
            self._current_source = p
            try:
                self.sourceChanged.emit(self._current_source)
            except Exception:
                pass
            return

        # otherwise fall back to user input parsing (for http(s) etc.)
        url = QUrl.fromUserInput(path)
        self._player.setSource(url)
        self._current_source = path
        try:
            self.sourceChanged.emit(self._current_source)
        except Exception:
            pass

    def play(self, path: str | None = None):
        """Load & play a new file in one call.

        If `path` is None, play the currently loaded source (if any).
        """
        if path is not None:
            self.setSource(path)
        if self._current_source is None:
            # Nothing loaded; UI should set a source first.
            return
        self._player.play()

    def pause(self):
        self._player.pause()

    def stop(self):
        self._player.stop()

    def is_playing(self):
        return self._player.playbackState() == QMediaPlayer.PlayingState

    # Public slot intended for UI to call. `checked` comes from a
    # checkable QPushButton (True -> play, False -> pause).
    @Slot(bool)
    def toggle_play(self, checked: bool):
        """Slot for UI: start or pause playback depending on checked."""
        if checked:
            if self._current_source is None:
                # Nothing loaded; no-op. UI should load a source first.
                return
            self._player.play()
        else:
            self._player.pause()

    @Slot(bool)
    def set_playing(self, playing: bool):
        """Programmatically set playing state. Equivalent to toggling."""
        if playing:
            if self._current_source is None:
                return
            self._player.play()
        else:
            self._player.pause()

    @Slot(int)
    def seek(self, ms: int):
        """Seek to ms milliseconds in the current media."""
        try:
            # QMediaPlayer expects an integer number of milliseconds
            self._player.setPosition(int(ms))
        except Exception:
            pass

    @Slot(float)
    def set_volume(self, v: float):
        """Set volume (float 0.0..1.0). Emits volumeChanged."""
        try:
            vol = max(0.0, min(1.0, float(v)))
        except Exception:
            return
        self._volume = vol
        try:
            self._audio_output.setVolume(self._volume)
        except Exception:
            pass
        try:
            self.volumeChanged.emit(self._volume)
        except Exception:
            pass

    @Slot(bool)
    def set_muted(self, muted: bool):
        """Mute/unmute. When muting, remember previous volume; when unmuting, restore."""
        try:
            muted = bool(muted)
        except Exception:
            return
        if muted:
            # remember current volume and set to zero
            self._prev_volume = getattr(self, "_volume", 1.0)
            try:
                self._audio_output.setVolume(0.0)
            except Exception:
                pass
            self._muted = True
        else:
            # restore previous
            prev = getattr(self, "_prev_volume", 1.0)
            try:
                self._audio_output.setVolume(prev)
            except Exception:
                pass
            self._volume = prev
            self._muted = False
        try:
            self.mutedChanged.emit(self._muted)
            self.volumeChanged.emit(getattr(self, "_volume", 0.0))
        except Exception:
            pass

    @Slot(int)
    def set_bass(self, db: int):
        """Set bass gain in dB (UI only). Emits bassChanged."""
        try:
            self._bass = int(db)
        except Exception:
            return
        try:
            self.bassChanged.emit(self._bass)
        except Exception:
            pass

    @Slot(int)
    def set_treble(self, db: int):
        """Set treble gain in dB (UI only). Emits trebleChanged."""
        try:
            self._treble = int(db)
        except Exception:
            return
        try:
            self.trebleChanged.emit(self._treble)
        except Exception:
            pass

    def _on_playback_state_changed(self, state):
        # Emit a simple boolean: True when playing, False otherwise.
        is_playing = state == QMediaPlayer.PlayingState
        try:
            self.playingChanged.emit(is_playing)
        except RuntimeError:
            # In some teardown cases signals may be disconnected; ignore.
            pass
