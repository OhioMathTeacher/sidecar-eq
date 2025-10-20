# Stem Mixing & Remix Sharing Vision

## Overview

Transform the EQ panel into a full **stem mixing console** where users can:
1. Separate songs into isolated tracks (vocals, drums, bass, guitar, other)
2. Control volume and mute for each stem independently
3. Apply per-stem EQ (5 stems × 7 bands = 35 EQ controls!)
4. **Save and share "remixes" as lightweight text files**

This enables a **collaborative remix ecosystem** where:
- Remixes are tiny JSON files (few KB) instead of full audio files (MB/GB)
- Anyone with the original song can apply someone else's remix instantly
- Remixes are version-controllable, diffable, and shareable via text (email, GitHub, forums)
- No copyright issues - you're sharing mixing instructions, not audio

## Architecture Already in Place ✅

The codebase was **designed with stem separation from day 1**:

### Song Class (`library.py`)
```python
class Song:
    """Each song can have separated stems cached on disk."""
    
    # Per-stem settings stored in database
    stem_settings = {
        'vocals': {'volume': 1.0, 'muted': False, 'eq': None},
        'drums':  {'volume': 1.0, 'muted': False, 'eq': None},
        'bass':   {'volume': 1.0, 'muted': False, 'eq': None},
        'guitar': {'volume': 1.0, 'muted': False, 'eq': None},
        'other':  {'volume': 1.0, 'muted': False, 'eq': None},
    }
    
    # Stems cached in: ~/.sidecar_eq/stems/{song_hash}/
    #   ├─ vocals.wav
    #   ├─ drums.wav
    #   ├─ bass.wav
    #   ├─ guitar.wav
    #   └─ other.wav
```

### Methods Already Implemented
- `song.has_stems` - Check if stems exist
- `song.get_stem_path(name)` - Get path to specific stem
- `song.stem_cache_dir` - Directory for this song's stems
- `song.to_dict()` - Serializes stem_settings to JSON
- `store.save_record()` - Persists stem settings to database

## Implementation Roadmap

### Phase 1: Stem Separation (Foundation)
**Estimated Time**: 2-3 weeks

#### 1.1 Integrate Demucs or Spleeter
```python
# New file: sidecar_eq/stem_separator.py

class StemSeparator:
    """Separate audio into stems using AI models."""
    
    def separate(self, audio_path: str) -> dict[str, str]:
        """Separate audio into 5 stems.
        
        Args:
            audio_path: Path to original audio file
            
        Returns:
            Dict of stem_name -> stem_path
            {'vocals': '~/.sidecar_eq/stems/abc123/vocals.wav', ...}
        """
        # Use demucs (best quality) or spleeter (faster)
        # Cache results in song.stem_cache_dir
        pass
```

