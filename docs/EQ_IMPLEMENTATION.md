# EQ Audio Processing - Implementation Research

**Created**: October 19, 2025  
**Status**: Research Phase  
**Goal**: Implement real-time 7-band parametric EQ

---

## 🎯 Current Situation

### What We Have
- ✅ Beautiful UI with 7 EQ sliders (60Hz, 150Hz, 400Hz, 1kHz, 2.4kHz, 6kHz, 15kHz)
- ✅ Settings save/load perfectly
- ✅ Qt-based player (`QMediaPlayer` + `QAudioOutput`)
- ✅ Volume control works

### What's Missing
- ❌ **EQ sliders don't affect audio** - `set_eq_values()` is a placeholder
- ❌ No audio DSP pipeline
- ❌ No real-time filtering

### The Challenge
`QMediaPlayer` is a high-level abstraction that doesn't expose raw audio buffers for processing. We need to:
1. Get raw audio data
2. Apply 7-band parametric EQ filtering
3. Output processed audio
4. Do it in real-time (<10ms latency)

---

## 🔧 Implementation Options

### Option A: PyAudio + scipy (RECOMMENDED ⭐)

**Architecture**:
```
Audio File
    ↓
Decode (librosa/soundfile)
    ↓
PyAudio Stream
    ↓
scipy Biquad Filters (7 bands)
    ↓
Output Buffer
    ↓
Speaker/Headphones
```

**Pros**:
- ✅ Full control over audio pipeline
- ✅ Pure Python (easy debugging)
- ✅ scipy has excellent filter design (`scipy.signal.iirpeak`, `iirnotch`)
- ✅ Can add more effects later (compressor, limiter)
- ✅ Works on all platforms (PyAudio is cross-platform)
- ✅ Low latency possible with small buffer sizes

**Cons**:
- ⚠️ Need to replace QMediaPlayer entirely
- ⚠️ Manual playback state management
- ⚠️ Threading complexity (Qt event loop + audio callback)
- ⚠️ ~500-800 lines of code
- ⚠️ May have issues with some formats (need ffmpeg decoding)

**Libraries Needed**:
```bash
pip install pyaudio scipy soundfile
```

**Code Sketch**:
```python
import pyaudio
import numpy as np
from scipy import signal

class AudioProcessor:
    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.eq_filters = self._design_eq_filters()
        
    def _design_eq_filters(self):
        """Design 7 biquad peaking filters"""
        fs = 44100  # Sample rate
        bands = [60, 150, 400, 1000, 2400, 6000, 15000]
        Q = 1.0  # Bandwidth
        
        filters = []
        for freq in bands:
            # Peaking EQ filter (boost/cut)
            b, a = signal.iirpeak(freq, Q, fs)
            filters.append((b, a))
        return filters
    
    def process_buffer(self, audio_data, eq_gains):
        """Apply EQ to audio buffer"""
        # Convert to numpy array
        samples = np.frombuffer(audio_data, dtype=np.float32)
        
        # Apply each band
        for i, (b, a) in enumerate(self.eq_filters):
            gain_db = eq_gains[i]
            gain_linear = 10 ** (gain_db / 20)
            
            # Apply filter with gain
            samples = signal.lfilter(b * gain_linear, a, samples)
        
        return samples.tobytes()
```

**Next Steps**:
1. [ ] Research PyAudio + Qt integration (threading model)
2. [ ] Prototype simple 1-band EQ
3. [ ] Test latency and CPU usage
4. [ ] Design proper filter bank

---

### Option B: FFmpeg Audio Filters

**Architecture**:
```
Audio File
    ↓
FFmpeg Process
    ↓
Audio Filter Graph (equalizer=f=60:t=peak:g=+3)
    ↓
Pipe to PyAudio/Qt
    ↓
Speaker/Headphones
```

**Pros**:
- ✅ Professional-grade DSP
- ✅ Already using FFmpeg for video extraction
- ✅ Powerful filter language
- ✅ Excellent format support

**Cons**:
- ⚠️ Complex filter syntax
- ⚠️ Harder to debug (subprocess communication)
- ⚠️ Need to rebuild pipeline on EQ change
- ⚠️ May have latency issues
- ⚠️ Difficult to integrate with Qt signals/slots

