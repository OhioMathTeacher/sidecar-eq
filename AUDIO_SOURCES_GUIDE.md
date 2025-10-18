# Audio Sources Plugin System

## Overview

SidecarEQ uses a **modular, plugin-based architecture** for handling audio from multiple sources. This allows you to play music from:

- 📁 **Local files** (MP3, FLAC, WAV, etc.)
- 🌐 **Plex Media Server**
- ☁️ **Cloud storage** (S3, Google Cloud, etc.)
- 🔗 **HTTP streams**
- 🎵 **Future sources** (Spotify, YouTube Music, IPFS, etc.)

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Player (app.py)                    │
│  - Doesn't care about source type               │
│  - Just plays URLs                              │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│         AudioRepository (Manager)               │
│  - Picks best available source                  │
│  - Returns playback URL                         │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│          AudioSource (Plugin Interface)         │
│  - LocalFileSource                              │
│  - PlexSource                                   │
│  - S3Source                                     │
│  - StreamSource                                 │
│  - [Your custom source...]                      │
└─────────────────────────────────────────────────┘
```

## Core Concepts

### 1. Track ID System

Every track gets a **unique ID** based on its metadata (title + artist + album), not its location:

```python
from sidecar_eq.audio_sources import generate_track_id

track_id = generate_track_id("Money", "Pink Floyd", "Dark Side of the Moon")
# Result: "a1b2c3d4e5f6g7h8" (stable, won't change if file moves)
```

**Why this matters:**
- Settings (EQ, ratings) follow the song, not the file
- Works even if you move/rename files
- Same song from different sources = same track ID

### 2. Multi-Source Tracks

A track can have **multiple sources**:

```python
from sidecar_eq.audio_sources import Track, AudioSourceInfo

track = Track.from_metadata(
    title="Money",
    artist="Pink Floyd",
    album="Dark Side of the Moon",
    sources=[
        # Local FLAC file (highest quality)
        AudioSourceInfo(
            source_type="local",
            location="/Music/Pink Floyd/Money.flac",
            quality={"bitrate": 1411, "format": "flac"}
        ),
        # Plex backup
        AudioSourceInfo(
            source_type="plex",
            location="http://plex:32400/...?X-Plex-Token=xyz",
            quality={"bitrate": 320, "format": "mp3"}
        ),
        # Cloud backup
        AudioSourceInfo(
            source_type="s3",
            location="s3://my-music/pink-floyd/money.mp3",
            quality={"bitrate": 320, "format": "mp3"}
        ),
    ]
)
```

**Benefits:**
- Automatic fallback if local file is missing
- Play from fastest available source
- Seamless transition between home and remote

### 3. Source Priority

The system automatically picks the **best available source**:

```
Priority Order:
1. local     - Fastest, no network needed
2. plex      - Local network, fast streaming
3. s3        - Cloud storage, requires internet
4. stream    - HTTP streams
5. youtube   - Streaming services
6. spotify   - Requires authentication
```

You can override this by implementing custom logic in `Track.get_best_source()`.

## Usage Examples

### Basic: Play a Local File

```python
from sidecar_eq.audio_sources import create_track_from_path, AudioRepository

# Create track from local file
track = create_track_from_path(
    file_path="/Music/song.mp3",
    title="Song Title",
    artist="Artist Name",
    album="Album Name"
)

# Get playback URL
repo = AudioRepository()
url = repo.get_playback_url(track)

# Play with Qt Multimedia
player.setSource(QUrl(url))
player.play()
```

### Advanced: Multi-Source Track

```python
from sidecar_eq.audio_sources import Track, AudioSourceInfo, AudioRepository

# Create track with multiple sources
track = Track.from_metadata(
    title="Bohemian Rhapsody",
    artist="Queen",
    album="A Night at the Opera",
    sources=[
        # Local file (try this first)
        AudioSourceInfo(
            source_type="local",
            location="/Music/Queen/Bohemian Rhapsody.flac",
            quality={"bitrate": 1411, "format": "flac", "sample_rate": 44100}
        ),
        # Plex fallback
        AudioSourceInfo(
            source_type="plex",
            location="http://192.168.1.100:32400/library/metadata/12345",
            quality={"bitrate": 320, "format": "mp3"}
        ),
    ],
    year=1975,
    genre="Rock"
)

# Repository automatically picks best source
repo = AudioRepository()
url = repo.get_playback_url(track)  # Will use local if available, Plex if not

# Check which sources are available
availability = repo.check_availability(track)
# Result: {"local": True, "plex": True}
```

### Custom: Add Your Own Source Plugin

```python
from sidecar_eq.audio_sources import AudioSource, AudioSourceInfo

