#!/usr/bin/env python3
"""
Test the background analysis implementation.
This creates a simple test audio file and verifies that background analysis works correctly.
"""

import tempfile
import os
import time
from pathlib import Path

def create_simple_test_audio():
    """Create a simple test audio file using a basic approach."""
    try:
        import numpy as np
        import wave
        
        # Create a simple sine wave
        sample_rate = 22050
        duration = 2.0
        frequency = 440  # A4 note
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        signal = np.sin(2 * np.pi * frequency * t)
        
        # Scale to 16-bit range
        signal = (signal * 32767).astype(np.int16)
        
        # Create temporary WAV file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            with wave.open(tmp.name, 'w') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(signal.tobytes())
            
            return tmp.name
            
    except Exception as e:
        print(f"Failed to create test audio: {e}")
        return None

def test_background_analysis():
    """Test that background analysis works without blocking."""
    print("=== Background Analysis Test ===\n")
    
    # Create test audio file
    test_file = create_simple_test_audio()
    if not test_file:
        print("Could not create test audio file")
        return
    
    try:
        from sidecar_eq.app import BackgroundAnalysisWorker
        from PySide6.QtCore import QThread, QCoreApplication
        
        # We need a QCoreApplication for signals to work
        import sys
        from PySide6.QtWidgets import QApplication
        
        if not QApplication.instance():
            app = QApplication(sys.argv)
        
        print(f"Testing background analysis with: {Path(test_file).name}")
        
        # Track results
        analysis_complete = False
        analysis_failed = False
        result_data = None
        error_message = None
        
        def on_complete(path, data):
            nonlocal analysis_complete, result_data
            analysis_complete = True
            result_data = data
            print(f"✓ Analysis completed for: {Path(path).name}")
            if data and 'analysis_data' in data:
                lufs = data['analysis_data'].get('loudness_lufs', 'N/A')
                volume = data['analysis_data'].get('suggested_volume', 'N/A')
                print(f"  LUFS: {lufs}, Suggested Volume: {volume}")
        
        def on_failed(path, error):
            nonlocal analysis_failed, error_message
            analysis_failed = True
            error_message = error
            print(f"✗ Analysis failed for: {Path(path).name} - {error}")
        
        # Create and start background worker
        worker = BackgroundAnalysisWorker(test_file)
        worker.analysis_complete.connect(on_complete)
        worker.analysis_failed.connect(on_failed)
        
        print("Starting background analysis...")
        start_time = time.time()
        worker.start()
        
        # Process events while waiting (simulates UI not blocking)
        timeout = 30  # 30 second timeout
        while not analysis_complete and not analysis_failed:
            QCoreApplication.processEvents()
            time.sleep(0.1)
            
            if time.time() - start_time > timeout:
                print("✗ Analysis timed out")
                worker.stop_analysis()
                break
        
        # Wait for thread to finish
        worker.wait(2000)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        if analysis_complete:
            print(f"✓ Background analysis completed successfully in {elapsed:.1f} seconds")
            print("✓ UI would remain responsive during analysis")
        elif analysis_failed:
            print(f"✗ Background analysis failed: {error_message}")
        else:
            print("✗ Analysis did not complete within timeout")
    
    except Exception as e:
        print(f"✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.unlink(test_file)
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_background_analysis()