**Filter Command Example**:
```bash
ffmpeg -i input.mp3 \
  -af "equalizer=f=60:t=peak:w=100:g=+3,\
       equalizer=f=150:t=peak:w=100:g=+2,\
       equalizer=f=400:t=peak:w=100:g=0,\
       equalizer=f=1000:t=peak:w=100:g=-1,\
       equalizer=f=2400:t=peak:w=100:g=+1,\
       equalizer=f=6000:t=peak:w=100:g=+2,\
       equalizer=f=15000:t=peak:w=100:g=-2" \
  -f s16le pipe:1
```

**Next Steps**:
1. [ ] Test FFmpeg filter graph with dynamic parameters
2. [ ] Measure latency
3. [ ] Figure out how to update filters in real-time

---

### Option C: Qt Multimedia Audio I/O

**Architecture**:
```
QAudioDecoder
    ↓
QAudioBuffer (raw PCM)
    ↓
Custom DSP Processing
    ↓
QAudioSink
    ↓
Speaker/Headphones
```

**Pros**:
- ✅ Native Qt solution
- ✅ Integrated with existing code
- ✅ No additional dependencies

**Cons**:
- ⚠️ Limited documentation
- ⚠️ Less flexible than PyAudio
- ⚠️ Platform-specific issues
- ⚠️ Still need to implement DSP filters manually

**Next Steps**:
1. [ ] Research QAudioDecoder API
2. [ ] Test buffer processing
3. [ ] Verify platform support

---

## 🎚️ EQ Filter Design

### Parametric EQ Basics

Each band needs:
- **Center Frequency**: 60Hz, 150Hz, 400Hz, 1kHz, 2.4kHz, 6kHz, 15kHz
- **Bandwidth (Q)**: How wide the boost/cut affects (typically 0.7-1.4)
- **Gain**: -12dB to +12dB (our UI range)

### Filter Types

**Peaking EQ** (most bands):
- Boosts or cuts a specific frequency
- Bell-shaped curve
- scipy: `signal.iirpeak()` or `signal.butter()` with modifications

**High-Pass** (optional for 60Hz):
- Cuts everything below frequency
- Useful for rumble removal

**Low-Pass** (optional for 15kHz):
- Cuts everything above frequency
- Useful for brightness control

### Implementation Approaches

#### Approach 1: Biquad Cascade (Recommended)
```python
# Each band is a 2nd-order IIR filter (biquad)
# 7 bands = 7 cascaded biquads
# Very efficient, low CPU

for band in eq_bands:
    audio = apply_biquad(audio, band.b, band.a)
```

#### Approach 2: FFT-based Filtering
```python
# Transform to frequency domain
fft = np.fft.rfft(audio)

# Apply gain at each frequency
for band in eq_bands:
    freq_range = get_freq_range(band.center, band.width)
    fft[freq_range] *= band.gain

# Transform back
audio = np.fft.irfft(fft)
```

**Pros**: Very flexible, perfect frequency control  
**Cons**: Higher latency, more CPU intensive

---

## 🧵 Threading Architecture

### Challenge: Qt Event Loop + Audio Callback

Qt runs in main thread, but audio needs dedicated thread for low latency.

### Solution: Producer-Consumer Pattern

```python
# Audio Thread (high priority)
def audio_callback(in_data, frame_count, time_info, status):
    # Get EQ parameters from thread-safe queue
    eq_params = param_queue.get_nowait()
    
    # Process audio
    output = process_audio(in_data, eq_params)
    
    return (output, pyaudio.paContinue)

# Qt Main Thread
def on_eq_slider_changed(band, value):
    # Update EQ parameters thread-safely
    eq_params[band] = value
    param_queue.put(eq_params)
```

### Libraries for Thread Safety
- `queue.Queue` - Thread-safe parameter passing
- `threading.Lock` - Protect shared state
- Qt signals for UI updates from audio thread

---

## 📊 Performance Targets

### Latency
- **Target**: <10ms
- **Acceptable**: <20ms
- **Bad**: >50ms (users will notice delay)

