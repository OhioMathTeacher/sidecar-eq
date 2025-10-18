#!/usr/bin/env python3
"""Test script for online metadata fetching."""

from sidecar_eq.online_metadata import get_metadata_fetcher

def test_artist_lookup():
    """Test looking up artist info."""
    fetcher = get_metadata_fetcher()
    
    print("=" * 80)
    print("Testing Online Metadata Fetching")
    print("=" * 80)
    
    # Test with a well-known artist
    test_artists = [
        ("Bob Marley", "Three Little Birds"),
        ("The Beatles", "Hey Jude"),
        ("Pink Floyd", "Comfortably Numb"),
    ]
    
    for artist, track in test_artists:
        print(f"\n\nFetching info for: {artist} - {track}")
        print("-" * 80)
        
        info = fetcher.fetch_artist_info(artist, track)
        
        if info:
            print(f"✓ Found data from: {info.get('source', 'Unknown')}")
            print(f"  Name: {info.get('name', 'N/A')}")
            print(f"  Formed: {info.get('formed', 'N/A')}")
            print(f"  Country: {info.get('country', 'N/A')}")
            print(f"  Type: {info.get('type', 'N/A')}")
            print(f"  Listeners: {info.get('listeners', 0):,}")
            print(f"  Play Count: {info.get('play_count', 0):,}")
            
            bio = info.get('bio', '')
            if bio:
                print(f"\n  Bio snippet: {bio[:200]}...")
            
            tags = info.get('tags', [])
            if tags:
                print(f"\n  Tags: {', '.join(tags)}")
            
            similar = info.get('similar_artists', [])
            if similar:
                print(f"\n  Similar: {', '.join(similar)}")
            
            url = info.get('url', '')
            if url:
                print(f"\n  URL: {url}")
        else:
            print("✗ No data found")
    
    print("\n" + "=" * 80)
    print("Test completed!")
    print("=" * 80)

if __name__ == "__main__":
    test_artist_lookup()
