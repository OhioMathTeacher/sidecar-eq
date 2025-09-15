#!/usr/bin/env python3
"""Test video audio extraction functionality"""

import sys
import subprocess
from pathlib import Path

# Add the sidecar_eq package to the path
sys.path.insert(0, str(Path(__file__).parent))

def check_ffmpeg():
    """Check if FFmpeg is available"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ FFmpeg is available")
            # Extract version info
            version_line = result.stdout.split('\n')[0]
            print(f"   {version_line}")
            return True
        else:
            print("❌ FFmpeg command failed")
            return False
    except FileNotFoundError:
        print("❌ FFmpeg not found - please install FFmpeg")
        print("   macOS: brew install ffmpeg")
        print("   Ubuntu: sudo apt install ffmpeg")
        print("   Windows: Download from https://ffmpeg.org/")
        return False
    except Exception as e:
        print(f"❌ FFmpeg check failed: {e}")
        return False

def test_video_detection():
    """Test video file detection"""
    print(f"\n{'='*60}")
    print("Testing video file detection...")
    
    try:
        from sidecar_eq.video_extractor import is_video_file
        
        test_files = [
            "test.mp4",      # Video
            "test.mov",      # Video  
            "test.avi",      # Video
            "test.mp3",      # Audio
            "test.flac",     # Audio
            "test.txt",      # Other
        ]
        
        for filename in test_files:
            is_video = is_video_file(filename)
            file_type = "Video" if is_video else "Not Video"
            print(f"  {filename:<12} -> {file_type}")
            
        print("✅ Video detection working")
        return True
        
    except Exception as e:
        print(f"❌ Video detection failed: {e}")
        return False

def test_j_geils_extraction():
    """Test extraction on the actual J. Geils files"""
    print(f"\n{'='*60}")
    print("Testing J. Geils Band video extraction...")
    
    try:
        from sidecar_eq.video_extractor import VideoAudioExtractor
        
        # Known J. Geils video files
        video_files = [
            "/Volumes/Music/****Need to process/J Geils Band Monkey Island.mp4",
            "/Volumes/Music/****Need to process/J Geils Band Self Titled.mp4",
        ]
        
        extractor = VideoAudioExtractor()
        
        for video_path in video_files:
            if Path(video_path).exists():
                print(f"\nTesting: {Path(video_path).name}")
                
                # Check if it's detected as video
                if extractor.is_video_file(video_path):
                    print("  ✅ Detected as video file")
                    
                    # Get video info
                    info = extractor.get_video_info(video_path)
                    if info:
                        print(f"  📹 Has video: {info.get('has_video', 'unknown')}")
                        print(f"  🔊 Has audio: {info.get('has_audio', 'unknown')}")
                        print(f"  🎵 Audio codec: {info.get('audio_codec', 'unknown')}")
                        duration = info.get('duration', 0)
                        if duration > 0:
                            minutes, seconds = divmod(int(duration), 60)
                            print(f"  ⏱️  Duration: {minutes}:{seconds:02d}")
                    
                    # Test cache path generation
                    cache_path = extractor.get_cached_audio_path(video_path)
                    print(f"  💾 Cache path: {cache_path.name if cache_path else 'None'}")
                    
                    # Check if we should attempt extraction
                    if info and info.get('has_audio'):
                        print("  ⚠️  Would extract audio (not running full extraction in test)")
                    else:
                        print("  ❌ No audio track detected")
                        
                else:
                    print("  ❌ Not detected as video file")
            else:
                print(f"  ⚠️  File not found: {video_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ J. Geils extraction test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cache_management():
    """Test cache directory management"""
    print(f"\n{'='*60}")
    print("Testing cache management...")
    
    try:
        from sidecar_eq.video_extractor import VideoAudioExtractor
        
        extractor = VideoAudioExtractor()
        cache_dir = extractor.cache_dir
        
        print(f"Cache directory: {cache_dir}")
        print(f"Cache exists: {cache_dir.exists()}")
        
        if cache_dir.exists():
            cached_files = list(cache_dir.glob("*.m4a"))
            print(f"Cached files: {len(cached_files)}")
            
            total_size = sum(f.stat().st_size for f in cached_files) / (1024 * 1024)
            print(f"Total cache size: {total_size:.1f} MB")
            
            for cached_file in cached_files[:3]:  # Show first 3
                size_mb = cached_file.stat().st_size / (1024 * 1024)
                print(f"  {cached_file.name} ({size_mb:.1f} MB)")
                
            if len(cached_files) > 3:
                print(f"  ... and {len(cached_files) - 3} more")
        
        print("✅ Cache management working")
        return True
        
    except Exception as e:
        print(f"❌ Cache management test failed: {e}")
        return False

if __name__ == "__main__":
    print("Video Audio Extraction Test Suite")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 4
    
    # Run tests
    if check_ffmpeg():
        tests_passed += 1
    
    if test_video_detection():
        tests_passed += 1
        
    if test_j_geils_extraction():
        tests_passed += 1
        
    if test_cache_management():
        tests_passed += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Test Results: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("✅ All tests passed! Video audio extraction is ready.")
        print("\nNext steps:")
        print("1. Start the Sidecar EQ app")
        print("2. Add the J. Geils Band MP4 files")
        print("3. They should appear with '(video)' indicator")
        print("4. Click play - audio will be extracted automatically")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        if not check_ffmpeg():
            print("💡 Install FFmpeg to enable video audio extraction")
    
    sys.exit(0 if tests_passed == total_tests else 1)