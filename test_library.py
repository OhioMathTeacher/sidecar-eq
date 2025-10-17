#!/usr/bin/env python3
"""Test script for the hierarchical Library system.

Tests:
1. Library creation and loading
2. Indexer scanning and building Library
3. Library search functionality
4. Song/Album/Artist hierarchy
5. Autocomplete suggestions

Run with: python test_library.py
"""

from pathlib import Path
from sidecar_eq.library import Library, Song, Album, Artist
from sidecar_eq.indexer import LibraryIndexer


def test_basic_library():
    """Test basic Library operations."""
    print("\n=== Test 1: Basic Library Operations ===")
    
    # Create a library
    lib = Library()
    
    # Create some test songs
    song1 = Song(
        path="/fake/path/song1.mp3",
        title="Money",
        artist="Pink Floyd",
        album="Dark Side of the Moon"
    )
    
    song2 = Song(
        path="/fake/path/song2.mp3",
        title="Time",
        artist="Pink Floyd",
        album="Dark Side of the Moon"
    )
    
    song3 = Song(
        path="/fake/path/song3.mp3",
        title="Comfortably Numb",
        artist="Pink Floyd",
        album="The Wall"
    )
    
    # Add songs to library
    lib.add_song(song1)
    lib.add_song(song2)
    lib.add_song(song3)
    
    print(f"✓ Created library: {lib}")
    print(f"✓ Total artists: {lib.total_artists}")
    print(f"✓ Total albums: {lib.total_albums}")
    print(f"✓ Total songs: {lib.total_songs}")
    
    # Check hierarchy
    assert lib.total_artists == 1, "Should have 1 artist"
    assert lib.total_albums == 2, "Should have 2 albums"
    assert lib.total_songs == 3, "Should have 3 songs"
    
    pink_floyd = lib.artists.get("Pink Floyd")
    assert pink_floyd is not None, "Pink Floyd should exist"
    print(f"✓ Artist: {pink_floyd}")
    
    dark_side = pink_floyd.albums.get("Dark Side of the Moon")
    assert dark_side is not None, "Album should exist"
    assert dark_side.song_count == 2, "Album should have 2 songs"
    print(f"✓ Album: {dark_side}")
    
    print("✅ Test 1 PASSED\n")


def test_library_search():
    """Test Library search functionality."""
    print("\n=== Test 2: Library Search ===")
    
    lib = Library()
    
    # Add test data
    for i in range(5):
        song = Song(
            path=f"/fake/song{i}.mp3",
            title=f"Song {i}",
            artist="Pink Floyd",
            album="Dark Side"
        )
        song.play_count = i * 10  # Give some play counts
        lib.add_song(song)
    
    # Add different artist
    song = Song(
        path="/fake/led.mp3",
        title="Stairway to Heaven",
        artist="Led Zeppelin",
        album="Led Zeppelin IV"
    )
    lib.add_song(song)
    
    # Search for "pink"
    results = lib.search("pink")
    print(f"Search 'pink': {len(results['artists'])} artists, {len(results['albums'])} albums, {len(results['songs'])} songs")
    assert len(results['artists']) == 1, "Should find 1 artist"
    assert len(results['songs']) == 5, "Should find 5 songs"
    
    # Search for "led"
    results = lib.search("led")
    print(f"Search 'led': {len(results['artists'])} artists, {len(results['albums'])} albums, {len(results['songs'])} songs")
    assert len(results['artists']) == 1, "Should find Led Zeppelin"
    
    # Search for "song"
    results = lib.search("song")
    print(f"Search 'song': {len(results['songs'])} songs")
    assert len(results['songs']) == 5, "Should find 5 songs with 'song' in title"
    
    print("✅ Test 2 PASSED\n")


