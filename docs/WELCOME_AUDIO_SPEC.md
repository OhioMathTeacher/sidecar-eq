# Welcome Audio Clip Specification

## File Details
- **Filename**: `introduction.mp3`
- **Location**: `/Users/todd/sidecar-eq/sidecar_eq/introduction.mp3`
- **Total Duration**: ~3 seconds
- **Format**: MP3 (128-320 kbps recommended)

## Audio Script - Dual-Voice Tagline

### Sound Effects & Voice Timeline

| Time Range | Element | Description |
|------------|---------|-------------|
| **0.00–0.40s** | SFX | Powerful cinematic whoosh, then fast riser into tag |
| **0.40–1.20s** | Male Voice | "Sidecar EQ." (gravelly, assertive tone) |
| **1.20–2.60s** | Female Voice | "The future of music starts here." (bright, confident tone) |
| **2.60–3.00s** | SFX | Analog tape click with subtle reverb tail |

## Voice Characteristics

### Male Voice (Line 1)
- **Tone**: Gravelly, assertive
- **Line**: "Sidecar EQ."
- **Duration**: ~0.8 seconds
- **Style**: Professional, authoritative, deep

### Female Voice (Line 2)
- **Tone**: Bright, confident
- **Line**: "The future of music starts here."
- **Duration**: ~1.4 seconds
- **Style**: Energetic, optimistic, clear

## Sound Design Elements

### Opening (0.00–0.40s)
- Cinematic whoosh (creates anticipation)
- Fast riser building tension
- Should feel powerful and modern

### Closing (2.60–3.00s)
- Analog tape click (nostalgic audio tech reference)
- Subtle reverb tail (spacious, professional)
- Clean fadeout

## Production Notes

### Audio Quality
- Sample rate: 44.1 kHz or 48 kHz
- Bit depth: 16-bit minimum
- No clipping or distortion
- Professional mixing with clear separation between voices and SFX

### Balance
- Voices should be clearly intelligible over SFX
- SFX provides atmosphere but doesn't overpower
- Equal volume balance between male and female voices
- Smooth transitions between elements

### Mood
- Professional yet approachable
- Modern and forward-thinking
- Confident without being arrogant
- Exciting without being overwhelming

## Technical Implementation

### When This Plays
The audio automatically plays in these scenarios:
1. **First Launch**: When app starts with no saved queue
2. **Empty Queue**: When user deletes all tracks from the queue
3. **Load Failure**: When saved queue fails to load

### Behavior
- Track appears in queue as: "Welcome to SideCarAI" by "SideCarAI Team"
- Album: "System Audio"
- Can be deleted like any other track (will reload if queue becomes empty again)
- Play count and rating are tracked normally

## Fallback Behavior

Until `introduction.mp3` is created, the system uses:
- **Temporary**: `MLKDream_64kb.mp3` 
- **Placeholder**: Text entry if no audio files exist

## Voice Talent Suggestions

### Option 1: Professional Voice Actors
- Fiverr, Voices.com, or Voice123
- Search for: "gravelly male voiceover" + "bright female voiceover"
- Budget: ~$50-100 for both voices

### Option 2: AI Voice Generation
- ElevenLabs (high quality, natural sounding)
- Play.ht or Murf.ai
- Settings: Adjust tone, pace, and emotion

### Option 3: Text-to-Speech (Quick Prototype)
- macOS `say` command for testing
- Lower quality but immediate

## SFX Sources

### Recommended Libraries
- **Epidemic Sound**: Cinematic whooshes, risers
- **Freesound.org**: Free tape clicks, analog sounds
- **Adobe Stock Audio**: Professional production elements
- **Splice Sounds**: Modern production SFX

### DIY Options
- Create whoosh with synthesizer (long reverb + pitch automation)
- Record actual tape machine for authentic click
- Layer multiple elements for richness

## Production Checklist

- [ ] Record/generate male voice: "Sidecar EQ."
- [ ] Record/generate female voice: "The future of music starts here."
- [ ] Source or create opening whoosh/riser SFX
- [ ] Source or create closing tape click/reverb SFX
- [ ] Import all elements into DAW (Logic, Ableton, Audacity, etc.)
- [ ] Arrange on timeline per specification
- [ ] Mix: balance levels, add compression if needed
- [ ] Master: normalize to -1dB peak, add subtle limiting
- [ ] Export as MP3 (320 kbps recommended)
- [ ] Test: Place in `sidecar_eq/` folder and run app
- [ ] Verify: Check audio quality, timing, and overall impact

## Alternative Script Ideas (Future)

If you want to iterate on the script later:

### Option A (More Technical)
- "Sidecar EQ. Master your sound."

### Option B (More Inspiring)  
- "Sidecar EQ. Where music lives."

### Option C (More Direct)
- "Welcome to Sidecar EQ. Your music, elevated."

---

**Note**: The current implementation expects the file at:
```
/Users/todd/sidecar-eq/sidecar_eq/introduction.mp3
```

Once created, the app will automatically use it!
