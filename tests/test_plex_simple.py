#!/usr/bin/env python3
"""Quick test of Plex connection using different methods."""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from plexapi.myplex import MyPlexAccount

# Get token
token = os.getenv('PLEX_TOKEN', '')
print(f"Using token: {token[:10]}...")

try:
    # Method 1: Connect via MyPlex (cloud)
    print("\n1️⃣ Trying MyPlex (cloud) connection...")
    account = MyPlexAccount(token=token)
    print(f"✅ Logged in as: {account.username}")
    
    # List resources
    print("\n📋 Your Plex resources:")
    for resource in account.resources():
        if resource.provides == 'server':
            print(f"\n   🖥️  {resource.name}")
            print(f"      Owner: {resource.owned}")
            print(f"      Product: {resource.product}")
            
            # Get connections
            if hasattr(resource, 'connections'):
                for conn in resource.connections:
                    local = "🏠" if conn.local else "🌐"
                    print(f"      {local} {conn.uri}")
    
    # Connect to first server
    print("\n2️⃣ Connecting to your Plex server...")
    # Or just use:
    servers = [r for r in account.resources() if r.provides == 'server']
    if servers:
        print(f"\n   Connecting to: {servers[0].name}")
        plex = servers[0].connect()
        print(f"✅ Connected to: {plex.friendlyName}")
        
        # List music sections
        print("\n3️⃣ Finding music libraries...")
        music_sections = [s for s in plex.library.sections() if s.type == 'artist']
        print(f"✅ Found {len(music_sections)} music library(ies)")
        
        if music_sections:
            section = music_sections[0]
            print(f"\n   📚 {section.title}: {section.totalSize} items")
            
            # Get a sample track
            tracks = section.searchTracks(limit=3)
            if tracks:
                print(f"\n4️⃣ Sample tracks:")
                for track in tracks:
                    print(f"   🎵 {track.title}")
                    print(f"      Artist: {track.grandparentTitle}")
                    
                    # Get stream URL
                    stream_url = track.getStreamURL()
                    print(f"      Stream URL: {stream_url[:80]}...")
                    print(f"      ✅ Ready to play!")
                    break
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
