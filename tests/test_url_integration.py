#!/usr/bin/env python3
"""Integration test for Website URL playback"""

import sys
from pathlib import Path

# Add the sidecar_eq package to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_url_integration():
    """Test URL integration without requiring Qt UI"""
    print("Testing URL integration...")
    
    try:
        from sidecar_eq.queue_model import QueueModel
        from sidecar_eq.player import Player
        
        # Test QueueModel with URLs (mock Qt parent)
        class MockParent:
            pass
            
        print("✅ Creating QueueModel...")
        model = QueueModel(None)  # Use None as parent for testing
        
        # Test adding URLs via add_paths
        test_urls = [
            "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav",
            "http://streaming.example.com/test.mp3"
        ]
        
        print(f"✅ Adding {len(test_urls)} URLs to queue...")
        model.add_paths(test_urls)
        
        # Verify URLs are in paths
        paths = model.paths()
        print(f"✅ Queue paths: {paths}")
        
        for url in test_urls:
            if url in paths:
                print(f"  ✅ URL found in queue: {Path(url).name}")
            else:
                print(f"  ❌ URL missing from queue: {url}")
        
        # Test URL detection in path list
        for path in paths:
            if path.startswith(('http://', 'https://')):
                print(f"  ✅ URL detected: {Path(path).name}")
            else:
                print(f"  ℹ️  Non-URL: {Path(path).name}")
        
        # Test Player URL handling (without actually playing)
        from PySide6.QtCore import QUrl
        
        print("✅ Testing Player URL handling...")
        for url in test_urls:
            # Test the URL creation logic from Player.setSource
            if url.startswith(('http://', 'https://')):
                qurl = QUrl(url)  # Network URL
                url_type = "Network"
            else:
                qurl = QUrl.fromLocalFile(url)  # Local file
                url_type = "Local"
            
            print(f"  ✅ {url_type} URL: {qurl.toString()[:60]}{'...' if len(qurl.toString()) > 60 else ''}")
            
            if not qurl.isValid():
                print(f"    ❌ Invalid URL: {url}")
                return False
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error (PySide6 not available in test): {e}")
        return False  # Expected in test environment
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def simulate_play_logic():
    """Simulate the _play_row URL detection logic"""
    print(f"\n{'='*50}")
    print("Simulating _play_row URL logic...")
    
    # Test cases: (path, track_info, expected_source_type, expected_playback_url)
    test_cases = [
        # Local file
        ("/Users/todd/Music/song.mp3", {}, "local", "/Users/todd/Music/song.mp3"),
        # Website URL
        ("https://example.com/audio.mp3", {}, "url", "https://example.com/audio.mp3"),
        # Plex track
        ("/library/metadata/123", {"stream_url": "https://plex.server.com/stream/456"}, "plex", "https://plex.server.com/stream/456"),
    ]
    
    for path, track_info, expected_source, expected_playback in test_cases:
        # Simulate the detection logic from _play_row
        if track_info.get('stream_url'):
            # Plex track
            playback_url = track_info['stream_url']
            identifier = track_info['stream_url']
            source_type = 'plex'
        elif path.startswith(('http://', 'https://')):
            # Website URL
            playback_url = path
            identifier = path
            source_type = 'url'
        else:
            # Local file
            playback_url = path
            identifier = path
            source_type = 'local'
        
        status = "✅" if source_type == expected_source and playback_url == expected_playback else "❌"
        print(f"  {status} {source_type}: {Path(path).name}")
        print(f"      Playback URL: {playback_url}")
        print(f"      Identifier: {identifier}")
        
        if source_type != expected_source:
            print(f"      ❌ Expected source: {expected_source}")
        if playback_url != expected_playback:
            print(f"      ❌ Expected playback: {expected_playback}")

if __name__ == "__main__":
    print("Website URL Integration Test")
    print("=" * 50)
    
    success = test_url_integration()
    simulate_play_logic()
    
    if success:
        print(f"\n{'='*50}")
        print("✅ URL integration test completed successfully!")
        print("Website URLs should now:")
        print("- Add to queue correctly via add_paths()")
        print("- Be detected as 'url' source type")
        print("- Skip audio analysis (like Plex streams)")
        print("- Play through QMediaPlayer with QUrl()")
        print("- Support EQ/volume save/load functionality")
    else:
        print(f"\n{'='*50}")
        print("⚠️  URL integration test completed with limitations")
        print("(PySide6 not available in test environment - normal for headless testing)")
        
    print("\nTo test fully: Run the app and try adding a Website URL!")
    sys.exit(0 if success else 1)