**Buffer Size Tradeoff**:
- Smaller buffers = lower latency, higher CPU, more dropouts
- Larger buffers = higher latency, lower CPU, smoother
- Sweet spot: 512-1024 samples @ 44.1kHz = 11-23ms

### CPU Usage
- **Target**: <5% on modern CPU
- **Acceptable**: <15%
- **Bad**: >25% (fans spin up, battery drain)

**Optimization Strategies**:
- Use compiled filters (scipy/numpy are fast)
- Minimize allocations in audio callback
- Pre-compute filter coefficients
- Use SIMD instructions (numpy does this)

---

## 🧪 Testing Plan

### Phase 1: Proof of Concept (1 week)
- [ ] Implement 1-band EQ with PyAudio
- [ ] Verify it actually changes the sound
- [ ] Measure latency and CPU
- [ ] Test on macOS (your platform)

### Phase 2: Full Implementation (1 week)
- [ ] Add remaining 6 bands
- [ ] Integrate with Qt UI (replace QMediaPlayer)
- [ ] Test with various file formats
- [ ] Handle edge cases (very quiet/loud files)

### Phase 3: Polish (3-5 days)
- [ ] Smooth parameter changes (no clicks/pops)
- [ ] Bypass mode (EQ on/off comparison)
- [ ] Preset management
- [ ] Performance optimization

### Phase 4: Cross-Platform Testing (1 week)
- [ ] Test on Windows
- [ ] Test on Linux
- [ ] Fix platform-specific issues
- [ ] Document platform differences

---

## 🎯 Recommendation: Start with PyAudio

**Why PyAudio + scipy**:
1. Full control over pipeline
2. Proven technology (used in Audacity, etc.)
3. Easy to debug
4. Can add more effects later (v2.0 VST support builds on this)
5. Platform-independent

**Migration Path**:
1. Keep `Player` class interface the same
2. Replace internal implementation
3. Gradual rollout (feature flag?)
4. Fall back to QMediaPlayer if PyAudio fails

**Estimated Timeline**:
- Week 1: Research + prototype (1 band)
- Week 2: Full 7-band implementation
- Week 3: Integration + testing
- Week 4: Bug fixes + polish

---

## 📚 Resources

### PyAudio Documentation
- https://people.csail.mit.edu/hubert/pyaudio/docs/
- Tutorial: Real-time audio processing
- Examples: Streaming audio

### scipy Signal Processing
- https://docs.scipy.org/doc/scipy/reference/signal.html
- `signal.iirpeak()` - Peaking EQ filter design
- `signal.lfilter()` - Apply IIR filter
- `signal.freqz()` - Plot frequency response

### Audio DSP Theory
- "The Scientist and Engineer's Guide to DSP" (free online)
- "Designing Audio Effect Plugins in C++" (Pirkle)
- "Introduction to Digital Filters" (Julius O. Smith)

### Existing Python EQ Implementations
- `pedalboard` by Spotify (audio effects library)
- `librosa` (music analysis, has filtering)
- `pyo` (dedicated audio DSP library)

---

## 🚀 Next Action Items

1. **Install Dependencies**:
   ```bash
   pip install pyaudio scipy soundfile
   ```

2. **Create Prototype Script**:
   - Load audio file
   - Apply simple 1-band EQ
   - Play through PyAudio
   - Verify audible change

3. **Measure Baseline**:
   - Latency with no EQ
   - CPU usage
   - Audio quality

4. **Get Approval**:
   - Show prototype to user
   - Confirm approach before full implementation

---

## 💭 Open Questions

1. **Replace QMediaPlayer completely, or layer on top?**
   - Leaning toward: Replace for full control

2. **Sample rate: 44.1kHz or 48kHz?**
   - Recommendation: 44.1kHz (CD quality, widely supported)

3. **Bit depth: 16-bit or 32-bit float?**
   - Recommendation: 32-bit float internally (scipy default)

4. **Handle format conversion where?**
   - Use `soundfile` or `librosa` for decoding

5. **What if PyAudio installation fails?**
   - Fallback to QMediaPlayer (no EQ, but app still works)

---

*Ready to build a real EQ! Let's make some noise! 🎛️*
