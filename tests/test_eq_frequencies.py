"""
EQ Frequency Test - Generate test tones to verify EQ bands work correctly
===========================================================================

This generates pure sine waves at each EQ frequency (60, 150, 400, 1000, 2400, 6000, 15000 Hz)
so you can verify that:
1. Boosting 60Hz makes ONLY the 60Hz tone louder
2. Cutting 150Hz makes ONLY the 150Hz tone quieter
3. etc.

Usage:
    python tests/test_eq_frequencies.py
    
Then play the generated test files in SidecarEQ and adjust EQ sliders.
"""

import numpy as np
from pathlib import Path
from pedalboard.io import AudioFile

# EQ bands to test
EQ_BANDS = [60, 150, 400, 1000, 2400, 6000, 15000]

# Audio settings
SAMPLE_RATE = 44100
DURATION = 3.0  # 3 seconds per tone
AMPLITUDE = 0.3  # Reduced volume to prevent clipping


def generate_sine_wave(frequency: float, duration: float, sample_rate: int, amplitude: float = 0.5):
    """Generate a pure sine wave."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # Add fade in/out to prevent clicks
    fade_samples = int(sample_rate * 0.05)  # 50ms fade
    fade_in = np.linspace(0, 1, fade_samples)
    fade_out = np.linspace(1, 0, fade_samples)
    
    wave = amplitude * np.sin(2 * np.pi * frequency * t)
    
    # Apply fades
    wave[:fade_samples] *= fade_in
    wave[-fade_samples:] *= fade_out
    
    return wave


def generate_test_files():
    """Generate test tone files for each EQ band."""
    output_dir = Path("assets/eq_test_tones")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("🎵 Generating EQ test tones...")
    print(f"📁 Output directory: {output_dir}")
    print()
    
    for freq in EQ_BANDS:
        # Generate mono sine wave
        tone = generate_sine_wave(freq, DURATION, SAMPLE_RATE, AMPLITUDE)
        
        # Convert to stereo (duplicate to both channels)
        stereo_tone = np.array([tone, tone])
        
        # Save as WAV file
        output_file = output_dir / f"test_tone_{freq}Hz.wav"
        with AudioFile(str(output_file), 'w', SAMPLE_RATE, num_channels=2) as f:
            f.write(stereo_tone)
        
        print(f"✅ Generated: {output_file.name} ({freq} Hz)")
    
    print()
    print("🎉 Test tones generated successfully!")
    print()
    print("📋 HOW TO TEST:")
    print("1. Open SidecarEQ")
    print(f"2. Add test tone files from: {output_dir}")
    print("3. Play each tone and adjust the corresponding EQ band:")
    print()
    for freq in EQ_BANDS:
        print(f"   • test_tone_{freq}Hz.wav:")
        print(f"     - Boost {freq}Hz slider → tone should get LOUDER")
        print(f"     - Cut {freq}Hz slider → tone should get QUIETER")
        print(f"     - Other sliders should NOT affect this tone")
    print()
    print("⚠️  If you hear changes when moving WRONG sliders, there's a bug!")
    print()
    
    # Also generate a "sweep" file that plays all frequencies
    print("🎵 Generating frequency sweep (all tones in sequence)...")
    all_tones = []
    for freq in EQ_BANDS:
        tone = generate_sine_wave(freq, 2.0, SAMPLE_RATE, AMPLITUDE)
        all_tones.append(tone)
        # Add brief silence between tones
        silence = np.zeros(int(SAMPLE_RATE * 0.5))
        all_tones.append(silence)
    
    sweep = np.concatenate(all_tones)
    stereo_sweep = np.array([sweep, sweep])
    
    sweep_file = output_dir / "eq_frequency_sweep.wav"
    with AudioFile(str(sweep_file), 'w', SAMPLE_RATE, num_channels=2) as f:
        f.write(stereo_sweep)
    
    print(f"✅ Generated: {sweep_file.name}")
    print("   This plays all 7 frequencies in order (60Hz → 15kHz)")
    print("   Listen to identify which frequency is which!")


if __name__ == "__main__":
    generate_test_files()
