#!/usr/bin/env python3
"""Test Plex playback with the new audio source system.

This script:
1. Connects to your Plex server
2. Lists available music
3. Gets a playback URL
4. Tests it with the audio source system
5. (Optionally) Plays it with Qt Multimedia

Usage:
    python test_plex_playback.py
"""

import sys
from pathlib import Path

# Add sidecar_eq to path
sys.path.insert(0, str(Path(__file__).parent))

from sidecar_eq.audio_sources import Track, AudioSourceInfo, AudioRepository, create_track_from_plex
from sidecar_eq import plex_helpers

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def test_plex_connection():
    """Test basic Plex connection."""
    print("=" * 60)
    print("Step 1: Testing Plex Connection")
    print("=" * 60)
    
    try:
        # Try to connect to Plex via MyPlex (cloud method)
        from plexapi.myplex import MyPlexAccount
        import os
        
        plex_token = os.getenv('PLEX_TOKEN', '')
        
        if not plex_token:
            print("❌ No PLEX_TOKEN found in .env file")
            print("\nTo set up Plex:")
            print("1. Find your Plex token: https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/")
            print("2. Add to .env file:")
            print("   PLEX_TOKEN=your_token_here")
            return None
        
        print(f"Connecting via MyPlex...")
        account = MyPlexAccount(token=plex_token)
        print(f"✅ Logged in as: {account.username}")
        
        # Get first server
        servers = [r for r in account.resources() if r.provides == 'server']
        if not servers:
            print("❌ No Plex servers found")
            return None
        
        print(f"✅ Found server: {servers[0].name}")
        plex = servers[0].connect()
        print(f"✅ Connected to: {plex.friendlyName}")
        
        return plex
        
    except Exception as e:
        print(f"❌ Failed to connect to Plex: {e}")
        import traceback
        traceback.print_exc()
        return None


def list_music_libraries(plex):
    """List available music libraries."""
    print("\n" + "=" * 60)
    print("Step 2: Finding Music Libraries")
    print("=" * 60)
    
    try:
        music_sections = [s for s in plex.library.sections() if s.type == 'artist']
        
        if not music_sections:
            print("❌ No music libraries found")
            return None
        
        print(f"✅ Found {len(music_sections)} music library(ies):")
        for i, section in enumerate(music_sections, 1):
            print(f"   {i}. {section.title} ({section.totalSize} items)")
        
        return music_sections[0]  # Return first music library
        
    except Exception as e:
        print(f"❌ Failed to list libraries: {e}")
        return None