class DropboxSource(AudioSource):
    """Plugin for Dropbox-hosted audio files."""
    
    def can_handle(self, source_info: AudioSourceInfo) -> bool:
        return source_info.source_type == "dropbox"
    
    def get_playback_url(self, source_info: AudioSourceInfo) -> str:
        """Convert Dropbox path to direct download link."""
        # Example: Convert share link to direct download
        link = source_info.location
        if "www.dropbox.com" in link:
            # Change dl=0 to dl=1 for direct download
            return link.replace("dl=0", "dl=1")
        return link
    
    def is_available(self, source_info: AudioSourceInfo) -> bool:
        """Check if we have internet connection."""
        # Could ping dropbox.com
        return True

# Register your plugin
repo = AudioRepository()
repo.register_source(DropboxSource())

# Now you can use Dropbox sources!
track = Track.from_metadata(
    title="Song",
    artist="Artist",
    album="Album",
    sources=[
        AudioSourceInfo(
            source_type="dropbox",
            location="https://www.dropbox.com/s/xyz/song.mp3?dl=0",
            quality={"bitrate": 320, "format": "mp3"}
        )
    ]
)
```

## Integration with Existing Code

### Backward Compatibility

Old code using file paths still works:

```python
# Old way (still works)
file_path = "/Music/song.mp3"
player.play(file_path)

# New way (same result, more flexible)
track = create_track_from_path(file_path)
url = repo.get_playback_url(track)
player.play(url)
```

### Migration Strategy

1. **Phase 1**: Continue using paths, add `audio_sources.py` (✅ Done)
2. **Phase 2**: Update `queue_model.py` to use Track objects
3. **Phase 3**: Update `library.py` Song class to use Track
4. **Phase 4**: Update `store.py` to use track IDs instead of paths
5. **Phase 5**: Remove path-based code

### Queue Model Integration

```python
# queue_model.py (future)
from sidecar_eq.audio_sources import Track, create_track_from_path

class QueueModel:
    def add_paths(self, paths):
        for path in paths:
            # Create Track object instead of dict
            track = create_track_from_path(path)
            self._rows.append({
                "track": track,  # Store Track object
                "track_id": track.track_id,
                "title": track.title,
                # ... other fields
            })
```

## Source Plugins

### Built-in Plugins

#### LocalFileSource
- **Type**: `"local"`
- **Location**: File system path
- **URL Format**: `file:///path/to/file.mp3`
- **Availability**: Checks if file exists

#### PlexSource
- **Type**: `"plex"`
- **Location**: Plex stream URL with auth token
- **URL Format**: `http://server:32400/...?X-Plex-Token=xyz`
- **Availability**: Assumes available (could ping server)

#### StreamSource
- **Type**: `"stream"`
- **Location**: HTTP/HTTPS URL
- **URL Format**: Direct URL
- **Availability**: Always true (could add HEAD request)

#### S3Source
- **Type**: `"s3"`
- **Location**: `s3://bucket/key/path.mp3`
- **URL Format**: Presigned URL (1 hour expiry)
- **Availability**: Always true (could add HEAD request)

### Future Plugins

Ideas for additional sources:

```python
# YouTube Music
class YouTubeMusicSource(AudioSource):
    # Download audio stream via yt-dlp
    pass

# Spotify
class SpotifySource(AudioSource):
    # Use Spotify Web API + player
    pass

# IPFS
class IPFSSource(AudioSource):
    # Decentralized file storage
    pass

# Google Drive
class GoogleDriveSource(AudioSource):
    # Play from Drive
    pass

# SMB/NFS Network Share
class NetworkShareSource(AudioSource):
    # Mount and play from network drives
    pass
```

## Benefits

### For Users
- ✅ Music library works anywhere (home, office, mobile)
- ✅ Automatic fallback if files move
- ✅ Play from fastest available source
- ✅ Settings follow songs, not files

### For Developers
- ✅ Add new sources without changing core code
- ✅ Easy to test (mock sources)
- ✅ Clean separation of concerns
- ✅ Future-proof architecture

## Next Steps

1. **Test**: Run the example at bottom of `audio_sources.py`
2. **Integrate**: Update `queue_model.py` to use Track objects
3. **Migrate**: Update `library.py` Song class
4. **Enhance**: Add source icons to UI
5. **Extend**: Add new source plugins as needed

## File Locations

- **Plugin System**: `sidecar_eq/audio_sources.py`
- **This Guide**: `AUDIO_SOURCES_GUIDE.md`
- **Queue Model**: `sidecar_eq/queue_model.py` (to be updated)
- **Library**: `sidecar_eq/library.py` (to be updated)
- **Store**: `sidecar_eq/store.py` (to be updated)

---

**Ready to build the future of music playback!** 🎵
