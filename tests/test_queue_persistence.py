#!/usr/bin/env python3

"""
Test queue persistence functionality
"""

import sys
import tempfile
import os
from pathlib import Path

# Add sidecar_eq to path
sys.path.insert(0, '/Users/todd/sidecar-eq')

from sidecar_eq.queue_model import QueueModel

def test_queue_persistence():
    print("=== Testing Queue Persistence ===")
    
    # Create test files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create some dummy test files
        audio_file1 = temp_path / "song1.mp3"
        audio_file2 = temp_path / "song2.flac" 
        video_file1 = temp_path / "video1.mp4"
        
        for f in [audio_file1, audio_file2, video_file1]:
            f.write_text("dummy content")
        
        # Test 1: Create queue and add items
        print("\n1. Creating queue and adding test files...")
        model1 = QueueModel()
        
        # Add audio files
        count = model1.add_paths([str(audio_file1), str(audio_file2)])
        print(f"   Added {count} audio files")
        
        # Add video file using add_track (to test different source types)
        model1.add_track({
            "file": str(video_file1),
            "title": "Test Video",
            "artist": "Test Artist",
            "album": "Test Album",
            "source": "local"
        })
        print(f"   Added video file as track")
        
        print(f"   Queue has {model1.rowCount()} items")
        
        # Test 2: Save queue state
        print("\n2. Saving queue state...")
        queue_file = temp_path / "test_queue.json"
        success = model1.save_queue_state(queue_file)
        print(f"   Save successful: {success}")
        print(f"   Queue file exists: {queue_file.exists()}")
        
        if queue_file.exists():
            print(f"   Queue file size: {queue_file.stat().st_size} bytes")
        
        # Test 3: Load queue state into new model
        print("\n3. Loading queue state into new model...")
        model2 = QueueModel()
        print(f"   New model starts with {model2.rowCount()} items")
        
        success = model2.load_queue_state(queue_file)
        print(f"   Load successful: {success}")
        print(f"   Loaded model has {model2.rowCount()} items")
        
        # Test 4: Verify loaded data
        print("\n4. Verifying loaded data...")
        for i in range(model2.rowCount()):
            row_data = model2._rows[i]
            title = row_data.get('title', Path(row_data['path']).name)
            source = row_data.get('source', 'local')
            print(f"   Row {i}: {title} (source: {source})")
        
        # Test 5: Test missing files (simulate files being deleted)
        print("\n5. Testing missing file handling...")
        
        # Delete one test file
        audio_file1.unlink()
        print(f"   Deleted {audio_file1.name}")
        
        # Try to load again
        model3 = QueueModel()
        success = model3.load_queue_state(queue_file)
        print(f"   Load successful: {success}")
        print(f"   Model with missing file has {model3.rowCount()} items (should be fewer)")
        
        # Test 6: Clear queue
        print("\n6. Testing queue clear...")
        model3.clear_queue()
        print(f"   After clear: {model3.rowCount()} items")

        print("\n✅ Queue persistence tests completed!")

if __name__ == "__main__":
    test_queue_persistence()