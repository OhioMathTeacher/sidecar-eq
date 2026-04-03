# Sidecar EQ - Software Assessment & Upgrade Roadmap

**Assessment Date**: April 2026
**Current Version**: v2.2.0
**Assessed By**: Automated Code Analysis

---

## 1. Executive Summary

Sidecar EQ is a desktop music player built with Python/PySide6 (Qt6) that differentiates itself through per-track EQ and volume memory. The application has grown organically from v1.0 to v2.2.0, adding Plex integration, a library browser, playlist management, real-time EQ via Pedalboard/PyAudio, and artist metadata display.

**Strengths**: Unique per-track EQ concept, functional audio engine with real DSP, comprehensive metadata support, and solid Plex integration.

**Key Concerns**: The main `app.py` file is 6,277 lines (a "god class"), the UI relies heavily on inline Qt stylesheets with no consistent design system, test coverage is thin relative to codebase size, and data persistence uses flat JSON files that won't scale.

---

## 2. Architecture Assessment

### 2.1 Codebase Structure

| Component | File | Lines | Assessment |
|-----------|------|-------|------------|
| Main Window (God Class) | `app.py` | 6,277 | **Critical** - needs decomposition |
| Search | `search.py` | 942 | Large but focused |
| Plex Account Manager | `plex_account_manager.py` | 958 | Reasonable for complexity |
| Queue Model | `queue_model.py` | 788 | Well-structured Qt model |
| Library | `library.py` | 648 | Good data modeling |
| Audio Sources | `audio_sources.py` | 546 | Multi-source abstraction |
| Music Metadata | `music_metadata.py` | 477 | Network metadata fetching |
| Player | `player.py` | 446 | Multi-backend player wrapper |
| Audio Engine | `audio_engine.py` | 291 | Clean, focused DSP engine |
| **Total Source** | **16,233 lines** across 30 Python files | | |

### 2.2 Critical Architectural Issues

#### Issue 1: Monolithic `app.py` (Severity: HIGH)
The `MainWindow` class in `app.py` is a 6,000+ line god class that handles:
- UI construction (toolbar, panels, menus, status bar)
- Playback control logic
- Queue management
- EQ slider wiring
- Artist metadata display
- Playlist management
- Library browser integration
- Plex connection
- Background analysis orchestration
- Panel collapse state management
- Layout presets
- Keyboard shortcuts

**Impact**: Extremely difficult to maintain, test, or modify without side effects. Any UI change risks breaking unrelated functionality.

#### Issue 2: Flat JSON Data Store (Severity: MEDIUM)
`store.py` loads the entire `db.json` into memory at startup and rewrites it on every change. This works for small libraries but will degrade with large collections (10,000+ tracks).

#### Issue 3: No Separation of Concerns (Severity: HIGH)
Business logic (playback, EQ processing, metadata fetching) is tightly coupled with UI code in `app.py`. There is no controller/presenter layer between the model and view.

#### Issue 4: Dead Code and Duplicates (Severity: LOW)
- `audio_engine_old.py` (438 lines) - superseded by `audio_engine.py`
- Duplicate docstrings at the top of `app.py` (lines 1-37 repeated)
- `dist_dir/` contains a full bundled application that inflates the repo

### 2.3 Tech Stack Assessment

| Technology | Version | Status | Notes |
|------------|---------|--------|-------|
| Python | >=3.10 | Good | Current and well-supported |
| PySide6 | >=6.7 | Good | Official Qt6 bindings |
| Pedalboard | (imported) | Good | Spotify's DSP library, professional quality |
| PyAudio | (imported) | Adequate | Works but PortAudio dependency can be painful to install |
| librosa | >=0.10 | Good | Audio analysis |
| numpy/scipy | latest | Good | Core scientific computing |
| plexapi | >=4.0 | Good | Official Plex Python client |
| mutagen | >=1.47 | Good | Audio metadata reading |

**Missing from `pyproject.toml`**: `pedalboard` and `pyaudio` are imported but not listed as dependencies, meaning `pip install -e .` won't install them.

