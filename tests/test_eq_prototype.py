#!/usr/bin/env python3
"""
EQ Audio Processing Prototype
==============================

This script tests basic EQ functionality using PyAudio + scipy.

Tests:
1. Load audio file
2. Apply single-band parametric EQ (1kHz boost/cut)
3. Play through PyAudio
4. Verify audible difference

Usage:
    python tests/test_eq_prototype.py [audio_file.wav]
"""

import sys
import argparse
import numpy as np
from pathlib import Path

# Test if dependencies are available
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    print("⚠️  PyAudio not installed. Run: pip install pyaudio")

try:
    from scipy import signal
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("⚠️  scipy not installed. Run: pip install scipy")

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False
    print("⚠️  soundfile not installed. Run: pip install soundfile")


def design_peaking_eq(center_freq, gain_db, q=1.0, fs=44100):
    """Design a parametric peaking EQ filter.
    
    Args:
        center_freq: Center frequency in Hz (e.g., 1000 for 1kHz)
        gain_db: Gain in dB (positive = boost, negative = cut)
        q: Q factor (bandwidth), typically 0.7-1.4
        fs: Sample rate in Hz
    
    Returns:
        b, a: Filter coefficients for scipy.signal.lfilter
    """
    if not SCIPY_AVAILABLE:
        raise ImportError("scipy is required for filter design")
    
    # Convert gain from dB to linear
    A = 10 ** (gain_db / 40)  # Using /40 for peaking filter
    
    # Calculate angular frequency
    w0 = 2 * np.pi * center_freq / fs
    
    # Calculate alpha (bandwidth parameter)
    alpha = np.sin(w0) / (2 * q)
    
    # Peaking EQ filter coefficients
    b0 = 1 + alpha * A
    b1 = -2 * np.cos(w0)
    b2 = 1 - alpha * A
    a0 = 1 + alpha / A
    a1 = -2 * np.cos(w0)
    a2 = 1 - alpha / A
    
    # Normalize by a0
    b = np.array([b0, b1, b2]) / a0
    a = np.array([1, a1, a2]) / a0
    
    return b, a


def apply_eq(audio, b, a):
    """Apply EQ filter to audio signal.
    
    Args:
        audio: Audio samples (numpy array)
        b, a: Filter coefficients from design_peaking_eq
    
    Returns:
        Filtered audio (same shape as input)
    """
    if not SCIPY_AVAILABLE:
        raise ImportError("scipy is required for filtering")
    
    # Handle stereo (apply to each channel)
    if audio.ndim == 2:
        filtered = np.zeros_like(audio)
        for ch in range(audio.shape[1]):
            filtered[:, ch] = signal.lfilter(b, a, audio[:, ch])
        return filtered
    else:
        # Mono
        return signal.lfilter(b, a, audio)


def play_audio(audio, samplerate, title="Playing..."):
    """Play audio through PyAudio.
    
    Args:
        audio: Audio samples (numpy array, float32, -1.0 to 1.0)
        samplerate: Sample rate in Hz
        title: Display title
    """
    if not PYAUDIO_AVAILABLE:
        print("❌ Cannot play: PyAudio not installed")
        return
    
    print(f"\n🔊 {title}")
    print(f"   Sample rate: {samplerate} Hz")
    print(f"   Duration: {len(audio) / samplerate:.1f} seconds")
    print(f"   Channels: {audio.shape[1] if audio.ndim == 2 else 1}")
    
    # Normalize to prevent clipping
    peak = np.abs(audio).max()
    if peak > 1.0:
        normalized_audio = audio / peak
        print(f"   ⚠️  Normalized (peak was {peak:.2f}, reduced by {20*np.log10(peak):.1f}dB)")
    else:
        normalized_audio = audio
    
    print("\n   Press Ctrl+C to stop...")
    
    # Initialize PyAudio
    p = pyaudio.PyAudio()
    
    # Determine format
    channels = normalized_audio.shape[1] if normalized_audio.ndim == 2 else 1
    
    # Convert to int16 for playback
    audio_int16 = (normalized_audio * 32767).astype(np.int16)
    
    # Open stream
    stream = p.open(
        format=pyaudio.paInt16,
        channels=channels,
        rate=samplerate,
        output=True,
        frames_per_buffer=1024
    )
    
    try:
        # Play audio
        stream.write(audio_int16.tobytes())
        stream.stop_stream()
    except KeyboardInterrupt:
        print("\n   Stopped by user")
    finally:
        stream.close()
        p.terminate()


