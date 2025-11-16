#!/usr/bin/env python3
"""Test Qt multimedia backend availability."""

from PySide6 import QtCore
from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
import sys

app = QApplication(sys.argv)

print(f"Qt version: {QtCore.qVersion()}")
print(f"\nQt library paths:")
for p in QtCore.QCoreApplication.libraryPaths():
    print(f"  {p}")

print(f"\n Creating QMediaPlayer...")
player = QMediaPlayer()
audio_output = QAudioOutput()
player.setAudioOutput(audio_output)

print(f"QMediaPlayer error: {player.errorString()}")
print(f"QMediaPlayer state: {player.playbackState()}")