---

## 3. UI/UX Assessment

### 3.1 Current UI Architecture

The UI uses a vertical stack of `CollapsiblePanel` widgets:
1. **Song Queue & Metadata** - Table view with 15 columns
2. **EQ & Waveform** - 7-band EQ sliders + waveform progress bar
3. **Now Playing** - Artist info, album art, tracklist
4. **Playlists** - Playlist browser
5. **Library Browser** - Artist > Album > Track tree (shown by layout presets)

Layout presets (Full, Queue Only, EQ Only, etc.) show/hide panels.

### 3.2 UI Issues

#### Issue 1: Inconsistent Styling (Severity: MEDIUM)
Styles are split across multiple locations:
- `ui_builders/styles.py` - Centralized stylesheets (165 lines)
- `modern_ui.py` - Color constants and font utilities (331 lines)
- Inline `setStyleSheet()` calls scattered throughout `app.py` and other files (e.g., the context menu in `CustomTableHeader` at line 218)
- Hard-coded color values (`#2a2a2a`, `#404040`, etc.) repeated in many places

There is no single source of truth for theming.

#### Issue 2: No Responsive Layout (Severity: MEDIUM)
The application uses fixed column widths and pixel-based sizing. Panels don't adapt well to different screen sizes or DPI settings. The `CollapsiblePanel` system works but doesn't provide smooth resizing between panels (no `QSplitter` usage for user-resizable boundaries).

#### Issue 3: Waveform is Simulated (Severity: LOW)
The `WaveformProgress` widget generates random bar heights (`random.uniform(0.3, 1.0)`) rather than showing actual audio waveform data. This is cosmetic but misleading.

#### Issue 4: Limited Accessibility (Severity: MEDIUM)
- No keyboard navigation between panels
- No ARIA-equivalent accessibility hints for screen readers
- Color contrast ratios not verified against WCAG standards
- Tooltips are sparse

#### Issue 5: Dark Mode Only (Severity: LOW)
`ModernColors.is_dark_mode()` always returns `True`. There is no light theme option, and the system theme preference is ignored.

#### Issue 6: No Loading/Progress States (Severity: MEDIUM)
File loading, Plex connections, and metadata fetching happen in background threads but there is limited visual feedback. The audio engine note says "caller should show loading indicator" but this isn't implemented.

### 3.3 UI Components Quality

| Component | Quality | Notes |
|-----------|---------|-------|
| `KnobWidget` | Good | Angular rotation, wheel, keyboard, mute toggle |
| `WaveformProgress` | Fair | Visually appealing but uses fake data |
| `BeamSlider` | Good | Custom EQ slider with LED-style rendering |
| `LEDMeter` | Good | Real-time level visualization |
| `CollapsiblePanel` | Fair | Works but animations can feel janky |
| `IconButton` | Good | Three-state icons with hover/press feedback |
| `StarRatingDelegate` | Good | In-cell star rating editor |
| `ScrollingLabel` | Good | Marquee-style text for long metadata |
| Queue Table | Good | Sortable, column management, drag-drop |

---

## 4. Testing Assessment

### 4.1 Test Coverage

- **Test files**: 23 files, ~3,100 total lines
- **Source files**: 30 files, ~16,200 total lines
- **Approximate test-to-source ratio**: 0.19 (low; industry standard is 0.5-1.0+)

### 4.2 Test Quality

| Area | Coverage | Notes |
|------|----------|-------|
| Audio Engine | Moderate | `test_audio_engine.py` (189 lines) covers basic EQ |
| EQ Processing | Good | 5 separate test files for EQ functionality |
| Library | Moderate | `test_library.py` (297 lines) |
| Plex | Moderate | 2 test files but likely require live server |
| UI | Minimal | `test_ui.py` (127 lines) - very basic widget tests |
| `app.py` (MainWindow) | None | The largest file has zero direct test coverage |
| Integration | Minimal | `test_integration.py` (35 lines) |

