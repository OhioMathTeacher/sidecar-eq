# Sidecar EQ - TODO List

**Last Updated**: October 19, 2025  
**Current Sprint**: v1.2.0 - "Make It Actually Work"

---

## 🚨 CRITICAL (Must Fix for v1.2)

### 1. Real EQ Audio Processing - HIGHEST PRIORITY 🎛️
**Status**: Not Started  
**Estimate**: 2-3 weeks  
**Blocker**: This is THE feature - app is incomplete without it

**Current State**:
- ✅ UI sliders work perfectly
- ✅ Settings save/load correctly
- ❌ Audio is NOT filtered (sliders do nothing to sound)

**Implementation Options**:

#### Option A: PyAudio + scipy (RECOMMENDED)
**Pros**:
- Pure Python, easiest to debug
- Full control over audio pipeline
- scipy has excellent filter design tools
- Can add more effects later (compression, limiter)

**Cons**:
- Need to learn PyAudio API
- Manual buffer management
- ~500-800 lines of code

**Research Needed**:
- [ ] Test PyAudio with Qt event loop (threading issues?)
- [ ] Design parametric EQ filter bank (7 bands)
- [ ] Benchmark latency (target: <10ms)
- [ ] Test on macOS/Windows/Linux

#### Option B: FFmpeg Audio Filters
**Pros**:
- FFmpeg already used for video extraction
- Professional-grade DSP
- Powerful filter language

**Cons**:
- Complex filter syntax
- Harder to debug
- Need to rebuild audio pipeline

#### Option C: Qt Multimedia with Custom Filters
**Pros**:
- Integrated with existing QMediaPlayer
- Native Qt solution

**Cons**:
- Limited documentation
- Less flexible than PyAudio
- May not support all platforms equally

**Tasks**:
- [ ] Research: Which option best fits our architecture?
- [ ] Prototype: Simple 1-band EQ to prove concept
- [ ] Implement: Full 7-band parametric EQ
- [ ] Test: A/B comparison with known reference tracks
- [ ] Polish: Zero-latency, smooth parameter changes
- [ ] Document: How the audio pipeline works

---

### 2. Fix Time Slider 🕐
**Status**: Needs Investigation  
**Estimate**: 4-6 hours  
**Issue**: Position shows "00:00 / 00:00", seeking may not work

**Investigation Steps**:
- [ ] Test with actual playback - does it update at all?
- [ ] Check `Player.positionChanged` signal - is it emitting?
- [ ] Verify signal connections in `app.py`
- [ ] Test seeking (drag slider) - does position change?
- [ ] Check if issue is display-only or actual position tracking

**If Broken**:
- [ ] Debug player position/duration callbacks
- [ ] Add logging to trace signal flow
- [ ] Fix signal/slot connections
- [ ] Update UI on position changes
- [ ] Test with various file formats

**If Working**:
- [ ] Update TODO - mark as non-issue
- [ ] Document that it works correctly

---

### 3. Rack Mode Architecture 🎛️
**Status**: Foundation Started (feat/rack-mode branch)  
**Estimate**: 2-4 weeks (incremental rollout)  
**Goal**: Permanent solution to windowing issues

**Current Progress**:
- ✅ `rack.py` scaffolding created
- ✅ `settings_panel.py` component built
- ✅ Panel stretch fixes applied
- ⚠️ Needs design decisions on panel structure

