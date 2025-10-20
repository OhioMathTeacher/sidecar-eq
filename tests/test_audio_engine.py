#!/usr/bin/env python3
"""
Test AudioEngine with EQ
=========================

Quick test of the AudioEngine class with real-time EQ.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidecar_eq.audio_engine import AudioEngine, EQ_BANDS


def test_basic_playback():
    """Test basic playback without EQ."""
    print("=" * 70)
    print("Test 1: Basic Playback (No EQ)")
    print("=" * 70)
    
    engine = AudioEngine()
    
    # Load test file
    if not engine.load_file("assets/test_balanced.wav"):
        return False
    
    # Play
    print("\n▶️  Playing for 3 seconds...")
    engine.play()
    time.sleep(3)
    
    # Pause
    print("⏸️  Paused")
    engine.pause()
    time.sleep(1)
    
    # Resume
    print("▶️  Resuming...")
    engine.play()
    time.sleep(2)
    
    # Stop
    engine.stop()
    print("⏹️  Stopped\n")
    
    engine.cleanup()
    return True


def test_eq_processing():
    """Test EQ processing."""
    print("=" * 70)
    print("Test 2: EQ Processing")
    print("=" * 70)
    
    engine = AudioEngine()
    
    # Load test file
    if not engine.load_file("assets/test_balanced.wav"):
        return False
    
    print("\n🎛️  EQ Bands:", [f"{freq}Hz" for freq in EQ_BANDS])
    
    # Test each band
    for i, freq in enumerate(EQ_BANDS):
        print(f"\n▶️  Band {i+1}: {freq}Hz boosted +12dB")
        engine.set_eq_band(i, 12.0)
        engine.play()
        time.sleep(2)
        engine.stop()
        
        # Reset
        engine.set_eq_band(i, 0.0)
        engine.seek(0)
    
    print("\n✅ All bands tested\n")
    
    engine.cleanup()
    return True


def test_volume_control():
    """Test volume control."""
    print("=" * 70)
    print("Test 3: Volume Control")
    print("=" * 70)
    
    engine = AudioEngine()
    
    # Load test file
    if not engine.load_file("assets/test_balanced.wav"):
        return False
    
    # Test volume levels
    for vol in [1.0, 0.5, 0.2, 1.0]:
        print(f"\n▶️  Volume: {int(vol * 100)}%")
        engine.set_volume(vol)
        engine.play()
        time.sleep(2)
        engine.stop()
        engine.seek(0)
    
    print("\n✅ Volume control working\n")
    
    engine.cleanup()
    return True


def test_seeking():
    """Test seeking."""
    print("=" * 70)
    print("Test 4: Seeking")
    print("=" * 70)
    
    engine = AudioEngine()
    
    # Load test file
    if not engine.load_file("assets/test_balanced.wav"):
        return False
    
    duration = engine.get_duration_ms()
    print(f"\nDuration: {duration/1000:.1f}s")
    
    # Seek to different positions
    positions = [0, 2000, 5000, 8000]
    for pos_ms in positions:
        print(f"\n▶️  Seeking to {pos_ms/1000:.1f}s")
        engine.seek(pos_ms)
        engine.play()
        time.sleep(1.5)
        engine.stop()
    
    print("\n✅ Seeking working\n")
    
    engine.cleanup()
    return True


def main():
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  AudioEngine Test Suite".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print("\n")
    
    tests = [
        ("Basic Playback", test_basic_playback),
        ("EQ Processing", test_eq_processing),
        ("Volume Control", test_volume_control),
        ("Seeking", test_seeking),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except KeyboardInterrupt:
            print("\n\n⚠️  Test interrupted by user")
            return 1
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(success for _, success in results)
    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