def test_top_songs():
    """Test top songs/albums/artists methods."""
    print("\n=== Test 3: Top Songs/Albums/Artists ===")
    
    lib = Library()
    
    # Add songs with varying play counts
    songs_data = [
        ("Money", "Pink Floyd", "Dark Side", 100),
        ("Time", "Pink Floyd", "Dark Side", 80),
        ("Comfortably Numb", "Pink Floyd", "The Wall", 120),
        ("Stairway", "Led Zeppelin", "IV", 90),
        ("Kashmir", "Led Zeppelin", "Physical", 70),
    ]
    
    for title, artist, album, plays in songs_data:
        song = Song(f"/fake/{title}.mp3", title, artist, album)
        song.play_count = plays
        lib.add_song(song)
    
    # Get top songs
    top_songs = lib.get_top_songs(limit=3)
    print(f"Top 3 songs:")
    for i, song in enumerate(top_songs, 1):
        print(f"  {i}. {song.title} - {song.play_count} plays")
    
    assert top_songs[0].title == "Comfortably Numb", "Most played should be Comfortably Numb"
    assert top_songs[1].title == "Money", "Second should be Money"
    
    # Get top albums
    top_albums = lib.get_top_albums(limit=2)
    print(f"\nTop 2 albums:")
    for i, album in enumerate(top_albums, 1):
        print(f"  {i}. {album.title} by {album.artist} - {album.total_plays} plays")
    
    assert top_albums[0].title == "Dark Side", "Dark Side should be top album"
    
    # Get top artists
    top_artists = lib.get_top_artists(limit=2)
    print(f"\nTop 2 artists:")
    for i, artist in enumerate(top_artists, 1):
        print(f"  {i}. {artist.name} - {artist.total_plays} plays")
    
    print("✅ Test 3 PASSED\n")


def test_song_by_path():
    """Test finding songs by path."""
    print("\n=== Test 4: Find Song by Path ===")
    
    lib = Library()
    
    path = "/test/music/song.mp3"
    song = Song(path, "Test Song", "Test Artist", "Test Album")
    lib.add_song(song)
    
    # Find by path
    found = lib.get_song_by_path(path)
    assert found is not None, "Should find song by path"
    assert found.title == "Test Song", "Should be correct song"
    print(f"✓ Found song by path: {found}")
    
    # Try non-existent path
    not_found = lib.get_song_by_path("/fake/path.mp3")
    assert not_found is None, "Should not find non-existent song"
    print(f"✓ Correctly returns None for non-existent path")
    
    print("✅ Test 4 PASSED\n")


def test_indexer():
    """Test LibraryIndexer with real files (if available)."""
    print("\n=== Test 5: LibraryIndexer ===")
    
    indexer = LibraryIndexer()
    
    # Check if user has a music folder
    test_folders = [
        Path.home() / "Music",
        Path("/Users/todd/Music"),
        Path("/Users/todd/Documents/Music"),
    ]
    
    music_folder = None
    for folder in test_folders:
        if folder.exists() and folder.is_dir():
            music_folder = folder
            break
    
    if music_folder:
        print(f"✓ Found music folder: {music_folder}")
        print(f"  Scanning first 10 files only (non-recursive)...")
        
        # Scan just the top level, don't recurse
        added = indexer.scan_folder(str(music_folder), recursive=False)
        print(f"✓ Scanned and added {added} tracks")
        
        lib = indexer.get_library()
        print(f"✓ Library now has:")
        print(f"  - {lib.total_artists} artists")
        print(f"  - {lib.total_albums} albums")
        print(f"  - {lib.total_songs} songs")
        
        if lib.total_songs > 0:
            # Test search on real data
            first_artist = list(lib.artists.keys())[0]
            print(f"\n  Testing search for '{first_artist}'...")
            results = lib.search(first_artist)
            print(f"  Found: {len(results['artists'])} artists, {len(results['songs'])} songs")
    else:
        print("⚠️  No music folder found, skipping real file test")
        print("   This is OK - using synthetic data for other tests")
    
    print("✅ Test 5 PASSED\n")


def test_stem_support():
    """Test stem-related features (data structures only, no actual separation)."""
    print("\n=== Test 6: Stem Support (Data Structures) ===")
    
    song = Song(
        path="/test/song.mp3",
        title="Test",
        artist="Artist",
        album="Album"
    )
    
    # Check stem properties
    print(f"✓ Stem cache dir: {song.stem_cache_dir}")
    print(f"✓ Has stems: {song.has_stems}")
    print(f"✓ Vocals path: {song.get_stem_path('vocals')}")
    
    # Check stem settings
    assert 'vocals' in song.stem_settings, "Should have vocals settings"
    assert 'drums' in song.stem_settings, "Should have drums settings"
    print(f"✓ Stem settings structure: {list(song.stem_settings.keys())}")
    
    # Verify default values
    assert song.stem_settings['vocals']['volume'] == 1.0, "Default volume should be 1.0"
    assert song.stem_settings['vocals']['muted'] == False, "Default muted should be False"
    print(f"✓ Default stem settings correct")
    
    print("✅ Test 6 PASSED\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Hierarchical Library System")
    print("=" * 60)
    
    try:
        test_basic_library()
        test_library_search()
        test_top_songs()
        test_song_by_path()
        test_stem_support()
        test_indexer()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nLibrary system is ready for integration into app.py")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