### 4.3 Testing Gaps

- No tests for playlist save/load
- No tests for layout preset switching
- No tests for panel collapse/expand
- No end-to-end playback tests
- No performance/load tests
- No tests for Plex streaming pipeline
- `conftest.py` is only 20 lines with minimal fixtures

---

## 5. Performance Assessment

### 5.1 Known Performance Concerns

1. **JSON Database**: `store.py` reads/writes the entire DB on every operation. With 10,000 tracks, this could mean writing a multi-MB file on every play count increment.

2. **Audio Loading**: `AudioEngine.load_file()` loads the entire audio file into memory as a NumPy array. A 10-minute FLAC file at 44.1kHz stereo is ~200MB of float32 data.

3. **Metadata Loading**: Disabled in production (`_auto_refresh_metadata` is commented out) due to "UI responsiveness issues."

4. **No Lazy Loading**: The queue table loads all metadata upfront rather than on-demand as rows become visible.

### 5.2 Audio Pipeline

The current pipeline is functional and well-designed:
```
AudioFile (Pedalboard) → NumPy array → Pedalboard EQ → Volume → PyAudio output
```

The 2048-sample chunk size at 44.1kHz gives ~46ms latency, which is acceptable for music playback but could be tightened to ~23ms (1024 samples) for more responsive EQ changes.

---

## 6. Upgrade Roadmap

### Phase 1: Stabilize & Refactor (Weeks 1-4)

**Goal**: Make the codebase maintainable without changing visible behavior.

#### 1.1 Decompose `app.py` (Week 1-2)
Extract the MainWindow god class into focused modules:

```
sidecar_eq/
  app.py              → Slim MainWindow (~500 lines), wiring only
  controllers/
    playback.py       → Play/pause/stop/seek logic
    queue.py          → Queue add/remove/reorder logic
    eq.py             → EQ slider ↔ audio engine bridge
    metadata.py       → Artist info fetching orchestration
  views/
    toolbar.py        → Toolbar construction and actions
    eq_panel.py       → EQ & waveform panel
    now_playing.py    → Artist info panel
    playlist_panel.py → Playlist browser panel
    queue_panel.py    → Queue table configuration
```

**How**: Use the "Strangler Fig" pattern - extract one method group at a time, delegate from MainWindow, verify no regressions after each extraction.

#### 1.2 Fix Dependency Declaration (Week 1)
Add missing dependencies to `pyproject.toml`:
```toml
dependencies = [
  ...
  "pedalboard>=0.8",
  "pyaudio>=0.2.14",
]
```

#### 1.3 Remove Dead Code (Week 1)
- Delete `audio_engine_old.py`
- Remove duplicate docstring block in `app.py` (lines 20-37)
- Evaluate `dist_dir/` - add to `.gitignore` or remove from repo

#### 1.4 Unify Styling System (Week 2-3)
Create a single theme engine:

```python
# sidecar_eq/theme.py
class Theme:
    """Single source of truth for all colors, fonts, and spacing."""

    # Surfaces
    BG_PRIMARY = "#1c1c1e"
    BG_SECONDARY = "#2c2c2e"
    BG_ELEVATED = "#3a3a3c"

    # Text
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#a0a0a0"
    TEXT_DISABLED = "#606060"

    # Accent
    ACCENT = "#007aff"
    ACCENT_HOVER = "#3395ff"

    # Spacing
    SPACING_SM = 4
    SPACING_MD = 8
    SPACING_LG = 16

    @classmethod
    def stylesheet(cls) -> str:
        """Generate complete application stylesheet."""
        ...
```

Migrate all inline `setStyleSheet()` calls and `styles.py` constants to use this theme.

#### 1.5 Improve Test Foundation (Week 3-4)
- Expand `conftest.py` with reusable fixtures (mock player, mock audio engine, test queue)
- Add tests for the extracted controller classes
- Set up test coverage reporting (`pytest-cov`)
- Target: 40% coverage on non-UI code

