# Sidecar EQ - Product Vision & Requirements

**Last Updated**: October 14, 2025  
**Status**: Active Development - UI Refinement Phase

---

## 🎯 Core Mission

**Sidecar EQ is an intelligent music player that learns and remembers the perfect audio settings for every song you play.**

Unlike traditional music players that force you to manually adjust EQ and volume for each track, Sidecar EQ:
1. **Analyzes** each song's acoustic signature on first play
2. **Suggests** optimal EQ and volume settings automatically
3. **Remembers** your customizations forever (per-track persistence)
4. **Adapts** as you refine settings across listening sessions

---

## 🎵 Primary Use Case: The Perfect Playback Experience

### First-Time Playback Flow
1. User adds a song to the queue (local file, Plex server, or URL)
2. **Automatic Analysis**: Background sonic analysis determines:
   - Optimal volume level (LUFS-based loudness normalization)
   - Suggested EQ curve (based on frequency content analysis)
   - Bass/treble characteristics, peak frequencies
3. **Smart Application**: Song begins playing with suggested settings
   - EQ sliders automatically position to suggested values
   - Volume spinner sets to calculated optimal level
4. **User Refinement**: As song plays, user can:
   - Adjust any EQ band in real-time
   - Change volume via spinner or keyboard shortcuts
   - Hear changes immediately (real-time audio processing)
5. **Persistence**: Settings saved automatically when:
   - User clicks the circular save button (explicit save)
   - User moves to next track (implicit save if changed)
   - App closes with unsaved changes (save prompt dialog)