**Dependencies**:
- `demucs` (Meta's state-of-the-art stem separator)
- Or `spleeter` (Deezer's lighter alternative)
- `torch` (for neural network inference)

**UI Changes**:
- Add "Separate Stems" button to queue context menu
- Show progress bar during separation (can take 30-120s per song)
- Cache stems permanently (only separate once per song)

#### 1.2 Multi-Stem Playback in AudioEngine
```python
class AudioEngine:
    """Extend to play multiple stems simultaneously."""
    
    def load_stems(self, stem_paths: dict[str, str]):
        """Load and mix 5 stems in real-time.
        
        Each stem gets:
        - Independent volume control
        - Independent mute
        - Independent 7-band EQ
        """
        pass
    
    def set_stem_volume(self, stem_name: str, volume: float):
        """Adjust individual stem volume (0.0 to 2.0)."""
        pass
    
    def set_stem_muted(self, stem_name: str, muted: bool):
        """Mute/unmute a stem."""
        pass
    
    def set_stem_eq(self, stem_name: str, band: int, gain: float):
        """Apply EQ to individual stem."""
        pass
```

**Technical Challenge**: Mix 5 audio streams in real-time with low latency
- Solution: Use numpy to sum stem buffers before PyAudio output
- Each stem processes through its own EQ chain
- Volume/mute applied before mixing

### Phase 2: Mixer UI (The Fun Part!)
**Estimated Time**: 2-3 weeks

#### 2.1 Stem Mixer Panel
Replace or extend the EQ panel with a **professional mixing console**:

```
┌─────────────────────────────────────────────────────────┐
│  STEM MIXER                          [Save Remix] [Load]│
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Vocals      Drums       Bass        Guitar     Other   │
│  ┌────┐     ┌────┐     ┌────┐      ┌────┐     ┌────┐  │
│  │    │     │    │     │    │      │    │     │    │  │
│  │ ▓▓ │     │ ▓▓ │     │ ▓▓ │      │ ▓▓ │     │ ▓▓ │  │ ← Faders
│  │ ▓▓ │     │ ▓▓ │     │ ▓▓ │      │ ▓▓ │     │ ▓▓ │  │
│  │ ▓▓ │     │ ▓▓ │     │ ▓▓ │      │ ▓▓ │     │ ▓▓ │  │
│  │ ▓▓ │     │ ▓▓ │     │ ▓▓ │      │ ▓▓ │     │ ▓▓ │  │
│  └────┘     └────┘     └────┘      └────┘     └────┘  │
│   100%       85%        120%         60%        90%    │
│                                                          │
│  [M] Solo   [M] Solo   [M] Solo    [M] Solo   [M] Solo │ ← Mute/Solo
│  [ ] [S]    [ ] [S]    [ ] [S]     [✓] [S]    [ ] [S] │
│                                                          │
│  ┌─ EQ (click stem to expand) ─────────────────────┐   │
│  │  60Hz  150Hz  400Hz  1kHz  2.4kHz  6kHz  15kHz  │   │
│  │   +2    -1     +3    +1     -2     +4     +2    │   │ ← Per-Stem EQ
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  Master: [════════▓▓══] 95%                             │ ← Master fader
└─────────────────────────────────────────────────────────┘
```

**Features**:
- **Vertical faders**: Industry-standard mixer layout
- **Solo mode**: Mute all except selected stem
- **Per-stem EQ**: Collapsible 7-band EQ for each stem
- **Master fader**: Control overall mix volume
- **Peak meters**: Real-time VU meters for each stem
- **Color coding**: Visual distinction (vocals=blue, drums=red, etc.)

#### 2.2 Stem Waveform Visualization
Show 5 mini waveforms stacked vertically, like a DAW:
```
Vocals  ▁▂▃▅▇▇▅▃▂▁  ▁▂▃▅▇▇▅▃▂▁
Drums   ▁█▁█▁█▁█▁  ▁█▁█▁█▁█▁
Bass    ▂▂▂▂▄▄▂▂▂  ▂▂▂▂▄▄▂▂▂
Guitar  ▁▃▅▃▁▁▃▅▃  ▁▃▅▃▁▁▃▅▃
Other   ▁▁▂▂▂▂▁▁▁  ▁▁▂▂▂▂▁▁▁
```

### Phase 3: Remix File Format (The Innovation!)
**Estimated Time**: 1 week

#### 3.1 Remix File Structure
**Format**: JSON (human-readable, version-controllable, tiny)

```json
{
  "sidecar_remix_version": "1.0",
  "song_id": {
    "title": "Supernaut",
    "artist": "Black Sabbath",
    "album": "Vol. 4",
    "duration_ms": 264000,
    "fingerprint": "acb8f3e9a1c2..."  // Audio fingerprint to verify song match
  },
  "metadata": {
    "remix_name": "Vocals-Forward Mix",
    "creator": "todd@example.com",
    "created": "2025-10-20T15:30:00Z",
    "description": "Brings vocals to front, tames the distortion on guitar",
    "tags": ["vocal-focused", "clearer-mix", "radio-friendly"]
  },
  "stems": {
    "vocals": {
      "volume": 1.35,
      "muted": false,
      "eq": [
        {"band": 0, "freq": 60, "gain": -2.0},    // Hz: Cut mud
        {"band": 1, "freq": 150, "gain": -1.0},
        {"band": 2, "freq": 400, "gain": 0.0},
        {"band": 3, "freq": 1000, "gain": 2.5},   // kHz: Boost presence
        {"band": 4, "freq": 2400, "gain": 3.0},
        {"band": 5, "freq": 6000, "gain": 1.5},
        {"band": 6, "freq": 15000, "gain": 2.0}   // Sparkle
      ]
    },
    "drums": {
      "volume": 0.85,
      "muted": false,
      "eq": [...]
    },
    "bass": {
      "volume": 1.1,
      "muted": false,
      "eq": [...]
    },
    "guitar": {
      "volume": 0.65,  // Tamed!
      "muted": false,
      "eq": [
        {"band": 0, "freq": 60, "gain": 0.0},
        {"band": 1, "freq": 150, "gain": 0.0},
        {"band": 2, "freq": 400, "gain": -3.0},   // Cut harshness
        {"band": 3, "freq": 1000, "gain": -2.0},
        {"band": 4, "freq": 2400, "gain": -4.0},  // Major cut
        {"band": 5, "freq": 6000, "gain": -1.0},
        {"band": 6, "freq": 15000, "gain": 0.0}
      ]
    },
    "other": {
      "volume": 0.9,
      "muted": false,
      "eq": [...]
    }
  },
  "master": {
    "volume": 0.95,
    "eq": [...]  // Optional master bus EQ
  }
}
```

**File Size**: ~2-5 KB (vs 30-50 MB for audio file!)

#### 3.2 Remix Sharing Features

**Export Remix**:
```python
# File → Export → Remix File...
# Saves to: ~/Music/Remixes/Black_Sabbath-Supernaut-VocalForward.sidecar
```

**Import Remix**:
```python
# File → Import → Remix File...
# Or drag-drop .sidecar file onto app
# Verifies song match via fingerprint
# Applies all stem settings instantly
```

**Remix Browser** (Future):
```
┌─────────────────────────────────────────┐
│  REMIX BROWSER                          │
├─────────────────────────────────────────┤
│  Supernaut - Black Sabbath              │
│                                          │
│  ⭐⭐⭐⭐⭐  Vocals-Forward Mix            │
│  By: todd@example.com                   │
│  "Clearer vocals, tamed guitar"         │
│  [Preview] [Apply] [Download]           │
│                                          │
│  ⭐⭐⭐⭐   Drum-Heavy Mix                │
│  By: musicfan123                        │
│  "For drummers studying the track"      │
│  [Preview] [Apply] [Download]           │
│                                          │
│  ⭐⭐⭐⭐   Karaoke Version                │
│  By: singalong.net                      │
│  "Vocals muted, instruments balanced"   │
│  [Preview] [Apply] [Download]           │
└─────────────────────────────────────────┘
```

### Phase 4: Community Features (The Ecosystem!)
**Estimated Time**: 2-3 weeks

#### 4.1 Remix Repository
- **GitHub-like hosting** for .sidecar files
- Version control: Track changes to remixes over time
- Fork/branch: Create variations of existing remixes
- Pull requests: Suggest improvements to popular remixes
- Stars/ratings: Community curation

#### 4.2 Remix Marketplace
- **Free sharing**: Open ecosystem by default
- **Paid remixes**: Optional for professional mixers
- **Remix packs**: Bundle remixes for full albums
- **Creator profiles**: Build reputation as a remix artist

#### 4.3 Legal & Copyright Benefits
✅ **No copyright issues** - you're sharing mixing instructions, not audio
✅ **Tiny file size** - email-friendly, low bandwidth
✅ **Open format** - text-based, reverse-engineerable
✅ **Requires original** - users must own the song
✅ **Educational** - learn mixing by studying remix files
✅ **Collaborative** - diff/merge remix variations

## Technical Implementation Details

### Audio Fingerprinting
To verify song matches, use:
- **Chromaprint** (used by AcoustID/MusicBrainz)
- **echoprint** (Spotify's fingerprinting)
- Or simple MD5 of first 30s of audio

```python
def verify_remix_compatibility(song_path: str, remix_data: dict) -> bool:
    """Check if remix matches the song."""
    actual_fingerprint = get_audio_fingerprint(song_path)
    expected_fingerprint = remix_data['song_id']['fingerprint']
    return actual_fingerprint == expected_fingerprint
```

### Performance Considerations
- **5 stems × 7 bands = 35 biquad filters** running in real-time
- Need ~50ms buffers to avoid latency
- Target: <10% CPU on modern hardware
- Optimization: Use SIMD for filter processing

### Storage
- **Stems**: ~200 MB per song (5 × 40 MB WAV files)
- **Separation time**: 30-120 seconds per song
- **Caching**: Separate once, reuse forever
- **Cleanup**: Option to delete stems and re-separate if needed

## Use Cases

### For Listeners
- **Karaoke mode**: Mute vocals
- **Learn instruments**: Isolate bass/drums to study
- **Fix bad mixes**: Rebalance poorly mixed songs
- **Custom versions**: Create your ideal mix

### For Musicians
- **Practice tool**: Loop and isolate difficult parts
- **Study production**: Analyze stem levels in pro mixes
- **Cover songs**: Mute instruments you'll replace
- **Remix practice**: Learn mixing without recording

### For Educators
- **Music theory**: Demonstrate instrument roles
- **Production courses**: Teach mixing with real songs
- **Share assignments**: Students remix the same song
- **Grading**: Compare student remixes side-by-side

### For Communities
- **Remix contests**: Best mix wins
- **Collaborative mixing**: Crowd-source the perfect mix
- **Genre experiments**: Turn rock into jazz via stem balance
- **Accessibility**: Custom mixes for hearing impaired

## Example Workflow

1. **User adds song to queue**
2. **Right-click → "Separate Stems"** (one-time, 60s wait)
3. **Switch to "Mixer" panel** (new layout preset)
4. **Adjust stem volumes and EQ** in real-time
5. **Like the result? → File → Export → Remix File**
6. **Share remix.sidecar** via email/Discord/GitHub
7. **Friend imports remix** → Instant perfect mix!

## File Organization

```
~/.sidecar_eq/
├── stems/                    # Separated audio stems
│   ├── abc123/               # Hash of original file path
│   │   ├── vocals.wav
│   │   ├── drums.wav
│   │   ├── bass.wav
│   │   ├── guitar.wav
│   │   └── other.wav
│   └── def456/
│       └── ...
│
└── remixes/                  # Downloaded/imported remixes
    ├── Black_Sabbath/
    │   ├── Supernaut-VocalForward.sidecar
    │   ├── Supernaut-DrumHeavy.sidecar
    │   └── Supernaut-Karaoke.sidecar
    └── ...
```

## Migration Path (Gradual Rollout)

### v1.0 (Current)
- ✅ Basic EQ per song
- ✅ AudioEngine with real-time processing

### v1.5 (Next 1-2 months)
- 🔨 Stem separation integration
- 🔨 Multi-stem playback in AudioEngine
- 🔨 Basic mixer UI (5 faders)

### v2.0 (3-4 months)
- 🎯 Full mixer panel with per-stem EQ
- 🎯 Remix file export/import
- 🎯 Solo/mute modes
- 🎯 Waveform visualization

### v2.5 (6 months)
- 🚀 Remix browser/marketplace
- 🚀 Cloud sync for remixes
- 🚀 Community features

## Why This is Revolutionary

### For the Music Industry
- **New creative format**: Remixes without redistribution
- **Educational tool**: Learn from pro mixers
- **Accessibility**: Anyone can create remixes
- **Low barrier**: No DAW knowledge required

### For Open Source
- **Text-based format**: Git-friendly
- **Diffable**: See exact changes between versions
- **Mergeable**: Combine best parts of different remixes
- **Inspectable**: Learn by reading remix files

### For Users
- **Tiny files**: Email/share anywhere
- **Instant**: Apply remix in <1 second
- **Safe**: No piracy, requires original song
- **Fun**: Creative expression with favorite songs

## Next Steps

1. ✅ Document vision (this file!)
2. 📋 Research best stem separation library (demucs vs spleeter)
3. 📋 Prototype multi-stem AudioEngine
4. 📋 Design mixer UI mockups
5. 📋 Define remix file format spec v1.0
6. 🔨 Implement stem separation
7. 🔨 Build mixer panel
8. 🔨 Add export/import
9. 🚀 Launch remix ecosystem!

---

**This could be the killer feature that makes SidecarEQ unique in the music player space.** No other player lets you collaboratively remix songs as a community using text files. 🎵✨
