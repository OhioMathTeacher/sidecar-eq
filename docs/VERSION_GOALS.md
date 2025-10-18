# Version Goals: v1.0.0 and v2.0.0

## Version 1.0.0 - Search-First Music Player
**Goal**: Modern search interface + intelligent per-track memory

### The Core Problem We're Solving
**Two fundamental issues with modern music players:**

1. **Traditional players make you browse folders** - Nobody wants to navigate `/Music/Artist/Album/Track.mp3` anymore. People search like YouTube: type "war pigs" and expect instant results.

2. **All players use ONE EQ for ALL songs** - "Hotel California" needs bass cut? Turn it down. Next song is "Billie Jean"? Now bass is too quiet! You're constantly fiddling or you give up and leave it flat.

**Sidecar EQ solves both:**
- 🔍 **Search your music like YouTube** - Type artist, song, or album. Instant results.
- 🎚️ **Every song remembers YOUR perfect sound** - EQ and volume saved per track automatically.

### Must-Have Features

**Core Infrastructure (Completed):**
- [x] **Per-track settings persistence** - Automatic saving of EQ/volume (~120 bytes per track)
- [x] **Dark theme UI** - Clean dark interface with 70s blue VU meter aesthetics
- [x] **Play/Pause toggle** - Single button with spacebar support
- [x] **Drag & drop queue reordering** - Visual queue management
- [x] **Column resizing** - Interactive columns with sorting
- [x] **Metadata reading** - Auto-refresh with mutagen library

**Critical Path (v1.0.0):**
- [ ] **🔍 Search Bar Interface** 🎯 NEW CENTERPIECE (1 week)
  - Prominent search bar at top of window
  - Instant fuzzy search across local/network music library
  - Results show: title, artist, album, play count, "⭐" if EQ saved
  - Click result → add to queue
  - Enter on result → add and play immediately
  - Search by: artist name, song title, album, or lyrics (future)
  
- [ ] **Acoustic Fingerprinting** 🎯 CRITICAL (1-2 weeks)
  - Chromaprint integration for content-based track identification
  - Enables search to find same song across formats/locations
  - Settings survive file moves, renames, format conversions
  - Required for network volumes (SAMBA/NFS) where paths change
  - Powers "smart ranking" (your saved tracks appear first in results)
  
- [ ] **Real EQ audio processing** 🎯 CRITICAL (2-3 weeks)
  - PyAudio + scipy DSP pipeline for 7-band EQ
  - This is THE feature - make it actually work!
  
- [ ] **Library Indexer** (3-5 days)
  - Background thread to index local/network music files
  - Build searchable database: path, fingerprint, metadata, play stats
  - SQLite or simple JSON index for fast search
  - Watch folders for new files (auto-add to index)

**Quick Wins:**
- [ ] **Multi-select support** - Ctrl/Cmd+Click selection in queue (30 min)
- [ ] **Direct file drag-in** - Drag audio files into app window (2-3 hours)
- [ ] **Basic commands** - `HELP`, `PLAYLIST local`, `EQ export` (1-2 days)

### Nice-to-Have Features
- [ ] **Command history** - Up arrow recalls previous searches
- [ ] **Search filters** - `artist:pink floyd`, `genre:metal`, `year:1970`
- [ ] **Smart playlists** - Auto-generate based on play counts, EQ similarity
- [ ] **M3U8 playlist support** - Import/export playlists
- [ ] **Keyboard shortcuts** - Beyond Space/Delete (Ctrl+F for search, etc.)
- [ ] **Recently played list** - Quick access to recent tracks

### Storage Model v1.0.0

**Per-Track Settings** (`~/.sidecar_eq_settings.json`):
```json
{
  "/path/to/song.flac": {
    "fingerprint": "AQADtEkkUwnB4...",
    "eq_settings": [0, 2, 3, 2, 0, -1, -2],
    "suggested_volume": 85,
    "play_count": 42,
    "last_played": "2025-10-14T15:30:00",
    "analysis_data": { "lufs": -14.2, "peak": -0.5 }
  }
}
```

