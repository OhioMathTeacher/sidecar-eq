# Sidecar EQ

**Your music. Your sound. Everywhere.**

A powerful music player with per-track EQ and volume memory. Set your perfect sound once per track - the app remembers forever. No more adjusting EQ between songs.

## 🎯 The Problem We're Solving

Every other music player (Spotify, iTunes, VLC) forces ONE EQ setting for ALL songs:
- "Hotel California" needs bass cut? Turn it down.
- Next song is "Billie Jean"? Now bass is too quiet!
- You're constantly adjusting, or you give up and leave it flat.

**Sidecar EQ is different**: Every song remembers YOUR perfect EQ and volume. Automatic. Forever.

## 📥 Download

### Pre-Built Applications

> **Coming Soon!** We're working on automated builds for all platforms.

Platform-specific executables will be available soon:
- **macOS**: Universal binary (Apple Silicon + Intel)
- **Windows**: Standalone `.exe`
- **Linux**: AppImage (portable, works everywhere)

Check the [Releases](https://github.com/OhioMathTeacher/sidecar-eq/releases) page for the latest downloads.

### Run from Source (All Platforms)

```bash
# Clone repository
git clone https://github.com/OhioMathTeacher/sidecar-eq.git
cd sidecar-eq

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install and run
pip install -e .
python -m sidecar_eq.app
```

## ✨ Key Features

- **🧠 Per-Track Memory**: Each song remembers your EQ and volume settings
- **🎛️ Real-Time EQ**: 7-band equalizer (60Hz-15kHz) with actual audio processing
- **🎚️ Individual Volume**: Set perfect loudness for each track
- **📊 LED Meters**: Real-time audio level visualization
- **📈 Auto-Analysis**: Background frequency response, loudness (LUFS), tempo detection
- **🔍 Metadata Search**: Quickly find tracks by artist, album, or title
- **⭐ Star Ratings**: Five-star rating system for organizing favorites
- ** Plex Integration**: Browse and play from your Plex media server
- **🎵 Multi-Format**: Supports audio (MP3, FLAC, WAV, M4A) and video files
- **🌙 Dark Theme**: Professional audio interface aesthetics
- **⌨️ Keyboard Shortcuts**: Efficient playback control

## 🚀 Quick Start

1. **Download** the app for your platform (or run from source)
2. **Add Music**: Click "+" to add local folders or configure Plex
3. **Play & Adjust**: Select a track, tweak EQ/volume to perfection
4. **Save Settings**: Click the save button - done! That track will always sound perfect
5. **Repeat**: Each song gets its own custom sound profile

## � Documentation

Detailed guides available in the [docs](docs/) folder:
- [Product Vision & Roadmap](docs/VERSION_GOALS.md)
- [Plex Setup Guide](docs/PLEX_HOME_USER_SETUP.md)
- [Build Instructions](docs/BUILD_NOTES.md)
- [All Documentation](docs/README.md)

## 💡 Tips

- **Keyboard Shortcuts**: Space = Play/Pause, Delete = Remove track
- **Multi-Select**: Cmd+Click or Shift+Click for bulk operations
- **Column Management**: Right-click headers to hide/show, drag to reorder
- **Layout Presets**: Switch between Full, Queue Only, EQ Only, or Search Only views

## 📜 License

Dual-licensed:

### AGPL v3 (Free & Open Source)
✅ Use it FREE  
✅ Modify it freely  
✅ Share improvements  
❗ Must share source if you distribute or deploy as a service  

### Commercial License
For closed-source or SaaS use without AGPL requirements.  
Contact: Michael Todd Edwards

### .sidecar Protocol (Public Domain)
The `.sidecar` file format specification is **CC0 (Public Domain)** - implement in ANY software, no fees, no attribution required.

See [docs/PROTOCOL_LICENSE](docs/PROTOCOL_LICENSE) for details.

## 🤝 Contributing

Contributions welcome! See [docs/VERSION_GOALS.md](docs/VERSION_GOALS.md) for priorities.

By contributing, you agree to the dual-license model (AGPL v3 + Commercial).

---

**Built with ❤️ by Michael Todd Edwards**  
*Making every song sound exactly how YOU want it*