def get_sample_track(music_section):
    """Get a sample track from the library."""
    print("\n" + "=" * 60)
    print("Step 3: Getting Sample Track")
    print("=" * 60)
    
    try:
        # Get first 5 tracks
        tracks = music_section.searchTracks(limit=5)
        
        if not tracks:
            print("❌ No tracks found in library")
            return None
        
        print(f"✅ Found {len(tracks)} sample tracks:")
        for i, track in enumerate(tracks, 1):
            print(f"   {i}. {track.title} - {track.artist().title if track.artist() else 'Unknown'}")
        
        # Use first track
        track = tracks[0]
        print(f"\n📀 Selected: {track.title}")
        print(f"   Artist: {track.artist().title if track.artist() else 'Unknown'}")
        print(f"   Album: {track.album().title if track.album() else 'Unknown'}")
        
        return track
        
    except Exception as e:
        print(f"❌ Failed to get tracks: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_plex_url(plex_track):
    """Get and test Plex playback URL."""
    print("\n" + "=" * 60)
    print("Step 4: Getting Plex Playback URL")
    print("=" * 60)
    
    try:
        # Get stream URL from Plex
        stream_url = plex_track.getStreamURL()
        
        print(f"✅ Stream URL obtained:")
        print(f"   {stream_url[:80]}..." if len(stream_url) > 80 else f"   {stream_url}")
        
        # Check if URL is accessible
        print(f"\n📊 URL Details:")
        print(f"   Protocol: {'https' if stream_url.startswith('https') else 'http'}")
        print(f"   Has token: {'X-Plex-Token' in stream_url}")
        print(f"   Length: {len(stream_url)} chars")
        
        return stream_url
        
    except Exception as e:
        print(f"❌ Failed to get stream URL: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_audio_source_system(plex_track, stream_url):
    """Test the new audio source plugin system."""
    print("\n" + "=" * 60)
    print("Step 5: Testing Audio Source System")
    print("=" * 60)
    
    try:
        # Create Track object with Plex source
        track = Track.from_metadata(
            title=plex_track.title,
            artist=plex_track.artist().title if plex_track.artist() else "Unknown",
            album=plex_track.album().title if plex_track.album() else "Unknown",
            sources=[
                AudioSourceInfo(
                    source_type="plex",
                    location=stream_url,
                    quality={
                        "bitrate": getattr(plex_track, 'bitrate', 0),
                        "format": plex_track.media[0].container if plex_track.media else "unknown",
                    },
                    available=True,
                    metadata={
                        "duration": plex_track.duration,
                        "year": plex_track.year,
                    }
                )
            ]
        )
        
        print(f"✅ Created Track object:")
        print(f"   Track ID: {track.track_id}")
        print(f"   Title: {track.title}")
        print(f"   Artist: {track.artist}")
        print(f"   Album: {track.album}")
        print(f"   Sources: {len(track.sources)}")
        
        # Test AudioRepository
        repo = AudioRepository()
        playback_url = repo.get_playback_url(track)
        
        if playback_url:
            print(f"\n✅ AudioRepository generated playback URL:")
            print(f"   {playback_url[:80]}..." if len(playback_url) > 80 else f"   {playback_url}")
            
            # Check availability
            availability = repo.check_availability(track)
            print(f"\n✅ Source availability:")
            for source_type, available in availability.items():
                status = "✅ Available" if available else "❌ Unavailable"
                print(f"   {source_type}: {status}")
            
            return track, playback_url
        else:
            print(f"❌ AudioRepository failed to generate URL")
            return track, None
        
    except Exception as e:
        print(f"❌ Audio source system test failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_qt_playback(playback_url):
    """Test actual playback with Qt Multimedia."""
    print("\n" + "=" * 60)
    print("Step 6: Testing Qt Multimedia Playback")
    print("=" * 60)
    
    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
        from PySide6.QtWidgets import QApplication
        
        # Create Qt application if needed
        app = QApplication.instance() or QApplication(sys.argv)
        
        # Create player
        player = QMediaPlayer()
        audio_output = QAudioOutput()
        player.setAudioOutput(audio_output)
        
        print("✅ Created Qt Multimedia player")
        
        # Set source
        player.setSource(QUrl(playback_url))
        print(f"✅ Set source: {playback_url[:60]}...")
        
        # Connect signals to see what happens
        def on_error(error):
            print(f"❌ Player error: {error}")
            print(f"   Error string: {player.errorString()}")
        
        def on_media_status(status):
            status_names = {
                0: "NoMedia",
                1: "LoadingMedia", 
                2: "LoadedMedia",
                3: "StalledMedia",
                4: "BufferingMedia",
                5: "BufferedMedia",
                6: "EndOfMedia",
                7: "InvalidMedia"
            }
            print(f"📊 Media status: {status_names.get(status, f'Unknown({status})')}")
        
        def on_playback_state(state):
            state_names = {0: "StoppedState", 1: "PlayingState", 2: "PausedState"}
            print(f"📊 Playback state: {state_names.get(state, f'Unknown({state})')}")
        
        player.errorOccurred.connect(on_error)
        player.mediaStatusChanged.connect(on_media_status)
        player.playbackStateChanged.connect(on_playback_state)
        
        # Try to play
        print("\n🎵 Attempting to play for 3 seconds...")
        player.play()
        
        # Run for a bit to see what happens
        import time
        for i in range(3):
            app.processEvents()
            time.sleep(1)
            print(f"   ... {i+1}s")
        
        player.stop()
        print("\n✅ Playback test complete (stopped after 3s)")
        
        return True
        
    except Exception as e:
        print(f"❌ Qt playback test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n🎵 SidecarEQ - Plex Playback Test")
    print("=" * 60)
    
    # Step 1: Connect to Plex
    plex = test_plex_connection()
    if not plex:
        return 1
    
    # Step 2: Find music library
    music_section = list_music_libraries(plex)
    if not music_section:
        return 1
    
    # Step 3: Get sample track
    plex_track = get_sample_track(music_section)
    if not plex_track:
        return 1
    
    # Step 4: Get stream URL
    stream_url = test_plex_url(plex_track)
    if not stream_url:
        return 1
    
    # Step 5: Test audio source system
    track, playback_url = test_audio_source_system(plex_track, stream_url)
    if not playback_url:
        return 1
    
    # Step 6: Test Qt playback
    print("\n" + "=" * 60)
    print("Ready to test actual playback?")
    print("=" * 60)
    response = input("Test Qt Multimedia playback? (y/n): ").lower().strip()
    
    if response == 'y':
        test_qt_playback(playback_url)
    else:
        print("⏭️  Skipping playback test")
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ TEST COMPLETE!")
    print("=" * 60)
    print(f"\n📊 Summary:")
    print(f"   Track: {track.title}")
    print(f"   Artist: {track.artist}")
    print(f"   Track ID: {track.track_id}")
    print(f"   Playback URL: {playback_url[:60]}...")
    print(f"\n💡 You can now use this Track object in your queue!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
