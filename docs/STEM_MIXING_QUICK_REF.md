# Stem Mixing: Quick Reference

## What is Stem Mixing?

**Stem mixing** is the ability to separate a song into individual instrument tracks (stems) and control each one independently.

### The 5 Stems
1. **Vocals** - Lead and backing vocals
2. **Drums** - Kick, snare, hi-hat, cymbals, percussion
3. **Bass** - Bass guitar, synth bass, sub-bass
4. **Guitar** - Electric/acoustic guitars, keyboards, synths
5. **Other** - Everything else (effects, ambience, etc.)

## File Format: `.sidecar` Remix Files

### Why Text Files?

Traditional remixes require sharing **full audio files** (30-50 MB). 

Sidecar remixes share **mixing instructions** (~2-5 KB) as text files.

### Benefits

| Traditional Remix | Sidecar Remix |
|-------------------|---------------|
| 50 MB audio file | 2 KB text file |
| Copyright violation | Legal (no audio shared) |
| Can't edit/improve | Git-friendly, forkable |
| One fixed version | Collaborative iterations |
| Opaque binary | Human-readable JSON |

### Example `.sidecar` File

```json
{
  "sidecar_remix_version": "1.0",
  "song_id": {
    "title": "Supernaut",
    "artist": "Black Sabbath",
    "album": "Vol. 4"
  },
  "metadata": {
    "remix_name": "Karaoke Version",
    "creator": "todd@example.com",
    "description": "Vocals muted for karaoke"
  },
  "stems": {
    "vocals": {"volume": 0.0, "muted": true},
    "drums": {"volume": 1.1},
    "bass": {"volume": 1.2},
    "guitar": {"volume": 1.0},
    "other": {"volume": 0.9}
  }
}
```

## Use Cases

### For Listeners
- **Karaoke**: Mute vocals, sing along
- **Learn instruments**: Isolate bass to study technique
- **Fix bad mixes**: Rebalance poorly produced songs
- **Custom versions**: Your ideal mix of your favorite songs

### For Musicians
- **Practice**: Loop and isolate difficult parts
- **Study**: Analyze how pros balance instruments
- **Covers**: Mute instruments you'll replace
- **Transcription**: Hear each part clearly

### For Educators
- **Music theory**: Demonstrate instrument roles
- **Production**: Teach mixing with real songs
- **Assignments**: Students remix the same song
- **Analysis**: Compare student remixes

### For Communities
- **Remix contests**: Best mix wins
- **Collaborative mixing**: Crowd-source the perfect mix
- **Accessibility**: Custom mixes for hearing impaired
- **Preservation**: Save improved mixes of favorite songs

## Workflow

### Creating a Remix

1. **Add song to queue**
2. **Right-click → "Separate Stems"** (one-time, ~60s)
3. **Switch to Mixer panel**
4. **Adjust volumes and EQ** while listening
5. **File → Export → Remix File...**
6. **Share `MyRemix.sidecar` file** (email, Discord, GitHub)

### Applying a Remix

1. **File → Import → Remix File...**
2. **Select `MyRemix.sidecar` file**
3. **App verifies song match** (via audio fingerprint)
4. **Remix applied instantly** ✨

## Technical Details

### Stem Separation

**Technology**: Meta's Demucs (state-of-the-art AI)

**Performance**:
- Processing: ~60 seconds per 4-minute song
- Quality: Studio-grade separation
- Storage: ~200 MB per song (5 × 40 MB WAV files)
- Cached: Separate once, reuse forever

### Real-Time Mixing

**Processing**:
- 5 stems × 7 EQ bands = 35 biquad filters
- Target: <10% CPU on modern hardware
- Latency: <50ms (imperceptible)
- Buffer size: 2048 samples @ 44.1kHz

### File Format Spec

**Version**: 1.0  
**Format**: JSON (UTF-8)  
**Extension**: `.sidecar`  
**MIME type**: `application/x-sidecar-remix`

**Required fields**:
- `sidecar_remix_version`: Format version
- `song_id`: Song identification
- `stems`: Stem settings (volume, mute, EQ)

**Optional fields**:
- `metadata`: Creator info, description, tags
- `master`: Master bus settings
- `fingerprint`: Audio fingerprint for verification

## Sharing & Discovery

### Local Sharing
- Email attachment
- Drag & drop file sharing
- Messaging apps (Discord, Slack, etc.)

### Version Control
- GitHub repositories
- Track changes over time
- Fork and improve remixes
- Pull requests for suggestions

### Future: Remix Browser
- Browse popular remixes
- Filter by genre, mood, creator
- Preview before applying
- One-click download and apply
- Rate and review remixes

## Comparison to Other Tools

| Feature | DAW (Pro Tools) | Stems.app | SidecarEQ |
|---------|----------------|-----------|-----------|
| Stem separation | ❌ Manual only | ✅ AI-powered | ✅ AI-powered |
| File size | 500+ MB project | 50 MB audio | 2 KB text |
| Learning curve | Steep | Medium | Easy |
| Shareable | ❌ Huge files | ❌ Audio only | ✅ Tiny text |
| Version control | ❌ | ❌ | ✅ Git-friendly |
| Collaborative | ❌ | ❌ | ✅ Fork/improve |
| Copyright | ⚠️ Complicated | ⚠️ Sharing audio | ✅ No audio shared |
| Cost | $$$$ | $$ | Free |

## Legal & Copyright

### Why It's Legal

✅ **No audio distributed** - Only mixing instructions  
✅ **Requires original** - User must own the song  
✅ **Fair use** - Educational and transformative  
✅ **Open format** - Can't hide piracy in text  

### What You CAN Share
- Stem volume levels
- EQ settings per stem
- Mute/solo states
- Mixing instructions
- Creative decisions

### What You CANNOT Share
- Audio files
- Stems themselves
- Copyrighted content
- Pirated material

## Future Enhancements

### v2.1 - Advanced Mixing
- Per-stem compression
- Per-stem reverb/delay
- Automation (volume changes over time)
- Crossfades between sections

### v2.2 - Community Platform
- Remix marketplace
- Creator profiles
- Remix discovery
- Ratings and reviews

### v3.0 - AI Enhancement
- AI-suggested remixes
- Genre conversion (rock → jazz)
- Stem quality improvement
- Auto-mastering

## Resources

- **Full Vision**: See `STEM_MIXING_VISION.md`
- **Roadmap**: See `ROADMAP.md` v2.0 section
- **Architecture**: See `library.py` stem_settings
- **Examples**: See `examples/remixes/` (coming soon)

---

**Questions?** Check the [FAQ](FAQ.md) or open an issue on GitHub!
