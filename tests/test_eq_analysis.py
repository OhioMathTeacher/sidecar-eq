#!/usr/bin/env python3

"""
Test EQ dial functionality and spectral analysis integration
"""

import sys
import tempfile
import os
from pathlib import Path

# Add sidecar_eq to path
sys.path.insert(0, '/Users/todd/sidecar-eq')

def test_eq_analysis():
    print("=== Testing EQ Analysis & Suggested Settings ===")
    
    # Test the analyzer directly
    try:
        from sidecar_eq.analyzer import analyze
        print("\n1. Testing analyzer import... ✅")
    except Exception as e:
        print(f"\n1. Analyzer import failed: {e}")
        return

    # Create a simple test audio file (sine wave)
    print("\n2. Creating test audio file...")
    try:
        import numpy as np
        import soundfile as sf
        
        # Generate a 2-second sine wave at 440 Hz (A4) with some harmonics
        sample_rate = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # Mix of fundamental + harmonics (bass-heavy example)
        fundamental = np.sin(2 * np.pi * 220 * t) * 0.5  # A3 (lower)
        harmonic2 = np.sin(2 * np.pi * 440 * t) * 0.3    # A4 
        harmonic3 = np.sin(2 * np.pi * 880 * t) * 0.1    # A5 (higher)
        
        # Create bass-heavy audio
        audio = fundamental + harmonic2 + harmonic3
        audio = audio / np.max(np.abs(audio)) * 0.8  # Normalize
        
        # Save temporary test file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            sf.write(tmp.name, audio, sample_rate)
            test_file = tmp.name
            
        print(f"   Created test file: {test_file}")
        
    except Exception as e:
        print(f"   Failed to create test audio: {e}")
        return

    # Test analysis
    print("\n3. Running spectral analysis...")
    try:
        result = analyze(test_file)
        print("   Analysis completed ✅")
        print(f"   Frequency bands: {result.get('bands_hz', [])}")
        print(f"   Suggested EQ gains: {result.get('gains_db', [])}")
        print(f"   Preamp: {result.get('preamp_db', 0)}dB")
        
        if 'analysis_data' in result:
            analysis = result['analysis_data']
            print(f"   Bass energy: {analysis.get('bass_energy', 0):.2f}")
            print(f"   Treble energy: {analysis.get('treble_energy', 0):.2f}")
            print(f"   Peak frequency: {analysis.get('peak_frequency', 0):.1f}Hz")
            print(f"   Suggested volume: {analysis.get('suggested_volume', 70)}")
            print(f"   Loudness: {analysis.get('loudness_lufs', -23):.1f} LUFS")
            
    except Exception as e:
        print(f"   Analysis failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up test file
        try:
            os.unlink(test_file)
        except:
            pass

    # Test with a different frequency content (treble-heavy)
    print("\n4. Testing treble-heavy audio...")
    try:
        # Generate treble-heavy audio
        t = np.linspace(0, duration, int(sample_rate * duration))
        high_freq1 = np.sin(2 * np.pi * 4000 * t) * 0.4   # 4kHz
        high_freq2 = np.sin(2 * np.pi * 8000 * t) * 0.3   # 8kHz  
        high_freq3 = np.sin(2 * np.pi * 2000 * t) * 0.2   # 2kHz
        
        audio = high_freq1 + high_freq2 + high_freq3
        audio = audio / np.max(np.abs(audio)) * 0.8
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            sf.write(tmp.name, audio, sample_rate)
            test_file2 = tmp.name
            
        result2 = analyze(test_file2)
        analysis2 = result2.get('analysis_data', {})
        
        print(f"   Treble-heavy analysis:")
        print(f"   Bass energy: {analysis2.get('bass_energy', 0):.2f}")
        print(f"   Treble energy: {analysis2.get('treble_energy', 0):.2f}")
        print(f"   EQ suggestions: {result2.get('gains_db', [])[::2]}")  # Every other band
        
        os.unlink(test_file2)
        
    except Exception as e:
        print(f"   Treble test failed: {e}")

    print("\n5. Testing with real audio files...")
    # Look for J. Geils Band files to test
    possible_paths = [
        "/Users/todd/Music/J Geils Band Monkey Island.mp4",
        "/Users/todd/Music/J Geils Band Self Titled.mp4", 
        "/Users/todd/Desktop/J Geils Band Monkey Island.mp4",
        "/Users/todd/Desktop/J Geils Band Self Titled.mp4"
    ]
    
    real_files = [p for p in possible_paths if Path(p).exists()]
    if real_files:
        for audio_path in real_files[:1]:  # Test first file found
            print(f"   Analyzing real file: {Path(audio_path).name}")
            try:
                result = analyze(audio_path)
                analysis = result.get('analysis_data', {})
                eq_gains = result.get('gains_db', [])
                
                print(f"   Real audio EQ suggestions: {[f'{g:+d}' for g in eq_gains[:5]]}... (showing first 5 bands)")
                print(f"   Bass/Treble balance: {analysis.get('bass_energy', 0):.2f}/{analysis.get('treble_energy', 0):.2f}")
                print(f"   Suggested volume: {analysis.get('suggested_volume', 70)}")
                
            except Exception as e:
                print(f"   Real file analysis failed: {e}")
    else:
        print("   No J. Geils Band files found for testing")

    print("\n✅ EQ Analysis tests completed!")

if __name__ == "__main__":
    test_eq_analysis()