**Search Index** (`~/.sidecar_eq_index.json` or SQLite):
```json
[
  {
    "path": "/Volumes/Music/Pink Floyd/Dark Side/Money.flac",
    "fingerprint": "AQADtEkkUwnB4...",
    "title": "Money",
    "artist": "Pink Floyd",
    "album": "Dark Side of the Moon",
    "has_eq": true,
    "play_count": 47
  }
]
```

**Key Strategies:**
- **Dual-Key Lookup**: File path (fast) + acoustic fingerprint (reliable)
- **Search Index**: Pre-built for instant search results
- **Smart Ranking**: Tracks with saved EQ appear first in search results
- **Automatic Updates**: Index rebuilds when new files detected
- **Size**: ~150 bytes per track settings + ~200 bytes per track index entry

### Supported Sources v1.0.0
- ✅ **Local files** - Full support with fingerprinting
- ✅ **Network volumes** - SAMBA/NFS with fingerprint-based tracking
- ❌ **Plex** - Deferred to v2.0.0
- ❌ **Web URLs** - Deferred to v2.0.0 (no fingerprinting possible)
- ❌ **YouTube** - Deferred to v2.0.0

### Out of Scope for v1.0.0
- ❌ Plex integration (deferred to v2.0.0)
- ❌ Web URL playback (deferred to v2.0.0)
- ❌ YouTube/streaming sites (deferred to v2.0.0)
- ❌ Network device casting (too complex - 6-12+ months)
- ❌ Cloud sync (v2.0.0 - requires fingerprinting foundation)
- ❌ Collaborative playlists (future consideration)

### Success Criteria
1. EQ changes audibly affect audio output
2. Time slider shows position and allows seeking
3. All saved settings persist across app restarts
4. No data loss or corruption
5. App stable for 8+ hour sessions
6. Zero crash rate on supported platforms (macOS/Linux/Windows)

### Timeline Estimate
- **Search Bar UI**: 1 week
  - Search input widget with instant results dropdown
  - Result rendering (title, artist, play count, EQ indicator)
  - Click/Enter handlers to add to queue
- **Library Indexer**: 3-5 days
  - Scan local/network folders for audio files
  - Extract metadata (mutagen)
  - Build searchable index
- **Acoustic Fingerprinting**: 1-2 weeks (CRITICAL PATH)
  - Chromaprint/fpcalc integration
  - Fingerprint on first play OR during indexing
  - Dual-key lookup logic
  - Search by fingerprint for smart results
- **EQ Audio Processing**: 2-3 weeks (CRITICAL PATH)
  - PyAudio + scipy DSP pipeline
  - 7-band parametric EQ
- **Command System**: 1-2 days
  - Parse `COMMAND param param` syntax
  - Implement `HELP`, `PLAYLIST`, `EQ EXPORT`
- **Multi-select**: 30 minutes
- **Polish & Testing**: 1 week
- **Total**: ~6-8 weeks to v1.0.0

---

## Version 2.0.0 - Universal Music Search
**Goal**: Search EVERY music source like YouTube

### The Vision Expands
v1.0.0 proves search-first UI with local/network files. v2.0.0 becomes a **universal music search engine**:
- One search bar finds music EVERYWHERE
- Plex servers, Spotify, YouTube, SoundCloud, Bandcamp
- Results sorted by source (Local → Plex → Streaming)
- Same per-track EQ/volume intelligence across ALL sources
- Export/share your settings (open `.sidecar` protocol)

### Headline Features

#### **Universal Search** 🎯 FLAGSHIP FEATURE
Search one bar, find music EVERYWHERE:

