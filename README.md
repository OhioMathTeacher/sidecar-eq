# Sidecar EQ

**Your music. Your sound. Everywhere.**

A revolutionary music player that remembers YOUR perfect sonic settings for every track. No more fiddling with EQ between songs - set it once, never touch it again.

## 🎯 The Problem We're Solving

Every other music player (Spotify, iTunes, VLC) forces ONE EQ setting for ALL songs:
- "Hotel California" needs bass cut? Turn it down.
- Next song is "Billie Jean"? Now bass is too quiet!
- You're constantly adjusting, or you give up and leave it flat.

**Sidecar EQ is different**: Every song remembers YOUR perfect EQ and volume. Automatic. Forever.

## ✨ Key Features

- **🧠 Per-Track Intelligence**: Each song remembers your perfect EQ/volume settings
- **📊 Automatic Analysis**: Background audio analysis (LUFS, peaks, frequency distribution)
- **🎨 Beautiful Dark Theme**: 70s-style blue VU meter aesthetics
- **💾 Auto-Save**: Like Google Docs - no interrupting dialogs
- **🎵 Multi-Source**: Local files, Web URLs, Plex servers
- **🔓 Open Standard**: .sidecar format for universal compatibility (coming in v2.0)

## 🚀 What Makes This Revolutionary

### v1.0.0 (Current Development)
- Real-time 7-band EQ that actually processes audio
- Smart per-track memory (~120 bytes per song)
- Drag & drop queue management
- Multi-select support

### v2.0.0 (Roadmap)
- **Acoustic fingerprinting** - Settings follow songs across different paths/formats
- **Open .sidecar protocol** - Export settings that work in ANY player
- **Smart export** - Render audio with EQ baked in (matching source bitrate)
- Enhanced Plex integration with full library browser

See [VERSION_GOALS.md](VERSION_GOALS.md) for the complete vision.

## 🎨 Interface Highlights

### Thermometer EQ Controls
- **7-Band Frequency Response**: 60Hz to 15kHz professional audio bands
- **Liquid Fill Visualization**: CSS-powered gradient fills show EQ levels intuitively
- **Interactive Handles**: Drag endpoints to adjust frequency response
- **Educational Labels**: Clear frequency markings for learning

### Multi-Source Support
- **Local Files**: Audio and video files with automatic format detection
- **YouTube URLs**: Direct streaming with optional yt-dlp integration
- **Plex Integration**: Seamless media server connectivity

## Optional YouTube Support (yt-dlp)

Sidecar EQ can optionally accept YouTube page URLs in the UI. This uses the external tool `yt-dlp` to resolve direct stream URLs or download audio to a temporary file.

Install the optional dependency:

```bash
pip install -e .[yt]
# or separately:
pip install yt-dlp
```

**Note**: Downloading or programmatic access to third-party content may be subject to that site's Terms of Service. This feature is optional; we recommend users only play content they have rights to use.

## 🏗️ Development Status

**Current Version**: v0.8-alpha (approaching v1.0.0)  
**Status**: Core features working, implementing real EQ audio processing  
**Next**: Complete v1.0.0 must-haves, then v2.0.0 with open protocol

See [VERSION_GOALS.md](VERSION_GOALS.md) for complete roadmap.

## Run (dev)
```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
python -m sidecar_eq.app
```

## Optional YouTube support (yt-dlp)

Sidecar EQ can optionally accept YouTube page URLs in the UI. This uses the external tool `yt-dlp` to resolve direct stream URLs or download audio to a temporary file. This feature is opt-in and requires `yt-dlp` to be installed in the same Python environment.

Install the optional dependency into the venv:

```bash
/Users/todd/sidecar-eq/.venv/bin/python -m pip install -e .[yt]
# or separately:
/Users/todd/sidecar-eq/.venv/bin/python -m pip install yt-dlp
```

Notes:
- Some videos may require signing-in or browser cookies (yt-dlp will print a message like "Sign in to confirm you're not a bot"). In those cases you can provide a cookies file to yt-dlp with `--cookies PATH`.
- Downloading or programmatic access to third-party content may be subject to that site's Terms of Service. This feature is optional; we recommend users only play content they have rights to use.

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

