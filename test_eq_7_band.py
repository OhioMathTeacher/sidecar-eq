#!/usr/bin/env python3
"""
Test EQ with 7-band configuration
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from sidecar_eq.analyzer import AudioAnalyzer
import numpy as np

def test_7_band_eq():
    """Test that analyzer produces 7 EQ bands matching the UI."""
    
    analyzer = AudioAnalyzer()
    
    # Verify we have exactly 7 bands
    print(f"EQ Bands: {analyzer.EQ_BANDS}")
    print(f"Number of bands: {len(analyzer.EQ_BANDS)}")
    
    # Expected frequencies matching the UI labels
    expected_bands = [60, 150, 400, 1000, 2400, 6000, 15000]
    
    if analyzer.EQ_BANDS == expected_bands:
        print("✅ EQ bands match UI frequencies")
    else:
        print(f"❌ EQ bands mismatch. Expected: {expected_bands}, Got: {analyzer.EQ_BANDS}")
    
    # Create test audio to verify analysis output
    duration = 2.0  # seconds
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Create a test signal with energy in different frequency bands
    test_audio = np.zeros_like(t)
    
    # Add energy at each EQ band frequency
    for freq in analyzer.EQ_BANDS:
        # Add a sine wave at each frequency
        amplitude = 0.1  # Keep it quiet
        test_audio += amplitude * np.sin(2 * np.pi * freq * t)
    
    print(f"\nTest audio: {len(test_audio)} samples at {sample_rate} Hz")
    
    # Save test audio to file and analyze
    try:
        import tempfile
        import soundfile as sf
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            sf.write(tmp.name, test_audio, sample_rate)
            temp_file = tmp.name
        
        result = analyzer.analyze_file(temp_file)
        eq_settings = result.get('eq_settings', [])
        
        # Clean up
        os.unlink(temp_file)
        
        print(f"EQ Settings returned: {len(eq_settings)} values")
        print(f"EQ Values: {eq_settings}")
        
        if len(eq_settings) == 7:
            print("✅ Analyzer returns exactly 7 EQ band values")
            
            # Print frequency labels with their suggested adjustments
            for freq, adjustment in zip(analyzer.EQ_BANDS, eq_settings):
                if freq >= 1000:
                    freq_label = f"{freq//1000}kHz" if freq % 1000 == 0 else f"{freq/1000:.1f}kHz"
                else:
                    freq_label = f"{freq}Hz"
                print(f"  {freq_label:>6s}: {adjustment:+4.1f} dB")
        else:
            print(f"❌ Expected 7 EQ values, got {len(eq_settings)}")
            
        return len(eq_settings) == 7
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing 7-band EQ configuration...")
    success = test_7_band_eq()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")