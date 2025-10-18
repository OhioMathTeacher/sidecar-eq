# Sidecar EQ

**Your music. Your sound. Everywhere.**

A powerful music player with per-track EQ and volume memory. Set your perfect sound once per track - the app remembers forever. No more adjusting EQ between songs.

## 🎯 The Problem We're Solving

Every other music player (Spotify, iTunes, VLC) forces ONE EQ setting for ALL songs:
- "Hotel California" needs bass cut? Turn it down.
- Next song is "Billie Jean"? Now bass is too quiet!
- You're constantly adjusting, or you give up and leave it flat.

**Sidecar EQ is different**: Every song remembers YOUR perfect EQ and volume. Automatic. Forever.

## ✨ Key Features

### Core Playback
- **🧠 Per-Track Memory**: Each song remembers your EQ and volume settings
- **🎛️ Real-Time EQ**: 7-band equalizer (60Hz-15kHz) with actual audio processing
- **🎚️ Individual Volume**: Set perfect loudness for each track
- **📊 LED Meters**: Real-time audio level visualization
- **🎵 Multi-Format**: Supports audio (MP3, FLAC, WAV, M4A) and video files

### Intelligence
- **📈 Auto-Analysis**: Background frequency response, loudness (LUFS), tempo detection
- **🔍 Metadata Search**: Quickly find tracks by artist, album, or title
- **⭐ Star Ratings**: Five-star rating system for organizing favorites
- **🎲 Smart Queue**: Drag-and-drop reordering, multi-select operations

### Multi-Source Playback
- **📁 Local Files**: Direct playback from your music library
- **🎬 Plex Integration**: Browse and play from your Plex media server
  - Auto-discovery on local network
  - Home User support (guest or PIN-protected)
  - No Plex account login required
- **🔗 Web URLs**: Direct streaming support (YouTube with optional yt-dlp)

### Modern UI
- **� Dark Theme**: Professional audio interface aesthetics
- **📐 Layout Presets**: Four workspace views (Full, Queue Only, EQ Only, Search Only)
- **� Auto-Save**: Settings persist automatically - like Google Docs
- **⌨️ Keyboard Shortcuts**: Efficient playback control

## 🚀 What Makes This Revolutionary

### v1.1.1 (Current)
- ✅ Real-time 7-band EQ that actually processes audio
- ✅ Per-track memory (~120 bytes per song)
- ✅ Plex server integration with Home Users
- ✅ Star rating system
- ✅ Smart layout presets
- ✅ Background audio analysis

### v2.0.0 (Roadmap)
- **Acoustic fingerprinting** - Settings follow songs across different paths/formats
- **Open .sidecar protocol** - Export settings that work in ANY player
- **Smart export** - Render audio with EQ baked in (matching source bitrate)
- **Cloud sync** - Access your settings anywhere

See [VERSION_GOALS.md](VERSION_GOALS.md) for the complete vision.

## 🎨 Interface Highlights

### 7-Band Equalizer
- **Professional Audio Bands**: 60Hz, 230Hz, 910Hz, 3.6kHz, 14kHz, 15kHz controls
- **Thermometer Visualization**: Intuitive liquid-fill sliders
- **Real-Time Processing**: Hear changes instantly
- **Per-Track Storage**: Every song remembers your settings

### Layout Presets
- **Full View**: All panels visible for complete control
- **Queue Only**: Focus on track management
- **EQ Only**: Detailed frequency adjustment
- **Search Only**: Quick library browsing

### Plex Integration (New in 1.1.0)
- **Auto-Discovery**: Finds servers automatically on your network
- **Home Users**: Support for managed Plex accounts
- **Guest Access**: No authentication for public libraries
- **PIN Protection**: Optional 4-digit PINs for admin users

## 🔧 Installation

### Download Pre-Built App (macOS)
1. Download `SidecarEQ.app` from releases
2. Drag to Applications folder
3. Right-click → Open (first time only)

### Build from Source
```bash
# Clone repository
git clone https://github.com/OhioMathTeacher/sidecar-eq.git
cd sidecar-eq

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Run application
python -m sidecar_eq.app
```

### Optional: YouTube Support (yt-dlp)

For YouTube URL streaming, install the optional dependency:

```bash
pip install -e .[yt]
# or separately:
pip install yt-dlp
```

**Note**: Downloading or accessing third-party content may be subject to their Terms of Service. Use responsibly.

## 🎬 Plex Setup