### Phase 2: UI Modernization (Weeks 5-8)

**Goal**: Make the UI polished, responsive, and intuitive.

#### 2.1 Implement Real Waveform Display (Week 5)
Replace the random waveform with actual audio data:
- Compute RMS envelope on file load (fast, ~100ms)
- Cache waveform data alongside EQ settings
- Draw actual amplitude bars in `WaveformProgress`

#### 2.2 Add Splitter-Based Panel Layout (Week 5-6)
Replace the fixed `QVBoxLayout` of collapsible panels with `QSplitter`:
- Users can drag panel boundaries to resize
- Remember splitter positions between sessions
- Minimum sizes prevent panels from being hidden accidentally
- Double-click splitter handle to auto-fit

#### 2.3 Modernize Visual Design (Week 6-7)
- **Rounded cards**: Wrap each panel in a subtle rounded-corner container with `border-radius: 8px`
- **Better contrast**: Increase text/background contrast to meet WCAG AA (4.5:1 ratio)
- **Icon refresh**: Replace emoji-based indicators (globe, play state) with proper SVG icons
- **Consistent spacing**: Apply uniform padding/margins from the theme system
- **Loading states**: Add spinner/skeleton screens for metadata fetching and file loading
- **Smooth animations**: Use `QPropertyAnimation` for panel transitions (already scaffolded in `modern_ui.py`)

#### 2.4 Add Light Theme Support (Week 7)
- Implement a `LightTheme` variant alongside the existing dark theme
- Auto-detect system preference on macOS/Windows (`QPalette` or platform APIs)
- Add theme toggle in settings

#### 2.5 Improve Queue Table UX (Week 7-8)
- **Virtual scrolling**: Use `fetchMore()` pattern for large queues
- **Inline editing**: Double-click to edit title/artist directly in the table
- **Multi-select**: Shift-click range selection (already partially implemented)
- **Context menu**: Right-click for Play, Remove, Show in Finder, Copy Path
- **Column presets**: Quick column layout switching (Compact, Full, Minimal)

#### 2.6 Add Keyboard Navigation (Week 8)
- Tab between panels
- Arrow keys within panels
- Global shortcuts documented in a help overlay (press `?`)
- Focus indicators visible on all interactive elements

### Phase 3: Data & Performance (Weeks 9-11)

**Goal**: Make the app fast and reliable at scale.

#### 3.1 Migrate to SQLite (Week 9-10)
Replace `store.py` JSON with SQLite:

```sql
CREATE TABLE tracks (
    path TEXT PRIMARY KEY,
    title TEXT,
    artist TEXT,
    album TEXT,
    eq_settings TEXT,  -- JSON blob for 7-band gains
    volume REAL,
    play_count INTEGER DEFAULT 0,
    rating INTEGER DEFAULT 0,
    last_played TEXT,
    analysis_data TEXT  -- JSON blob for LUFS, tempo, etc.
);
```

**Benefits**:
- Atomic writes (no data corruption from interrupted saves)
- Fast queries (no full-file read/write)
- Concurrent access safe
- Standard tooling for debugging

**Migration**: Auto-detect `db.json` on startup, import into SQLite, rename old file to `db.json.migrated`.

#### 3.2 Streaming Audio Decode (Week 10)
Replace full-file loading with chunked streaming:
- Read audio in 1-second blocks using `soundfile` or `pedalboard.io.AudioFile`
- Process and play each block in sequence
- Reduces memory from ~200MB per track to ~1MB buffer

#### 3.3 Background Indexing (Week 11)
- Use `QFileSystemWatcher` to detect new/changed files in library folders
- Index metadata in a background thread
- Incremental updates (only scan changed files)
- Progress indicator in status bar

### Phase 4: Feature Enhancements (Weeks 12-16)

**Goal**: Add high-value features that differentiate Sidecar EQ.

#### 4.1 Individual `.sidecar` Files (Week 12-13)
Implement the planned `.sidecar` file format:
- Write `song.mp3.sidecar` JSON next to each audio file
- Include EQ, volume, play count, rating, analysis data
- Fall back to SQLite for tracks in read-only locations
- Auto-migrate from centralized DB on first play of each track