```
🔍 Search: "comfortably numb"

LOCAL (your files) ─────────────────────────
⭐ Comfortably Numb - Pink Floyd           [EQ saved, 47 plays]
🎵 Comfortably Numb (Live) - Pink Floyd    [12 plays]

PLEX (home.server:32400) ───────────────────
🎬 Comfortably Numb - Pink Floyd           [Album: The Wall]

SPOTIFY (requires login) ───────────────────
🟢 Comfortably Numb - Pink Floyd           [Duration: 6:23]
🟢 Comfortably Numb (Live) - Pink Floyd    [Duration: 8:15]

YOUTUBE ─────────────────────────────────────
▶️ Pink Floyd - Comfortably Numb (Pulse)   [Duration: 9:28]
```

**Implementation**: Source plugins architecture (2-3 weeks per source)

#### **Web URL Playback**
- Support for direct YouTube, SoundCloud, Bandcamp URLs
- Automatic audio extraction (youtube-dl/yt-dlp)
- Streaming support for supported sites
- Visual indicator for web sources
- **Implementation**: 1 week
- **Challenge**: Cannot fingerprint streams (use URL as key)

#### **Duplicate Detection & Management**
- Automatic detection of duplicate songs in queue
- Visual indicators for duplicates (icon, highlight)
- Merge settings from duplicate entries (choose best analysis)
- "Find duplicates in library" tool
- **Implementation**: 3-5 days (leverages v1.0.0 fingerprinting)

### Additional Features
- [ ] **Export with EQ applied** - Render audio files with EQ baked in
  - Match source format and bitrate (no fake upconversion)
  - FLAC → FLAC (lossless), 320kbps MP3 → 320kbps MP3 (honest)
  - Progress bar for long renders
  - Batch export capability
  - **Use cases**: Share with friends, upload to phone, burn to CD
  - **Implementation**: 1 week

- [ ] **Open Sidecar Protocol** 🚀 INDUSTRY-CHANGING
  - Export settings as `.sidecar` JSON files alongside audio
  - Open standard that ANY music player can implement
  - Your settings work in VLC, Audacious, Clementine, etc.
  - Settings travel WITH your music library
  - Share sonic tweaks with friends (just send the .sidecar file!)
  - **File structure**:
    ```
    ~/Music/
      Hotel_California.flac
      Hotel_California.flac.sidecar  ← Settings travel with song!
    ```
  - **Implementation**: 4-6 days (JSON export + spec documentation)
  - **Impact**: Could become THE standard for per-track audio settings

- [ ] **Smart playlist generator** - Auto-generate playlists based on:
  - Audio characteristics (high energy, mellow, etc.)
  - Listening history patterns
  - Time of day preferences
  - **Implementation**: 1-2 weeks

- [ ] **Waveform visualization** - Visual waveform display in queue
  - Zoomable waveform
  - Click to jump to position
  - **Implementation**: 4-6 hours

- [ ] **Cloud sync** - Sync settings across devices
  - Requires fingerprinting (v2.0.0 prerequisite)
  - Encrypted backup to cloud storage
  - **Implementation**: 2-3 weeks

### Storage Model v2.0.0
Same as v1.0.0 (already includes fingerprinting), plus:
- Special handling for Plex URLs (use Plex track ID instead of stream URL)
- Web URLs stored with URL as key (no fingerprinting possible for streams)
- Enhanced metadata for Plex tracks (album art URLs, Plex library paths)

### Success Criteria
1. Fingerprinting correctly identifies >95% of duplicate songs
2. Settings persist when files are moved/renamed
3. Duplicate detection works across different formats
4. Zero performance degradation from v1.0.0
5. Smooth upgrade path (no manual data migration)

### Timeline Estimate
- **Plex Integration**: 2-3 weeks (CRITICAL PATH)
- **Web URL Playback**: 1 week
- **Duplicate Detection**: 3-5 days
- **Open Sidecar Protocol**: 4-6 days (simple but revolutionary)
- **Export Audio Feature**: 1 week
- **Testing & Polish**: 1-2 weeks
- **Total**: ~6-9 weeks to v2.0.0 (after v1.0.0 ships)

---

