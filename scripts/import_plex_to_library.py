#!/usr/bin/env python3
"""Import Plex music into SidecarEQ Library.

This script:
1. Connects to your Plex server
2. Scans your music library
3. Adds all Plex tracks to the SidecarEQ Library
4. Saves the library so search finds Plex music

Usage:
    python import_plex_to_library.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sidecar_eq.audio_sources import Track, AudioSourceInfo
from sidecar_eq.library import Library
from sidecar_eq.indexer import LibraryIndexer

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os
from plexapi.myplex import MyPlexAccount


def connect_to_plex():
    """Connect to Plex server."""
    print("=" * 60)
    print("Connecting to Plex")
    print("=" * 60)
    
    token = os.getenv('PLEX_TOKEN', '')
    if not token:
        print("❌ No PLEX_TOKEN in .env file")
        return None, None
    
    try:
        account = MyPlexAccount(token=token)
        print(f"✅ Logged in as: {account.username}")
        
        # Get first server
        servers = [r for r in account.resources() if r.provides == 'server']
        if not servers:
            print("❌ No Plex servers found")
            return None, None
        
        plex = servers[0].connect()
        print(f"✅ Connected to: {plex.friendlyName}")
        
        # Get music library
        music_sections = [s for s in plex.library.sections() if s.type == 'artist']
        if not music_sections:
            print("❌ No music libraries found")
            return plex, None
        
        music = music_sections[0]
        print(f"✅ Found music library: {music.title} ({music.totalSize} items)")
        
        return plex, music
        
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return None, None


def import_plex_tracks_to_library(music_section, library, limit=None):
    """Import Plex tracks into SidecarEQ Library.
    
    Args:
        music_section: Plex music section
        library: SidecarEQ Library instance
        limit: Optional limit for testing (None = import all)
    
    Returns:
        Number of tracks imported
    """
    print("\n" + "=" * 60)
    print("Importing Plex Tracks to Library")
    print("=" * 60)
    
    try:
        # Get all tracks
        print(f"\n📥 Scanning Plex library...")
        if limit:
            print(f"   (Limited to {limit} tracks for testing)")
            tracks = music_section.searchTracks(limit=limit)
        else:
            tracks = music_section.searchTracks()
        
        print(f"✅ Found {len(tracks)} tracks")
        
        # Import each track
        imported = 0
        for i, track in enumerate(tracks, 1):
            try:
                # Get metadata
                title = track.title
                artist = track.grandparentTitle or "Unknown Artist"
                album = track.parentTitle or "Unknown Album"
                
                # Store Plex key (not stream URL - those expire!)
                # Format: plex://<server_id>/<track_key>
                plex_path = f"plex://downstairs{track.key}"
                
                # Add to library (creates Artist/Album hierarchy)
                from sidecar_eq.library import Song
                song = Song(
                    path=plex_path,  # Store Plex identifier, not URL
                    title=title,
                    artist=artist,
                    album=album
                )
                library.add_song(song)
                
                imported += 1
                
                # Progress update
                if i % 50 == 0:
                    print(f"   ... {i}/{len(tracks)} tracks processed")
                
            except Exception as e:
                print(f"⚠️  Skipped track {i}: {e}")
                continue
        
        print(f"\n✅ Imported {imported} Plex tracks to library")
        return imported
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return 0


def main():
    """Main entry point."""
    print("\n🎵 SidecarEQ - Plex Library Import")
    print("=" * 60)
    
    # Connect to Plex
    plex, music = connect_to_plex()
    if not music:
        return 1
    
    # Load existing library
    print("\n" + "=" * 60)
    print("Loading Existing Library")
    print("=" * 60)
    
    library = Library()
    print(f"✅ Current library:")
    print(f"   Artists: {library.total_artists}")
    print(f"   Albums: {library.total_albums}")
    print(f"   Songs: {library.total_songs}")
    
    # Ask user
    print("\n" + "=" * 60)
    print("Import Options")
    print("=" * 60)
    print(f"\n💡 Your Plex library has {music.totalSize} items")
    print("\nOptions:")
    print("  1. Test import (50 tracks)")
    print("  2. Full import (all tracks)")
    print("  3. Cancel")
    
    choice = input("\nChoice (1/2/3): ").strip()
    
    if choice == "3":
        print("❌ Cancelled")
        return 0
    
    limit = 50 if choice == "1" else None
    
    # Import tracks
    imported = import_plex_tracks_to_library(music, library, limit=limit)
    
    if imported == 0:
        print("\n❌ No tracks imported")
        return 1
    
    # Save library
    print("\n" + "=" * 60)
    print("Saving Library")
    print("=" * 60)
    
    library.save()
    print(f"✅ Library saved to: {library.library_path}")
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ IMPORT COMPLETE!")
    print("=" * 60)
    print(f"\n📊 Library Stats:")
    print(f"   Artists: {library.total_artists}")
    print(f"   Albums: {library.total_albums}")
    print(f"   Songs: {library.total_songs}")
    
    print(f"\n💡 Next Steps:")
    print(f"   1. Launch SidecarEQ")
    print(f"   2. Search for any Plex track!")
    print(f"   3. Double-click to play from Plex")
    
    # Test search
    if library.total_songs > 0:
        print("\n" + "=" * 60)
        print("Testing Search")
        print("=" * 60)
        
        # Get first artist
        first_artist = sorted(library.artists.keys())[0]
        print(f"\nSearching for: {first_artist}")
        
        results = library.search(first_artist, limit=5)
        print(f"\n✅ Found:")
        print(f"   Artists: {len(results['artists'])}")
        print(f"   Albums: {len(results['albums'])}")
        print(f"   Songs: {len(results['songs'])}")
        
        if results['songs']:
            print(f"\n   Sample songs:")
            for song in results['songs'][:3]:
                print(f"   🎵 {song.title} - {song.artist}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