#### 4.2 EQ Presets Library (Week 13)
- Built-in presets: Flat, Bass Boost, Vocal Clarity, Treble Enhance, etc.
- User-created presets with save/name/delete
- One-click apply from dropdown in EQ panel
- Import/export presets as JSON

#### 4.3 Audio Spectrum Analyzer (Week 14)
- Real-time FFT visualization using `pyqtgraph`
- Show pre-EQ and post-EQ overlay
- Helps users understand what each EQ band affects
- Toggle on/off to save CPU

#### 4.4 Smart Search Improvements (Week 15)
- Fuzzy matching with configurable threshold
- Search by genre, year range, rating
- "More like this" based on audio analysis similarity
- Recently played quick list
- Search history with suggestions

#### 4.5 Export with EQ Applied (Week 16)
- Render a track with current EQ + volume baked in
- Output formats: WAV, FLAC, MP3
- Batch export for playlists
- Progress dialog with cancel support

---

## 7. Quick Wins (Can Do Immediately)

These improvements require minimal effort and high impact:

| # | Improvement | Effort | Impact |
|---|------------|--------|--------|
| 1 | Fix missing `pedalboard`/`pyaudio` in dependencies | 5 min | HIGH - app won't install without them |
| 2 | Delete `audio_engine_old.py` and duplicate docstring | 5 min | LOW - code hygiene |
| 3 | Replace emoji icons with SVGs in queue table | 2 hrs | MEDIUM - looks more professional |
| 4 | Add `.gitignore` entry for `dist_dir/` | 5 min | LOW - repo cleanliness |
| 5 | Show real waveform envelope instead of random bars | 4 hrs | MEDIUM - credibility boost |
| 6 | Add loading spinner during file load | 2 hrs | MEDIUM - UX improvement |
| 7 | Add `pytest-cov` and coverage reporting to CI | 1 hr | MEDIUM - visibility into test gaps |

---

## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `app.py` refactor introduces regressions | High | High | Extract incrementally, test each step, keep feature branch |
| SQLite migration loses user data | Low | Critical | Backup original JSON, verify migration row counts |
| PyAudio install fails on user systems | Medium | High | Provide pre-built wheels or document platform-specific steps |
| Qt version incompatibilities | Low | Medium | Pin PySide6 to tested minor version |
| Large FLAC files cause memory issues | Medium | Medium | Implement streaming decode (Phase 3.2) |

---

## 9. Recommended Priority Order

1. **Fix dependency declarations** (immediate)
2. **Decompose `app.py`** (enables everything else)
3. **Unify theme system** (enables consistent UI work)
4. **Migrate to SQLite** (data safety + performance)
5. **Modernize panel layout** (biggest UX win)
6. **Real waveform display** (credibility)
7. **Streaming audio decode** (memory safety)
8. **`.sidecar` file format** (core differentiator)
9. **EQ presets** (user-requested feature)
10. **Spectrum analyzer** (professional appeal)

---

## 10. Summary Metrics

| Metric | Current | Target (6 months) |
|--------|---------|-------------------|
| Largest file | 6,277 lines | < 800 lines |
| Test coverage (est.) | ~15% | > 50% |
| Data store | JSON (full read/write) | SQLite |
| Theme sources | 4+ locations | 1 centralized theme |
| Startup time (est.) | 2-5s | < 2s |
| Memory per track | ~200MB peak | < 5MB streaming |
| Supported themes | 1 (dark only) | 2 (dark + light + system detect) |
| CI pipeline | Build only | Build + test + coverage + lint |

---

*This assessment provides an honest evaluation of Sidecar EQ's current state and a practical roadmap for improvement. The app has a strong conceptual foundation - per-track EQ is genuinely useful. The primary work needed is structural: breaking apart the monolith, standardizing the UI layer, and hardening the data pipeline.*