## Decision Log

### Why Fingerprinting is v1.0.0, Not v2.0.0 (REVERSED DECISION)
1. **Network volumes**: SAMBA/NFS mounts have unstable paths (user's primary use case)
2. **File operations**: Settings must survive moves, renames, re-encoding
3. **Foundation for v2.0**: Duplicate detection, cloud sync require fingerprints
4. **Better UX**: Users shouldn't lose settings from path changes
5. **One-time cost**: 1-2 weeks now vs. migration pain later

### Why Network Casting is Out of Scope
1. **Complexity**: Protocol diversity (AirPlay, Chromecast, DLNA) = 6-12+ months
2. **Maintenance burden**: Each protocol requires ongoing compatibility work
3. **Limited audience**: Most users play locally 90%+ of the time
4. **Better alternatives**: Users can route system audio to network devices
5. **Focus**: Core EQ intelligence is unique value prop, not casting

### Why Plex/Web URLs are v2.0.0, Not v1.0.0 (NEW DECISION)
1. **Focus**: Local/network files are 90% of use cases
2. **Complexity**: Plex requires full library browser (2-3 weeks)
3. **Technical challenges**: 
   - Plex stream URLs change per session (need special handling)
   - Web URLs can't be fingerprinted (different storage strategy needed)
4. **Validation**: Prove fingerprinting + local files work before expanding
5. **Ship faster**: v1.0.0 in 5-7 weeks instead of 9-12 weeks

---

## v1.0.0 Release Notes (Target: ~6-8 weeks)
**"Search your music like YouTube, every song remembers YOUR perfect sound"**

- 🔍 **Search-first interface** - Type artist/song/album, instant results
- 🎵 **Intelligent per-track EQ and volume** - Every track remembers your settings
- � **Acoustic fingerprinting** - Settings survive file moves, renames, format changes
- 🎚️ **Real-time 7-band EQ** - Actual audio processing (not placeholder!)
- 📊 **Smart search ranking** - Your saved tracks appear first in results
- 🌙 **Beautiful dark theme** - 70s blue VU meters, clean interface
- � **Command system** - `HELP`, `PLAYLIST local`, `EQ export`
- 🗑️ **Drag & drop queue** - Visual playlist management
- ⌨️ **Multi-select support** - Ctrl/Cmd+Click
- 💾 **Local + network files** - SAMBA/NFS fully supported

## v2.0.0 Release Notes (Target: ~8-12 weeks after v1.0.0)
**"One search bar. Every music source. Your sound everywhere."**

- 🌐 **Universal search** - Find music across ALL sources in one search
- 📚 **Plex integration** - Search your Plex server's music library
- 🟢 **Spotify plugin** - Search and play Spotify (requires auth)
- ▶️ **YouTube plugin** - Search and play YouTube audio
- 🎵 **SoundCloud/Bandcamp** - Direct streaming support
- 🚀 **Open Sidecar Protocol** - Export settings for ANY player
- 🎭 **Smart duplicate detection** - Find same song across sources
- 💾 **Export with EQ baked in** - Share your perfect mix
- ☁️ **Cloud sync** - Settings follow you everywhere
- 🔌 **Plugin architecture** - Community can add new sources

## v2.0.0 Release Notes (Target: ~6-9 weeks after v1.0.0)
- 🚀 **Open Sidecar Protocol** - Export settings that work in ANY player supporting the standard
- � **Full Plex integration** - Browse library, sync play counts
- 🌐 **Web URL playback** - YouTube, SoundCloud, Bandcamp support
- 🎭 Smart duplicate detection across formats
- 💾 Export audio with EQ applied (match source quality, no fake upconversion)
- ☁️ Cloud sync for settings
- 📊 Waveform visualization
- 🎲 Smart playlist generator

### Tagline: "Search your music like YouTube. Every song remembers YOUR perfect sound."

---

**Last Updated**: October 14, 2025
**Next Review**: After v1.0.0 ships