### Subsequent Playback
- Song loads with **previously saved settings** (user's or defaults)
- No re-analysis needed unless user requests it
- Instant playback with perfect remembered settings

---

## 🔧 Critical Features (Must-Have)

### 1. Per-Track Audio Settings Persistence
**Current Status**: ✅ Implemented (JSON storage)  
**Requirements**:
- Every audio file gets a unique settings profile
- Settings include: 7-band EQ values, volume level, analysis data
- Works for: local files, Plex streams, URLs
- Storage: `~/.sidecar_eq_eqs.json` (human-readable)
- Never loses settings across app restarts

### 2. Real-Time EQ Audio Processing
**Current Status**: ⚠️ **BROKEN** - Placeholder only, no actual audio filtering  
**Requirements**:
- **7-band parametric EQ**: 60Hz, 150Hz, 400Hz, 1kHz, 2.4kHz, 6kHz, 15kHz
- Real-time DSP filtering (hear changes instantly as sliders move)
- No audio glitches or dropouts during adjustment
- Visual feedback matches audible changes
- **Implementation Options**:
  - PyAudio + numpy/scipy for DSP
  - FFmpeg audio filters (complex but powerful)
  - Qt Audio with custom filters
  - Third-party audio engine (OpenAL, FMOD)

**PRIORITY**: This is the #1 feature to fix - EQ must actually work!

### 3. Automatic Sonic Analysis
**Current Status**: ✅ Implemented (librosa-based)  
**Capabilities**:
- Loudness measurement (LUFS)
- Peak level detection
- Frequency distribution (bass/treble ratio)
- Suggested volume calculation
- Background processing (non-blocking)

**Enhancement Needed**: More accurate EQ suggestions based on:
- Genre detection
- Vocal presence/clarity
- Instrument separation
- Dynamic range characteristics

### 4. Unsaved Changes Protection
**Current Status**: ❓ Unknown - needs verification  
**Requirements**:
- Track which songs have modified-but-unsaved settings
- On app close: Show dialog listing unsaved tracks
- Dialog options:
  - "Save All" - persist all changes
  - "Discard All" - revert to last saved
  - "Review" - go through each track individually
  - "Cancel" - return to app without closing
- Visual indicator (asterisk?) on queue items with unsaved changes

---

## 🎚️ Interface Requirements

### Volume Control
**Current Status**: ✅ **FIXED** - QSpinBox with up/down arrows  
**Features**:
- Direct numeric input (0-100%)
- Up/down arrow buttons for fine control
- Keyboard shortcuts: +/- or Volume keys
- Real-time updates (no lag)
- Synced with per-track settings

### Source Selector
**Current Status**: ✅ **FIXED** - QComboBox dropdown  
**Features**:
- Three modes: "Local Files", "Website URL", "Plex Server"
- Clear visual indication of current mode
- Changes behavior of "Add" buttons appropriately

### EQ Visualization
**Current Status**: ✅ Beautiful blue VU meters (70s receiver aesthetic)  
**Features**:
- 7 vertical sliders with blue gradient fill
- Labeled with frequency bands
- Smooth drag interaction
- Visual confirmation of changes

### Opacity Control (View Menu)
**Current Status**: ✅ **FIXED** - Menu connects to EQ panel  
**Features**:
- View menu with opacity options: 30%, 60%, 90%
- Applies transparency to EQ panel
- Allows seeing queue behind EQ controls

---

## 📂 Queue Management (Critical Improvements Needed)

### Drag & Drop Reordering
**Current Status**: ❌ **NOT IMPLEMENTED**  
**Requirements**:
- Click and drag songs up/down in queue to reorder
- Visual feedback during drag (highlight insertion point)
- Works with keyboard (Alt+Up/Down?)
- Updates immediately, persists to saved queue

### Multi-Selection Operations
**Current Status**: ⚠️ Partial (single-select delete works)  
**Requirements**:
- **Command+Click** (macOS) / **Ctrl+Click** (Win/Linux): Toggle selection
- **Shift+Click**: Range selection
- Operations on selection:
  - **Delete key**: Remove all selected from queue
  - **Drag**: Move all selected together
  - **Context menu**: Batch operations (analyze, reset EQ, etc.)
- Visual: Highlight all selected rows clearly

### Direct File Drag-In
**Current Status**: ❌ **NOT IMPLEMENTED**  
**Requirements**:
- Drag audio files from Finder/Explorer directly into queue table
- Supports: Individual files, folders, playlists
- Insertion point: Drop position in queue (not just at end)
- Auto-analyze new additions (background)

### Delete Key Handling
**Current Status**: ✅ Works for single selection  
**Needs**: Multi-selection support (see above)

---

## 🎼 Playlist Features

### Save/Load Playlists
**Current Status**: ✅ Basic implementation exists  
**Current Format**: JSON (`.sidecar` extension)  
**Requirements**: **Human-readable text format**

**Proposed Format** (M3U8 Extended with Sidecar metadata):
```m3u8
#EXTM3U
#SIDECAR-VERSION:1.0

#EXTINF:323,Black Sabbath - Paranoid
#SIDECAR-EQ:[-2, 0, 3, 1, 0, -1, 2]
#SIDECAR-VOL:75
/path/to/Black Sabbath/Paranoid.mp3

#EXTINF:195,The Beatles - Come Together
#SIDECAR-EQ:[0, 0, 0, 0, 0, 0, 0]
#SIDECAR-VOL:68
#SIDECAR-SOURCE:plex
https://plex.example.com/library/tracks/12345

#EXTINF:240,Nirvana - Smells Like Teen Spirit
#SIDECAR-EQ:[4, 2, 0, -1, 1, 3, 0]
#SIDECAR-VOL:82
#SIDECAR-SOURCE:youtube
https://www.youtube.com/watch?v=hTWKbfoikeg
```

**Benefits**:
- Edit in any text editor
- Compatible with standard M3U8 players (ignores Sidecar lines)
- Version-controlled in git
- Share playlists with friends (they can edit paths)
- Metadata preserved but optional

### Upload/Share Playlists
**Future Feature**:
- Export to cloud storage (Dropbox, Google Drive)
- Generate shareable links
- Import from shared URLs
- Community playlist repository?

---

## 🖥️ Plex Integration (Needs Major Improvement)

### Current Issues
**Current Status**: ⚠️ Unclear if working properly  
**Problems**:
- Not obvious if Plex server is detected
- No visual indication of available servers
- Difficult to browse Plex library
- Can't tell if connected or disconnected

### Required Improvements

#### 1. Server Discovery & Management
**UI Requirements**:
- **Plex Servers Panel**: Dedicated view/dialog showing:
  - All Plex servers on local network (mDNS/Bonjour discovery)
  - Server name, IP address, connection status
  - Library counts (music, movies, etc.)
  - "Connect" / "Disconnect" buttons per server
- **Status Indicator**: Toolbar icon showing:
  - Green dot: Connected to Plex
  - Red dot: No Plex connection
  - Yellow dot: Connecting/searching
- **Server Switcher**: Dropdown to select active Plex server

#### 2. Library Browsing
**Features**:
- Browse Plex music library by:
  - Artists → Albums → Tracks
  - Playlists
  - Recently Added
  - Most Played
- Search within Plex libraries
- Thumbnail/artwork display
- Drag tracks from Plex browser to queue

#### 3. Authentication
- Save Plex credentials securely (keychain/keyring)
- Support Plex.tv authentication
- Handle Plex Pass vs. free accounts
- Manage multiple server profiles

---

## 🌐 Network Audio Device Discovery (Future Feature)

### Vision
- Discover **all audio devices** on local network:
  - Plex servers
  - DLNA/UPnP media servers
  - AirPlay devices
  - Chromecast Audio
  - Bluetooth speakers
  - Sonos systems
- Unified "Network" panel showing available endpoints
- Stream Sidecar EQ output to network devices
- Apply EQ processing before sending to network player

### Use Cases
- **Whole-home audio**: Play through Sonos with custom EQ
- **Party mode**: Stream to multiple devices simultaneously
- **Remote listening**: Access Plex server from laptop, apply EQ, send to TV
- **Teaching**: Stream teacher's EQ adjustments to student headphones

---

## 🐛 Known Issues (Priority Fixes)

### 1. ⚠️ EQ Doesn't Affect Audio Output
**Severity**: CRITICAL  
**Impact**: Core feature completely non-functional  
**Cause**: `Player.set_eq_values()` is a placeholder, no actual DSP  
**Fix Required**: Implement real audio filtering (see "Real-Time EQ" section)

### 2. ⚠️ Time Slider Shows 0:00 / Doesn't Seek
**Severity**: HIGH  
**Impact**: Can't see current position or skip ahead in songs  
**Symptoms**:
- Position always shows "00:00 / 00:00"
- Dragging slider doesn't change playback position
**Possible Causes**:
- Player signals not emitting properly
- Signal connections not wired
- Player position updates not triggering UI updates
**Investigation Needed**: Add debug logging to position/duration callbacks

### 3. ✅ Opacity Menu Didn't Work
**Status**: **FIXED** - Now references `_eq_bg_widget` (eq_panel)

### 4. ✅ JSON Serialization Error (numpy types)
**Status**: **FIXED** - Added `convert_to_native()` helper function

### 5. ✅ Deprecated Qt Warnings
**Status**: **FIXED** - Removed AA_EnableHighDpiScaling and AA_UseHighDpiPixmaps

---

## 🎨 Design Philosophy

### Visual Language
- **Modern Dark Theme**: Professional, easy on eyes during long sessions
- **70s Receiver Aesthetic**: Blue VU meters evoke classic hi-fi equipment
- **Functional First**: Beauty serves usability, not decoration
- **Consistent Spacing**: Balanced layout, clear visual hierarchy

### Interaction Principles
1. **Immediate Feedback**: Every action has instant visual/audio response
2. **Undo-Friendly**: Easy to experiment without fear of losing good settings
3. **Progressive Disclosure**: Simple by default, powerful when needed
4. **Keyboard-First**: All actions accessible without mouse
5. **Respectful Persistence**: Never lose user's work or preferences

### Error Handling
- **Graceful Degradation**: Missing Plex? App still works with local files
- **Clear Messaging**: No cryptic errors, explain what went wrong and how to fix
- **Recovery Options**: Always offer a path forward
- **Silent Fallbacks**: If analysis fails, use sensible defaults without alarming user

---

## 📋 Implementation Checklist

### Phase 1: Critical Fixes (This Sprint)
- [ ] **Fix EQ audio processing** - Implement real DSP filtering
- [ ] **Fix time slider** - Debug position/duration updates
- [ ] **Test opacity menu** - Verify fixed implementation works
- [ ] **Add unsaved changes dialog** - Protect user's work

### Phase 2: Queue Improvements
- [ ] **Drag & drop reordering** - Implement QAbstractItemModel drag/drop
- [ ] **Multi-selection** - Enable Command/Ctrl+Click selection
- [ ] **Batch delete** - Delete multiple selected tracks
- [ ] **Direct file drag-in** - Accept external file drops
- [ ] **Visual selection feedback** - Highlight selected rows clearly

### Phase 3: Playlist Enhancements
- [ ] **Design M3U8 extended format** - Define Sidecar metadata spec
- [ ] **Implement M3U8 export** - Save playlists in new format
- [ ] **Implement M3U8 import** - Load playlists, parse Sidecar metadata
- [ ] **Test with external editors** - Verify human editability
- [ ] **Migration tool** - Convert old JSON playlists to M3U8

### Phase 4: Plex Overhaul
- [ ] **Server discovery UI** - Design and implement server browser
- [ ] **Connection status indicator** - Toolbar status widget
- [ ] **Library browser** - Artist/Album/Track navigation
- [ ] **Authentication flow** - Secure credential storage
- [ ] **Multi-server support** - Switch between Plex servers

### Phase 5: Network Discovery (Future)
- [ ] **Research protocols** - mDNS, DLNA, UPnP, AirPlay APIs
- [ ] **Device discovery** - Scan for network audio devices
- [ ] **Unified network panel** - Show all available endpoints
- [ ] **Streaming implementation** - Send audio to network devices
- [ ] **EQ before streaming** - Apply processing before network send

---

## 🧪 Testing Requirements

### Manual Testing Checklist
- [ ] First-time song playback: Analysis runs, settings apply
- [ ] Modified settings: User changes apply in real-time
- [ ] Save button: Explicitly saves current track settings
- [ ] Track switching: Unsaved changes prompt on next track
- [ ] App close: Unsaved changes dialog appears
- [ ] Drag reorder: Songs move in queue correctly
- [ ] Multi-select delete: Multiple songs removed at once
- [ ] File drag-in: External files added to queue
- [ ] Plex server: Server appears, library browseable
- [ ] M3U8 playlist: Save/load preserves all metadata

### Automated Testing (Future)
- Unit tests for DSP functions
- Integration tests for persistence
- UI automation tests for critical flows
- Performance benchmarks for audio processing
- Cross-platform compatibility tests

---

## 📝 Documentation Needs

### User Documentation
- [ ] **Quick Start Guide**: 5-minute "First Song" walkthrough
- [ ] **EQ Basics**: Explanation of each frequency band
- [ ] **Plex Setup**: Connecting to Plex servers
- [ ] **Playlist Management**: Creating and editing playlists
- [ ] **Keyboard Shortcuts**: Complete reference
- [ ] **Troubleshooting**: Common issues and solutions

### Developer Documentation
- [ ] **Architecture Overview**: Code structure and data flow
- [ ] **API Reference**: Public classes and methods
- [ ] **Contributing Guide**: How to submit patches
- [ ] **Build Instructions**: Platform-specific setup
- [ ] **Audio Processing**: DSP implementation details
- [ ] **Persistence Format**: JSON schema and M3U8 spec

---

## 🚀 Success Criteria

**Sidecar EQ will be successful when**:

1. **Users trust it**: Settings never lost, always remembered correctly
2. **EQ actually works**: Moving sliders produces audible frequency changes
3. **Plex is seamless**: Connect once, browse forever, just works
4. **Queue is powerful**: Reorder, multi-select, drag-in, all intuitive
5. **Playlists are shareable**: Human-readable format, easy to edit
6. **It's fast**: No lag on EQ changes, instant track switching
7. **It's stable**: Never crashes, handles errors gracefully
8. **Users love it**: Becomes their daily music player of choice

---

*This document represents the aspirational vision for Sidecar EQ. Some features are implemented, others are in development, and some await future releases. All decisions should align with the core mission: **intelligent, personalized audio playback that remembers what you love.***
