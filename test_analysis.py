#!/usr/bin/env python3
"""
Test script for the enhanced audio analysis system.
Tests both spectral analysis and loudness calculation.
"""

import numpy as np
import tempfile
import os
from pathlib import Path

def create_test_audio_file(filename: str, duration: float = 2.0, sample_rate: int = 22050):
    """Create a test audio file with known characteristics."""
    try:
        import soundfile as sf
        
        # Generate test signal: mix of frequencies
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        # Create a signal with bass (100Hz), midrange (1kHz), and treble (8kHz)
        bass = 0.3 * np.sin(2 * np.pi * 100 * t)
        mid = 0.4 * np.sin(2 * np.pi * 1000 * t) 
        treble = 0.2 * np.sin(2 * np.pi * 8000 * t)
        
        # Add some noise for realism
        noise = 0.05 * np.random.randn(len(t))
        
        signal = bass + mid + treble + noise
        
        # Normalize to reasonable level (-12 dB peak)
        signal = signal / np.max(np.abs(signal)) * 0.25
        
        # Save as WAV file
        sf.write(filename, signal, sample_rate)
        print(f"Created test audio: {filename}")
        return True
        
    except ImportError:
        print("soundfile not available - using basic numpy approach")
        # Basic approach without soundfile
        return False

def test_analysis_without_file():
    """Test the analysis functions directly with synthetic data."""
    try:
        from sidecar_eq.analyzer import AudioAnalyzer
        
        analyzer = AudioAnalyzer()
        
        # Create synthetic audio data for testing
        sample_rate = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        # Test signal with known characteristics
        bass_heavy = 0.8 * np.sin(2 * np.pi * 80 * t) + 0.2 * np.sin(2 * np.pi * 1000 * t)
        treble_heavy = 0.2 * np.sin(2 * np.pi * 100 * t) + 0.8 * np.sin(2 * np.pi * 8000 * t)
        
        print("Testing bass-heavy signal:")
        # Test loudness calculation directly
        loudness_data = analyzer._calculate_loudness_metrics(bass_heavy, sample_rate)
        print(f"  RMS: {loudness_data['rms_db']:.1f} dB")
        print(f"  Peak: {loudness_data['peak_db']:.1f} dB") 
        print(f"  LUFS estimate: {loudness_data['loudness_lufs']:.1f}")
        print(f"  Suggested volume: {loudness_data['suggested_volume']}")
        
        print("\nTesting treble-heavy signal:")
        loudness_data2 = analyzer._calculate_loudness_metrics(treble_heavy, sample_rate)
        print(f"  RMS: {loudness_data2['rms_db']:.1f} dB")
        print(f"  Peak: {loudness_data2['peak_db']:.1f} dB")
        print(f"  LUFS estimate: {loudness_data2['loudness_lufs']:.1f}")
        print(f"  Suggested volume: {loudness_data2['suggested_volume']}")
        
        return True
        
    except Exception as e:
        print(f"Analysis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=== Enhanced Audio Analysis Test ===\n")
    
    # Test 1: Direct analysis functions
    print("1. Testing analysis functions with synthetic data...")
    if test_analysis_without_file():
        print("✓ Analysis functions working correctly\n")
    else:
        print("✗ Analysis test failed\n")
        return
    
    # Test 2: Try to create and analyze a real file
    print("2. Testing with temporary audio file...")
    try:
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp_path = tmp.name
        
        if create_test_audio_file(tmp_path):
            try:
                from sidecar_eq.analyzer import analyze
                print(f"Analyzing: {tmp_path}")
                result = analyze(tmp_path)
                
                if result:
                    analysis_data = result.get('analysis_data', {})
                    eq_data = result.get('eq_data', {})
                    
                    print("Analysis Results:")
                    print(f"  EQ suggestions: {len(eq_data)} bands")
                    if 'loudness_lufs' in analysis_data:
                        print(f"  Loudness: {analysis_data['loudness_lufs']:.1f} LUFS")
                        print(f"  Suggested volume: {analysis_data['suggested_volume']}")
                    print("✓ File analysis working correctly")
                else:
                    print("✗ File analysis returned no results")
                    
            except Exception as e:
                print(f"✗ File analysis failed: {e}")
            
            # Cleanup
            os.unlink(tmp_path)
        else:
            print("Could not create test audio file")
            
    except Exception as e:
        print(f"Test file creation failed: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()