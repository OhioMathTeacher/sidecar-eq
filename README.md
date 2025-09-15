# Sidecar EQ

An educati## 🎨 Interface Highlights

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

**Current Version**: v0.7-alpha  
**Status**: Educational milestone achieved with thermometer EQ interface  
**Next**: Enhanced audio processing and classroom features  

See [ROADMAP.md](ROADMAP.md) for detailed development plans.er with an innovative **thermometer-style EQ interface**. Designed for music students and educators, it analyzes tracks and provides intuitive visual EQ controls that feel like adjusting liquid levels in test tubes.

## ✨ Key Features

- **🌡️ Thermometer EQ Interface**: Revolutionary visual metaphor with 7-band liquid-fill sliders
- **🎵 Multi-Source Playback**: Local files, YouTube URLs, Plex media servers
- **💾 Smart Persistence**: EQ settings and playlists automatically saved per track
- **📊 Real-time Analysis**: Background audio analysis with instant playback
- **🎓 Educational Focus**: Perfect for teaching frequency response and audio concepts

## v0.7-alpha Milestone

The thermometer EQ interface represents a major breakthrough in educational audio software design. Students can intuitively understand frequency adjustment by "filling" or "draining" frequency bands like colored liquid in laboratory equipment.

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
- Some videos may require signing-in or browser cookies (yt-dlp will print a message like "Sign in to confirm you’re not a bot"). In those cases you can provide a cookies file to yt-dlp with `--cookies PATH`.
- Downloading or programmatic access to third-party content may be subject to that site's Terms of Service. This feature is optional; we recommend users only play content they have rights to use.

