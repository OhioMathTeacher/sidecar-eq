# Sidecar EQ - Product Roadmap

**Last Updated**: October 19, 2025  
**Current Version**: v1.1.0  
**Status**: Active Development

---

## 🎯 Vision: From Music Player to Audio Workstation

Sidecar EQ is evolving from an intelligent music player into a **hybrid DAW/Music Player** - combining the simplicity of iTunes with the power of professional audio tools.

### The Three-Phase Evolution

1. **v1.x - Intelligent Music Player** ✅ *Current Phase*
   - Per-track EQ and volume memory
   - Smart search and library management
   - Multi-source playback (local, Plex, web)

2. **v2.x - Universal Audio Hub** 🎯 *Next*
   - VST/AU plugin support
   - Audio routing and processing chains
   - Real-time effect stacking
   - Professional DAW-level audio quality

3. **v3.x - Collaborative Audio Platform** 🚀 *Future*
   - Cloud-based settings sharing
   - Collaborative playlists and presets
   - AI-powered audio enhancement
   - Multi-device synchronization

---

## 📋 Version 1.x - Intelligent Music Player

**Core Mission**: Your music. Your sound. Remembered forever.

### v1.1.0 ✅ SHIPPED (October 2025)
**"The Foundation"**

- ✅ Per-track EQ and volume persistence
- ✅ Dynamic Plex menu integration
- ✅ Scrolling metadata display
- ✅ Collapsible panel UI
- ✅ Layout presets (Full, Queue Only, EQ Only, Search Only)
- ✅ Dynamic window height per view
- ✅ Search improvements (Enter to play)
- ✅ Star ratings system
- ✅ Background audio analysis (LUFS, tempo, frequency response)

**Known Issues**:
- ⚠️ EQ sliders are placeholders (no actual audio filtering yet)
- ⚠️ Time slider needs verification
- ⚠️ Panel resize behavior needs polish

### v1.2.0 🔨 IN PROGRESS
**"Make It Actually Work"**

**Critical Fixes**:
- 🎛️ **Real EQ Audio Processing** - HIGHEST PRIORITY
  - Implement actual DSP filtering (PyAudio + scipy or FFmpeg)
  - Real-time parametric EQ on all 7 bands
  - Zero-latency processing
  - **Estimate**: 2-3 weeks
  
- 🕐 **Fix Time Slider**
  - Verify position/duration updates
  - Enable seeking (drag to jump)
  - Display current time correctly
  - **Estimate**: 4-6 hours

**UI Polish**:
- 🎨 Rack Mode Architecture (incremental migration)
  - Fixed-size panel components
  - Hot-swappable rack modules
  - Separate output window for panel content
  - Solve windowing issues permanently
  - **Estimate**: 2-4 weeks (phased rollout)

**Target**: Late November 2025

### v1.3.0 📚 PLANNED
**"Library & Discovery"**

- 🔍 **Enhanced Search**
  - Fuzzy search across all metadata
  - Search by lyrics (future)
  - Recently played list
  - Search history with suggestions

- 📂 **Queue Improvements**
  - Drag & drop reordering
  - Multi-select operations (Cmd/Ctrl+Click)
  - Direct file drag-in from Finder/Explorer
  - Batch operations (analyze, reset EQ, delete)

- 💾 **Playlist Enhancements**
  - M3U8 export with Sidecar metadata
  - Human-editable playlist format
  - Playlist sharing and import

**Target**: December 2025

---

## 🎚️ Version 2.x - Universal Audio Hub

**Core Mission**: Professional audio tools meet music player simplicity.

### v2.0.0 🚀 MAJOR RELEASE
**"The Audio Workstation Begins"**

**Stem Mixing & Remix Sharing** - THE KILLER FEATURE 🎵
- 🎛️ **AI-Powered Stem Separation**
  - Separate any song into 5 stems (vocals, drums, bass, guitar, other)
  - One-time processing (~60s), cached forever
  - Uses Meta's Demucs or Deezer's Spleeter
  - Stored in `~/.sidecar_eq/stems/{song_hash}/`
  
- 🎚️ **Professional Mixer Panel**
  - 5 vertical faders for independent stem volume control
  - Per-stem mute/solo modes
  - Per-stem 7-band EQ (35 total EQ bands!)
  - Real-time mixing while playing
  - **Use Cases**:
    - Karaoke mode (mute vocals)
    - Learn instruments (isolate bass/drums)
    - Fix bad mixes (rebalance poorly mixed songs)
    - Create custom versions

- 📦 **Remix Files - The Innovation!**
  - Save mix as tiny `.sidecar` text file (~2-5 KB)
  - JSON format: human-readable, version-controllable
  - Share remixes WITHOUT sharing audio (no copyright issues!)
  - Import friend's remix → Instant perfect mix
  - **Revolutionary**: Collaborative remixing as a community
  - **Examples**:
    - "Vocals-Forward Mix" - brings vocals to front
    - "Karaoke Version" - vocals muted
    - "Drummer's Cut" - drums isolated and enhanced
  
