#!/usr/bin/env python3

"""
Create a simple test audio file to verify EQ suggestions in the app
"""

import numpy as np
import soundfile as sf
from pathlib import Path

def create_bass_heavy_test():
    """Create a bass-heavy test file to see EQ suggestions."""
    
    sample_rate = 22050
    duration = 10.0  # 10 seconds
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create bass-heavy content
    bass = np.sin(2 * np.pi * 80 * t) * 0.6    # Deep bass
    low_mid = np.sin(2 * np.pi * 200 * t) * 0.4  # Low-mid
    mid = np.sin(2 * np.pi * 800 * t) * 0.2     # Mid (lower)
    
    # Mix and normalize
    audio = bass + low_mid + mid
    audio = audio / np.max(np.abs(audio)) * 0.8
    
    # Save test file
    output_path = Path('/Users/todd/sidecar-eq/test_bass_heavy.wav')
    sf.write(str(output_path), audio, sample_rate)
    print(f"Created bass-heavy test file: {output_path}")
    print("Expected EQ suggestions: Reduce bass frequencies, boost mids/highs")
    return output_path

def create_treble_heavy_test():
    """Create a treble-heavy test file to see EQ suggestions."""
    
    sample_rate = 22050
    duration = 10.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create treble-heavy content
    high1 = np.sin(2 * np.pi * 3000 * t) * 0.5   # High-mid
    high2 = np.sin(2 * np.pi * 6000 * t) * 0.4   # High  
    high3 = np.sin(2 * np.pi * 9000 * t) * 0.3   # Very high
    
    # Mix and normalize
    audio = high1 + high2 + high3
    audio = audio / np.max(np.abs(audio)) * 0.8
    
    # Save test file
    output_path = Path('/Users/todd/sidecar-eq/test_treble_heavy.wav')
    sf.write(str(output_path), audio, sample_rate)
    print(f"Created treble-heavy test file: {output_path}")
    print("Expected EQ suggestions: Reduce high frequencies, boost bass/mids")
    return output_path

def create_balanced_test():
    """Create a well-balanced test file."""
    
    sample_rate = 22050
    duration = 10.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create balanced content across frequency spectrum
    bass = np.sin(2 * np.pi * 100 * t) * 0.3
    low_mid = np.sin(2 * np.pi * 300 * t) * 0.3
    mid = np.sin(2 * np.pi * 1000 * t) * 0.3
    high_mid = np.sin(2 * np.pi * 3000 * t) * 0.3
    high = np.sin(2 * np.pi * 8000 * t) * 0.2
    
    # Mix and normalize
    audio = bass + low_mid + mid + high_mid + high
    audio = audio / np.max(np.abs(audio)) * 0.8
    
    # Save test file
    output_path = Path('/Users/todd/sidecar-eq/test_balanced.wav')
    sf.write(str(output_path), audio, sample_rate)
    print(f"Created balanced test file: {output_path}")
    print("Expected EQ suggestions: Minimal adjustments (close to 0)")
    return output_path

if __name__ == "__main__":
    print("=== Creating Test Audio Files for EQ Testing ===")
    
    try:
        create_bass_heavy_test()
        create_treble_heavy_test()  
        create_balanced_test()
        
        print("\n✅ Test files created successfully!")
        print("\nTo test EQ suggestions:")
        print("1. Open Sidecar EQ app")
        print("2. Add these test files to the queue")
        print("3. Play each file and observe EQ dial positions")
        print("4. The dials should move to suggested positions during analysis")
        
    except Exception as e:
        print(f"Error creating test files: {e}")
        import traceback
        traceback.print_exc()