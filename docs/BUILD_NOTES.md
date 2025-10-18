# SidecarEQ Build Notes

## Version 1.1.1 - Plex Home User Integration

### Release Date
October 18, 2025

### What's New

#### Plex Integration Redesign
- **Direct Server Connection**: No more Plex account login required
- **Auto-Discovery**: Automatically finds Plex servers on local network
- **Home User Support**: Works with managed Plex users (guest or PIN-protected)
- **Privacy-First**: All settings stored locally in `~/.sidecar-eq/config.json`
- **Portable**: Anyone can download and configure for their own server

#### Key Features
✅ Network auto-discovery using GDM protocol  
✅ Manual server IP entry as fallback  
✅ Home User configuration with optional PINs  
✅ Guest access (no authentication)  
✅ Protected admin access (4-digit PIN)  

### Building macOS App

#### Prerequisites
```bash
pip install py2app setuptools
```

#### Build Command
```bash
python setup.py py2app --no-strip
```

#### Output
- Location: `dist/SidecarEQ.app`
- Size: ~500MB (includes Python runtime + all dependencies)
- Architecture: Native for current platform
- Minimum macOS: 10.14 (Mojave)

#### Known Build Issues
- **scipy optimization error**: Non-fatal, app works fine
  ```
  error: [Errno 1] Operation not permitted: '.../_zpropack.cpython-313-darwin.so'
  ```
  This is a macOS code signing issue during optimization. The app builds successfully despite this error.

### File Structure

```
SidecarEQ.app/
├── Contents/
│   ├── MacOS/
│   │   └── SidecarEQ          # Main executable
│   ├── Resources/
│   │   ├── icons/              # UI icons
│   │   ├── lib/                # Python runtime + packages
│   │   │   └── python3.13/
│   │       ├── sidecar_eq/     # App modules
│   │       ├── PySide6/        # Qt framework
│   │       ├── librosa/        # Audio analysis
│   │       ├── numpy/
│   │       ├── scipy/
│   │       └── plexapi/        # Plex integration
│   └── Info.plist             # App metadata
```

### Configuration Storage

User settings stored in: `~/.sidecar-eq/config.json`

Example config:
```json
{
  "plex_servers": [
    {
      "name": "Downstairs",
      "host": "192.168.68.57",
      "port": "32400",
      "users": [
        {"username": "MusicMan", "pin": "", "enabled": true},
        {"username": "Billy_Nimbus", "pin": "1234", "enabled": true}
      ]
    }
  ]
}
```

### Testing the Build

```bash
# Open the app
open dist/SidecarEQ.app

# Or run from terminal to see logs
dist/SidecarEQ.app/Contents/MacOS/SidecarEQ
```

### Distribution

#### For Personal Use
- Just run `dist/SidecarEQ.app`
- Drag to Applications folder if desired

#### For Others
1. **Zip the app**:
   ```bash
   cd dist
   zip -r SidecarEQ-1.1.1.zip SidecarEQ.app
   ```

2. **Share the zip file**
   - They extract and run
   - First launch: Right-click → Open (to bypass Gatekeeper)
   - macOS may warn about "unidentified developer"

#### Code Signing (Optional)
For wider distribution, you can sign the app:
```bash
codesign --force --deep --sign - dist/SidecarEQ.app
```

Or with Apple Developer ID:
```bash
codesign --force --deep --sign "Developer ID Application: Your Name" dist/SidecarEQ.app
```

### Troubleshooting

#### App Won't Launch
- Check Console.app for crash logs
- Run from terminal to see error messages
- Verify Python 3.13+ dependencies are included

#### "App is Damaged" Error
```bash
xattr -cr dist/SidecarEQ.app
```

#### Missing Icons
- Icons should be in `Contents/Resources/icons/`
- Verify `setup.py` includes all icon files

#### Plex Connection Issues
- Server auto-discovery requires same network
- Manual IP entry works across VLANs
- Check port 32400 is accessible

### Version History

#### 1.1.1 (Oct 18, 2025)
- Redesigned Plex integration with Home Users
- Auto-discovery on local network
- PIN support for protected users
- Local config storage (privacy-first)

#### 1.1.0 (Oct 17, 2025)
- UI improvements (layout presets, fixed panel heights)
- Single "Save EQ and Vol" button
- Collapsible panel arrow status indicators
- LED meters moved to View menu
- Save buttons moved to playback area
- Star rating system

#### 1.0.0
- Initial release
- 7-band thermometer EQ
- Queue management
- Background audio analysis
- Plex playback support (legacy auth)

### Dependencies

Core libraries included in app bundle:
- **PySide6 6.7+**: Qt GUI framework
- **librosa 0.10+**: Audio analysis
- **soundfile 0.12+**: Audio I/O
- **numpy**: Numerical computing
- **scipy**: Scientific computing
- **pyqtgraph**: Plotting
- **python-dotenv 1.0+**: Environment variables
- **plexapi 4.0+**: Plex server integration

### Development

To modify and rebuild:
```bash
# Edit source files in sidecar_eq/
# Update version in pyproject.toml
# Rebuild
rm -rf build dist
python setup.py py2app --no-strip
```

### License

See LICENSE file for details.

### Support

For issues or questions:
- GitHub: https://github.com/OhioMathTeacher/sidecar-eq
- Documentation: See `PLEX_HOME_USER_SETUP.md`