### Quick Start
1. Open **Settings** → **Manage Plex Servers**
2. Click **Scan Network** to auto-discover servers
3. Select your server and configure Home Users
4. Enable users you want to access (e.g., "MusicMan", "Billy_Nimbus")
5. Optionally enter 4-digit PINs for protected users

Your server will appear in the source dropdown alongside local folders. See [PLEX_HOME_USER_SETUP.md](PLEX_HOME_USER_SETUP.md) for detailed configuration.

### Privacy
All Plex settings are stored locally in `~/.sidecar-eq/config.json`. No credentials are stored in the code - completely portable and private.

## 📦 Building macOS App

```bash
# Install build tools
pip install py2app setuptools

# Build application
python setup.py py2app --no-strip

# Output: dist/SidecarEQ.app
```

See [BUILD_NOTES.md](BUILD_NOTES.md) for detailed build instructions and troubleshooting.

## 🏗️ Development Status

**Current Version**: v1.1.1  
**Status**: Stable - Plex integration complete, UI polished  
**Next**: Multi-source infrastructure, acoustic fingerprinting (v2.0.0)

See [VERSION_GOALS.md](VERSION_GOALS.md) for complete roadmap.

## 📚 Documentation

- [VERSION_GOALS.md](VERSION_GOALS.md) - Product roadmap and vision
- [PLEX_HOME_USER_SETUP.md](PLEX_HOME_USER_SETUP.md) - Plex server configuration guide
- [BUILD_NOTES.md](BUILD_NOTES.md) - Building and distributing the app
- [WELCOME_AUDIO_SPEC.md](WELCOME_AUDIO_SPEC.md) - Welcome audio specification

## 📜 License

Sidecar EQ is dual-licensed:

### AGPL v3 (Free & Open Source)
The application is licensed under **GNU Affero General Public License v3.0**.

✅ Use it FREE  
✅ Modify it freely  
✅ Share improvements  
❗ Must share source if you distribute or deploy as a service  

### Commercial License (Proprietary Use)
Need to use Sidecar EQ in a closed-source product or service without AGPL requirements?

Commercial licenses available for:
- Closed-source applications
- SaaS deployments without source sharing
- Priority support and consulting

Contact: Michael Todd Edwards (contact details TBD)

### .sidecar Protocol (Public Domain)
The `.sidecar` file format specification (v2.0.0+) will be **CC0 (Public Domain)** to encourage universal adoption.

✅ Implement in ANY software (commercial or open source)  
✅ No attribution required  
✅ No licensing fees ever  

## 🤝 Contributing

Contributions welcome! See [VERSION_GOALS.md](VERSION_GOALS.md) for current priorities.

Key areas:
- Acoustic fingerprinting implementation
- Additional audio format support
- UI/UX improvements
- Documentation and testing

By contributing, you agree that your contributions will be licensed under the same dual-license model (AGPL v3 + Commercial).

## 🐛 Known Issues

- scipy build warning (non-fatal): Code signing optimization error during py2app build
- First launch may take a few seconds to initialize

## 💡 Tips

- **Keyboard Shortcuts**: Space = Play/Pause, Delete = Remove track
- **Multi-Select**: Cmd+Click or Shift+Click for bulk operations
- **Column Reorder**: Drag column headers to rearrange
- **Hide Columns**: Right-click headers to toggle visibility
- **Layout Quick Switch**: Use layout dropdown for instant workspace changes

---

**Built with ❤️ by Michael Todd Edwards**  
*Making every song sound exactly how YOU want it*

## 📜 License

Sidecar EQ is dual-licensed:

### AGPL v3 (Free & Open Source)
The application is licensed under **GNU Affero General Public License v3.0**.

✅ Use it FREE  
✅ Modify it freely  
✅ Share improvements  
❗ Must share source if you distribute or deploy as a service  

### Commercial License (Proprietary Use)
Need to use Sidecar EQ in a closed-source product or service without AGPL requirements?

Commercial licenses are available for:
- Closed-source applications
- SaaS deployments without source sharing
- Priority support and consulting

Contact: Michael Todd Edwards [contact info TBD]

### .sidecar Protocol (Public Domain)
The `.sidecar` file format specification is **CC0 (Public Domain)** to encourage universal adoption.

✅ Implement in ANY software (commercial or open source)  
✅ No attribution required  
✅ No licensing fees ever  

See [PROTOCOL_LICENSE](PROTOCOL_LICENSE) for details.

## 🤝 Contributing

Contributions welcome! See [VERSION_GOALS.md](VERSION_GOALS.md) for current priorities.

By contributing, you agree that your contributions will be licensed under the same dual-license model (AGPL v3 + Commercial).