- 🌐 **Remix Ecosystem** (Future)
  - Community remix browser/marketplace
  - GitHub-like version control for remixes
  - Fork/improve existing remixes
  - Rate and discover popular remixes
  - Educational: Learn mixing by reading remix files
  
- 🔒 **Legal & Copyright Benefits**
  - ✅ No copyright issues - sharing instructions, not audio
  - ✅ Tiny file size - email/text-friendly
  - ✅ Open format - reverse-engineerable
  - ✅ Requires original - users must own the song
  - ✅ Educational - learn professional mixing techniques

**VST/AU Plugin Support** - PROFESSIONAL POWER
- 🔌 **Plugin Host Architecture**
  - Load VST2/VST3 plugins (reverb, delay, compression, etc.)
  - Audio Units (AU) support on macOS
  - Plugin chain per track (EQ → Compressor → Reverb → etc.)
  - Real-time plugin parameter automation
  - Save plugin chains as presets
  - **Use Cases**:
    - Add studio reverb to live recordings
    - Professional mastering chains
    - Creative effects (chorus, flanger, distortion)
    - Vocal processing (de-esser, auto-tune)

- 🎛️ **Audio Routing Matrix**
  - Visual routing board (like Ableton/Logic)
  - Multiple effect buses
  - Send/return loops
  - Parallel processing chains
  - Master bus processing

- 📦 **Preset Management**
  - Save/load effect chains as `.sidecar-chain` files
  - Community preset sharing
  - Genre-specific starter packs
  - A/B comparison mode

**Universal Search**
- 🌐 **Multi-Source Integration**
  - Unified search across local + Plex + Spotify + YouTube
  - Results sorted by source availability
  - One search bar, all your music

- 🎭 **Smart Duplicate Detection**
  - Acoustic fingerprinting (Chromaprint)
  - Find same song across sources/formats
  - Merge play counts and settings

**Advanced Features**
- 🎨 **Spectrum Analyzer**
  - Real-time frequency visualization
  - Pre/post EQ comparison
  - Helps visualize what each band does

- 📊 **Audio Forensics**
  - Detailed waveform view
  - Click to jump to position
  - Visual problem detection (clipping, noise)

- 🚀 **Export with Processing**
  - Render tracks with EQ + plugins applied
  - Match source quality (no fake upsampling)
  - Batch export capability

**Estimate**: 3-6 months after v1.3.0  
**Target**: Q2 2026

### v2.1.0 📡 PLANNED
**"The Open Platform"**

- 🔓 **Open Sidecar Protocol** (Industry-Changing)
  - Export settings as `.sidecar` files alongside audio
  - Open spec for ANY player to implement
  - Settings travel WITH your music library
  - Share sonic tweaks with friends
  - **Vision**: Become THE standard for per-track settings

- ☁️ **Cloud Sync**
  - Sync settings across devices
  - Encrypted backup to cloud storage
  - Automatic conflict resolution
  - Requires acoustic fingerprinting

- 🤝 **Community Features**
  - Share presets and plugin chains
  - Curated genre packs
  - Upvote/download community settings
  - "EQ like a pro" tutorials

**Target**: Q3 2026

---

## 🎼 Version 3.x - Collaborative Audio Platform

**Core Mission**: Your perfect sound, everywhere, with everyone.

### v3.0.0 🌟 VISION
**"The Future of Music Playback"**

**AI-Powered Audio**
- 🤖 **Intelligent Audio Enhancement**
  - AI suggests optimal EQ based on genre/mood
  - Auto-mastering for home recordings
  - Stem separation (isolate vocals, drums, bass)
  - Neural audio upscaling

- 🎯 **Smart Recommendations**
  - "More like this" based on audio characteristics
  - Mood-based playlist generation
  - Discover music with similar sonic signatures

**Advanced DAW Features**
- 🎹 **MIDI Support**
  - Control plugins with MIDI controllers
  - Save automation curves
  - Hardware integration (mixing consoles, control surfaces)

- 🎚️ **Mix Console Mode**
  - Multi-track mixing interface
  - Professional metering (LUFS, true peak, phase)
  - Side-chain routing
  - Advanced dynamics processing

**Collaborative Platform**
- 👥 **Shared Sessions**
  - Collaborative listening parties
  - Sync playback across devices
  - Live DJ mode with crossfading

- 🌐 **Remote Audio**
  - Stream your library to friends
  - Cloud-based audio processing
  - Network device discovery (Sonos, Chromecast, AirPlay)

**Target**: 2027+

---

## 🏗️ Architecture Evolution

