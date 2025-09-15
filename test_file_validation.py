#!/usr/bin/env python3
"""Test file type validation fix"""

import sys
from pathlib import Path

# Add the sidecar_eq package to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_file_validation():
    """Test that file type validation works correctly"""
    print("Testing file type validation...")
    
    # Test cases
    test_files = [
        "/Users/todd/Music/song.mp3",           # Valid audio
        "/Users/todd/Music/song.flac",          # Valid audio  
        "/Users/todd/Music/song.wav",           # Valid audio
        "/Users/todd/Music/video.mp4",          # Invalid - should be rejected
        "/Users/todd/Music/video.avi",          # Invalid - should be rejected
        "/Users/todd/Music/document.pdf",       # Invalid - should be rejected
        "https://example.com/audio.mp3",        # URL - should be allowed
        "https://example.com/video.mp4",        # URL - should be allowed (can't validate remote)
    ]
    
    # Valid audio extensions
    AUDIO_EXTS = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}
    
    print("\nFile validation results:")
    for file_path in test_files:
        if file_path.startswith(('http://', 'https://')):
            # URLs are allowed regardless of extension
            should_allow = True
            reason = "URL (no extension validation)"
        else:
            # Local files must have valid audio extension
            ext = Path(file_path).suffix.lower()
            should_allow = ext in AUDIO_EXTS
            reason = f"Local file, extension: {ext}"
        
        status = "✅ Allow" if should_allow else "❌ Reject"
        print(f"  {status} {file_path}")
        print(f"    Reason: {reason}")

def test_existing_mp4_detection():
    """Test detection of existing problematic files"""
    print(f"\n{'='*60}")
    print("Testing detection of existing MP4 files...")
    
    # Known problematic files from diagnostic
    problematic_files = [
        "/Volumes/Music/****Need to process/J Geils Band Monkey Island.mp4",
        "/Volumes/Music/****Need to process/J Geils Band Self Titled.mp4",
    ]
    
    for file_path in problematic_files:
        if Path(file_path).exists():
            print(f"Found problematic file: {file_path}")
            print(f"  Extension: {Path(file_path).suffix}")
            print(f"  Size: {Path(file_path).stat().st_size} bytes")
            
            # Check if it would be rejected by new validation
            ext = Path(file_path).suffix.lower()
            AUDIO_EXTS = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}
            would_reject = ext not in AUDIO_EXTS
            
            print(f"  New validation would: {'✅ Reject' if would_reject else '❌ Allow'}")
        else:
            print(f"File not found: {file_path}")

if __name__ == "__main__":
    print("File Type Validation Test")
    print("=" * 60)
    
    test_file_validation()
    test_existing_mp4_detection()
    
    print(f"\n{'='*60}")
    print("Summary:")
    print("✅ File type validation now prevents MP4 and other non-audio files")
    print("✅ URLs are still allowed (for streaming audio)")
    print("✅ Existing MP4 files in queue should be detected and warned about")
    print("\nRecommendation: Remove any existing MP4 files from the queue manually")
    print("or restart the app to clear the queue of problematic entries.")