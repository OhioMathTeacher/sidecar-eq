#!/usr/bin/env python3
"""Diagnostic tool for J. Geils Band MP3 issue"""

import sys
import os
from pathlib import Path

# Add the sidecar_eq package to the path
sys.path.insert(0, str(Path(__file__).parent))

def find_jgeils_files():
    """Find any files with 'J-Geils' or 'Geils' in the name"""
    print("Searching for J. Geils Band files...")
    
    # Common music directories to search
    search_dirs = [
        Path.home() / "Music",
        Path("/Volumes/Music"),  # External drive
        Path("/Users/todd/Music"),
        Path.cwd(),  # Current directory
    ]
    
    found_files = []
    
    for search_dir in search_dirs:
        if search_dir.exists():
            print(f"Searching in: {search_dir}")
            try:
                # Search for files containing 'geils' (case insensitive)
                for file_path in search_dir.rglob("*"):
                    if file_path.is_file() and 'geils' in file_path.name.lower():
                        found_files.append(file_path)
                        print(f"  Found: {file_path}")
                        
                        # Check file properties
                        try:
                            stat = file_path.stat()
                            print(f"    Size: {stat.st_size} bytes")
                            print(f"    Readable: {os.access(file_path, os.R_OK)}")
                            
                            # Check if it's a valid audio file
                            if file_path.suffix.lower() in ['.mp3', '.flac', '.wav', '.ogg', '.m4a']:
                                print(f"    Audio file: {file_path.suffix}")
                                
                                # Try to read first few bytes
                                try:
                                    with open(file_path, 'rb') as f:
                                        header = f.read(16)
                                        print(f"    Header (hex): {header.hex()}")
                                        print(f"    Header (ascii): {header}")
                                except Exception as e:
                                    print(f"    ❌ Cannot read file: {e}")
                            else:
                                print(f"    Not an audio file: {file_path.suffix}")
                                
                        except Exception as e:
                            print(f"    ❌ Cannot stat file: {e}")
                            
            except Exception as e:
                print(f"  Error searching {search_dir}: {e}")
    
    return found_files

def test_paths():
    """Test path handling logic"""
    print(f"\n{'='*60}")
    print("Testing path handling logic...")
    
    # Test cases that might be problematic
    test_cases = [
        "J-Geils-Band-Monkey-Island.mp3",
        "/Users/todd/Music/J-Geils-Band-Monkey-Island.mp3", 
        "/Volumes/Music/J. Geils Band/Monkey Island.mp3",
        "https://example.com/J-Geils-Band-Monkey-Island.mp3",
    ]
    
    for path in test_cases:
        print(f"\nTesting path: '{path}'")
        
        # Test source detection logic
        if path.startswith(('http://', 'https://')):
            source_type = 'url'
        else:
            source_type = 'local'
            
        print(f"  Source type: {source_type}")
        
        # Test path validation
        if Path(path).exists():
            print(f"  ✅ File exists")
        else:
            print(f"  ❌ File does not exist")

def simulate_queue_model():
    """Simulate the queue model paths() method"""
    print(f"\n{'='*60}")
    print("Simulating queue model behavior...")
    
    # Simulate different row types
    test_rows = [
        # Local file added via add_paths
        {
            "path": "/Users/todd/Music/J-Geils-Band-Monkey-Island.mp3",
            "title": "Monkey Island",
            "artist": "J. Geils Band",
            "album": "Hotline",
        },
        # Local file accidentally added via add_track
        {
            "path": "/Users/todd/Music/song.mp3",
            "title": "Song",
            "artist": "Artist", 
            "album": "Album",
            "stream_url": None,  # This could cause issues
            "source": "local",
        },
        # Plex track properly added
        {
            "path": "/library/metadata/123",
            "title": "Plex Song",
            "artist": "Plex Artist",
            "album": "Plex Album",
            "stream_url": "https://plex.server.com/stream/456",
            "source": "plex",
        },
        # URL properly added
        {
            "path": "https://example.com/audio.mp3",
            "title": "URL Song",
            "artist": "URL Artist",
            "album": "URL Album",
        }
    ]
    
    print("Simulating paths() method results:")
    for i, row in enumerate(test_rows):
        # Original problematic logic: r.get("stream_url") or r["path"]
        old_result = row.get("stream_url") or row["path"]
        
        # New improved logic
        stream_url = row.get("stream_url")
        path = row.get("path", "")
        
        if stream_url and stream_url.strip():
            new_result = stream_url
        elif path and path.strip():
            new_result = path
        else:
            new_result = ""
            
        print(f"\n  Row {i}: {row.get('title', 'Unknown')}")
        print(f"    Row data: {row}")
        print(f"    Old logic result: '{old_result}'")
        print(f"    New logic result: '{new_result}'")
        
        if old_result != new_result:
            print(f"    ⚠️  Different results!")

if __name__ == "__main__":
    print("J. Geils Band MP3 Diagnostic Tool")
    print("=" * 60)
    
    found_files = find_jgeils_files()
    test_paths()
    simulate_queue_model()
    
    print(f"\n{'='*60}")
    print("Summary:")
    print(f"Found {len(found_files)} J. Geils files")
    if found_files:
        print("Check the file properties above for any issues.")
    print("The queue model logic has been improved to handle edge cases.")
    print("If files still won't play, check for file corruption or permission issues.")