### Current (v1.x)
```
Player → QMediaPlayer → Audio Output
         ↓
    (No real EQ yet)
```

### v2.x with VST
```
Audio Input
    ↓
Internal EQ (7-band)
    ↓
VST Plugin Chain
    ↓  ↓  ↓
   EQ  Reverb  Comp
    ↓
Master Bus Processing
    ↓
Audio Output
```

### v3.x Full DAW
```
Multi-Track Engine
    ↓
Routing Matrix
    ↓  ↓  ↓
  Bus A  Bus B  Bus C
    ↓      ↓      ↓
  FX Chain per bus
    ↓      ↓      ↓
Master Bus with Limiter
    ↓
Network/Local Output
```

---

## 🎯 Priority Matrix

### Must-Have (v1.2)
1. **Real EQ Processing** - Without this, we're not even a music player
2. **Time Slider Fix** - Basic functionality
3. **Rack Mode Foundation** - Solve windowing permanently

### Should-Have (v1.3)
4. **Queue Drag & Drop** - Expected feature
5. **Multi-Select** - Power user necessity
6. **Better Search** - Find music faster

### Nice-to-Have (v2.0)
7. **VST Support** - Game-changing feature
8. **Universal Search** - All sources, one bar
9. **Preset Sharing** - Community building

### Future (v2.1+)
10. **Cloud Sync** - Multi-device paradise
11. **AI Enhancement** - Smart audio processing
12. **DAW Features** - Professional workflows

---

## 🚧 Technical Debt to Address

### Before v2.0
- [ ] Refactor panel system to rack architecture
- [ ] Migrate to proper audio engine (PyAudio/PortAudio)
- [ ] Database for settings (currently JSON)
- [ ] Plugin SDK documentation
- [ ] Automated testing framework
- [ ] Cross-platform build pipeline

### Performance Targets
- **Audio Latency**: < 10ms for real-time processing
- **UI Responsiveness**: < 100ms for all interactions
- **Search Speed**: < 50ms for 100k+ track library
- **Plugin Load**: < 500ms per VST instance
- **Memory**: < 500MB for typical session

---

## 📊 Success Metrics

### v1.x
- ✅ EQ changes audibly affect sound (v1.2)
- ✅ Settings persist 100% across restarts
- ✅ Zero crashes in 8-hour sessions
- ✅ Users prefer it over default music player

### v2.x
- 🎯 Support 90% of popular VST plugins
- 🎯 Users create and share 1000+ presets
- 🎯 Pro audio engineers adopt for casual listening
- 🎯 "Sidecar Protocol" adopted by 2+ other players

### v3.x
- 🌟 100k+ active users
- 🌟 Industry standard for per-track audio settings
- 🌟 Featured in audio production magazines
- 🌟 First choice for audiophiles and creators

---

## 🤝 How to Contribute

### Current Priorities (Need Help!)
1. **EQ DSP Implementation** - Audio engineers welcome!
2. **UI/UX Polish** - Designers, help us shine
3. **Cross-Platform Testing** - Windows/Linux testers needed
4. **Documentation** - Write guides, tutorials, examples

### Future Opportunities
- VST SDK integration (v2.0)
- AI/ML audio processing (v3.0)
- Mobile apps (iOS/Android)
- Web player (WASM/WebAudio)

---

## 📅 Release Schedule

| Version | Focus | Target Date | Status |
|---------|-------|-------------|--------|
| v1.1.0 | Foundation | Oct 2025 | ✅ Shipped |
| v1.2.0 | Real EQ + Rack Mode | Nov 2025 | 🔨 In Progress |
| v1.3.0 | Queue & Search | Dec 2025 | 📋 Planned |
| v2.0.0 | VST + Universal Search | Q2 2026 | 🎯 Roadmap |
| v2.1.0 | Cloud + Protocol | Q3 2026 | 💭 Vision |
| v3.0.0 | AI + Collaboration | 2027+ | 🌟 Future |

---

## 💡 Why This Roadmap?

**Short-term (v1.x)**: Get the basics perfect
- Users need EQ that WORKS
- Library management must be smooth
- No crashes, no data loss

**Medium-term (v2.x)**: Differentiate and dominate
- VST support = professional power
- Universal search = ultimate convenience
- Open protocol = industry leadership

**Long-term (v3.x)**: Redefine the category
- AI audio = magical experience
- Collaboration = social platform
- DAW integration = creative hub

---

**Questions? Ideas? Join the conversation!**

- 📧 Email: OhioMathTeacher@users.noreply.github.com
- 💬 GitHub Discussions: [Coming Soon]
- 🐛 Issues: [github.com/OhioMathTeacher/sidecar-eq/issues](https://github.com/OhioMathTeacher/sidecar-eq/issues)

---

*"We're not just building a music player. We're building the future of personalized audio."*