def load_audio(filepath):
    """Load audio file using soundfile.
    
    Args:
        filepath: Path to audio file
    
    Returns:
        audio: Audio samples (numpy array, float32)
        samplerate: Sample rate in Hz
    """
    if not SOUNDFILE_AVAILABLE:
        raise ImportError("soundfile is required for loading audio")
    
    print(f"\n📂 Loading: {filepath}")
    audio, samplerate = sf.read(filepath, dtype='float32')
    print(f"   ✅ Loaded {len(audio)} samples at {samplerate} Hz")
    
    return audio, samplerate


def main():
    parser = argparse.ArgumentParser(
        description='Test EQ audio processing with PyAudio + scipy'
    )
    parser.add_argument(
        'audio_file',
        nargs='?',
        default='assets/test_balanced.wav',
        help='Audio file to process (default: assets/test_balanced.wav)'
    )
    parser.add_argument(
        '--freq',
        type=float,
        default=1000,
        help='EQ center frequency in Hz (default: 1000)'
    )
    parser.add_argument(
        '--gain',
        type=float,
        default=12,
        help='EQ gain in dB (default: +12, try -12 for cut)'
    )
    parser.add_argument(
        '--q',
        type=float,
        default=1.0,
        help='Q factor / bandwidth (default: 1.0)'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("EQ Audio Processing Prototype")
    print("=" * 70)
    
    # Check dependencies
    if not all([PYAUDIO_AVAILABLE, SCIPY_AVAILABLE, SOUNDFILE_AVAILABLE]):
        print("\n❌ Missing dependencies. Please install:")
        print("   pip install pyaudio scipy soundfile")
        return 1
    
    # Load audio file
    try:
        audio, samplerate = load_audio(args.audio_file)
    except Exception as e:
        print(f"❌ Failed to load audio: {e}")
        return 1
    
    # Design EQ filter
    print(f"\n🎛️  Designing EQ filter:")
    print(f"   Center Frequency: {args.freq} Hz")
    print(f"   Gain: {args.gain:+.1f} dB")
    print(f"   Q Factor: {args.q}")
    
    try:
        b, a = design_peaking_eq(args.freq, args.gain, args.q, samplerate)
        print(f"   ✅ Filter designed successfully")
    except Exception as e:
        print(f"❌ Failed to design filter: {e}")
        return 1
    
    # Apply EQ
    print(f"\n⚙️  Applying EQ filter...")
    try:
        audio_eq = apply_eq(audio, b, a)
        print(f"   ✅ EQ applied successfully")
    except Exception as e:
        print(f"❌ Failed to apply EQ: {e}")
        return 1
    
    # Play comparison
    print("\n" + "=" * 70)
    print("PLAYBACK TEST")
    print("=" * 70)
    print("\nYou should hear the difference between original and EQ'd audio.")
    print("Listen for changes at {}Hz ({}dB {})".format(
        args.freq,
        abs(args.gain),
        "boost" if args.gain > 0 else "cut"
    ))
    
    # Play original
    input("\n▶️  Press Enter to play ORIGINAL (no EQ)...")
    try:
        play_audio(audio, samplerate, "ORIGINAL (No EQ)")
    except Exception as e:
        print(f"❌ Playback failed: {e}")
        return 1
    
    # Play with EQ
    input("\n▶️  Press Enter to play WITH EQ...")
    try:
        play_audio(audio_eq, samplerate, f"WITH EQ ({args.gain:+.1f}dB @ {args.freq}Hz)")
    except Exception as e:
        print(f"❌ Playback failed: {e}")
        return 1
    
    # Success!
    print("\n" + "=" * 70)
    print("✅ SUCCESS! EQ prototype working!")
    print("=" * 70)
    print("\n💡 Next steps:")
    print("   1. Try different frequencies: --freq 60, --freq 6000")
    print("   2. Try boost and cut: --gain +12, --gain -12")
    print("   3. Try different Q values: --q 0.7, --q 2.0")
    print("   4. Try different audio files")
    print("\n   Example: python tests/test_eq_prototype.py --freq 60 --gain +12")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