**Phased Approach** (Don't break working UI):

#### Phase 1: Define Rack Panel Interface (2-3 days)
- [ ] Design RackPanel base class API
- [ ] Define fixed-size constraints (height only? or width too?)
- [ ] Plan panel registry (how to swap modules)
- [ ] Sketch output window design

#### Phase 2: Migrate One Panel (1 week)
- [ ] Convert Queue Panel to RackPanel
- [ ] Test thoroughly - does it work like before?
- [ ] Verify no regressions in functionality
- [ ] Document migration pattern

#### Phase 3: Migrate Remaining Panels (1 week)
- [ ] Convert EQ Panel to RackPanel
- [ ] Convert Search Panel to RackPanel
- [ ] Convert Settings Panel to RackPanel
- [ ] Test all view presets still work

#### Phase 4: Polish & Optimize (3-5 days)
- [ ] Output window for panel content (if needed)
- [ ] Hot-swap panel mechanism
- [ ] Keyboard shortcuts to swap panels
- [ ] Visual feedback for active panel
- [ ] Performance testing

**Success Criteria**:
- ✅ No more window resize bugs
- ✅ Panels are truly modular (can add new ones easily)
- ✅ All existing features still work
- ✅ UI feels more polished, less janky

---

## 🎯 HIGH PRIORITY (Should Fix for v1.2)

### 4. Queue Improvements
**Status**: Planned  
**May Defer to**: v1.3 if EQ takes longer

- [ ] **Drag & Drop Reordering**
  - Implement QAbstractItemModel drag/drop
  - Visual insertion indicator
  - Keyboard alternative (Alt+Up/Down?)
  - Works with multi-selection

- [ ] **Multi-Select Operations**
  - Command/Ctrl+Click to toggle selection
  - Shift+Click for range selection
  - Visual highlight for selected rows
  - Batch delete (Delete key on multiple)

- [ ] **Direct File Drag-In**
  - Accept drops from Finder/Explorer
  - Support: files, folders, playlists
  - Insert at drop position (not just end)
  - Auto-analyze new additions

---

## 💡 MEDIUM PRIORITY (Nice to Have for v1.2)

### 5. UI Polish
- [ ] Verify unsaved changes dialog works
- [ ] Add visual indicator (asterisk?) for modified tracks
- [ ] Test opacity menu with all panels
- [ ] Keyboard shortcuts documentation
- [ ] Tool tips on all controls

### 6. Error Handling
- [ ] Graceful handling of missing files
- [ ] Clear error messages (no cryptic Python tracebacks)
- [ ] Recovery options when things fail
- [ ] Log errors to file for debugging

### 7. Performance
- [ ] Profile startup time (currently acceptable?)
- [ ] Test with large queues (1000+ tracks)
- [ ] Optimize background analysis threading
- [ ] Memory leak testing (long sessions)

---

## 📋 BACKLOG (Defer to v1.3+)

### Search Enhancements
- [ ] Fuzzy search algorithm
- [ ] Search by lyrics (future)
- [ ] Recently played list
- [ ] Search history with suggestions
- [ ] Filter by genre, year, rating

### Playlist Features
- [ ] M3U8 export with Sidecar metadata
- [ ] Human-editable playlist format
- [ ] Smart playlists (auto-generated)
- [ ] Playlist sharing/import

### Library Management
- [ ] Background library indexer
- [ ] Automatic folder watching
- [ ] Duplicate detection
- [ ] Missing file scanner

---

## 🧪 Testing Checklist (Before v1.2 Release)

### Core Functionality
- [ ] EQ changes audibly affect audio (ALL 7 BANDS)
- [ ] Time slider shows position and allows seeking
- [ ] Settings persist across app restarts
- [ ] No data corruption in settings file
- [ ] No crashes in 8+ hour sessions

### Platform Testing
- [ ] macOS (Apple Silicon + Intel)
- [ ] Windows (10 & 11)
- [ ] Linux (Ubuntu, Fedora)

### Edge Cases
- [ ] Very long tracks (>1 hour)
- [ ] Many tracks in queue (500+)
- [ ] Rapid EQ adjustments (no audio glitches)
- [ ] Network file playback (NFS/SMB)
- [ ] Plex streams (various qualities)

### Regression Testing
- [ ] All v1.1 features still work
- [ ] No new bugs introduced
- [ ] Performance not degraded

---

## 📊 Progress Tracking

### v1.2.0 Completion: 15%
- [x] Views working (cleanup-style branch) - 10%
- [x] Search improvements (Enter to play) - 5%
- [ ] Real EQ audio processing - 0% (60% of remaining work)
- [ ] Time slider fixed - 0% (5% of remaining work)
- [ ] Rack mode foundation - 10% done, 90% remaining (30% of remaining work)
- [ ] Testing & polish - 0% (5% of remaining work)

### Estimated Timeline
- **Week 1-2**: EQ audio processing research & prototype
- **Week 2-3**: Full EQ implementation & testing
- **Week 3-4**: Rack mode migration (Phase 1-2)
- **Week 4-5**: Rack mode completion (Phase 3-4)
- **Week 5-6**: Bug fixes, testing, polish
- **Target Release**: Late November 2025

---

## 🎯 Definition of Done (v1.2)

**We can ship v1.2 when**:
1. ✅ EQ sliders audibly change the sound
2. ✅ Time slider shows position and works
3. ✅ Rack mode eliminates resize bugs
4. ✅ No regressions from v1.1
5. ✅ Tested on all 3 platforms
6. ✅ Documentation updated
7. ✅ ROADMAP.md reflects next steps

---

## 💭 Questions to Answer

### EQ Implementation
- **Q**: PyAudio vs FFmpeg vs Qt Audio?
  - **A**: TBD - need to prototype all three

- **Q**: Real-time or buffered processing?
  - **A**: Real-time for UI responsiveness

- **Q**: How to handle format conversions?
  - **A**: TBD - research needed

### Rack Mode
- **Q**: Fixed height only, or fixed width too?
  - **A**: TBD - depends on panel content needs

- **Q**: Do we need a separate output window?
  - **A**: Maybe? Test with current approach first

- **Q**: Can users create custom panels?
  - **A**: v2.0 feature (plugin system)

---

## 🔗 Related Documents

- [ROADMAP.md](ROADMAP.md) - Long-term vision (v1.x → v2.x → v3.x)
- [docs/VERSION_GOALS.md](docs/VERSION_GOALS.md) - Detailed v1/v2 requirements
- [docs/PRODUCT_VISION.md](docs/PRODUCT_VISION.md) - Product philosophy
- [docs/BUILD_NOTES.md](docs/BUILD_NOTES.md) - Build instructions

---

## 💡 How to Use This TODO

1. **Pick a task** from Critical section
2. **Create a branch** (`git checkout -b feature/eq-audio-processing`)
3. **Work on it** until done
4. **Check the box** when complete (`- [x] Task done`)
5. **Submit PR** or merge when tested
6. **Update progress** percentage

**Priority Order**:
1. EQ Audio Processing (blocks everything)
2. Time Slider Fix (quick win)
3. Rack Mode (long-term stability)
4. Everything else

---

*Let's make v1.2 the release where Sidecar EQ actually becomes a real EQ!* 🎛️
