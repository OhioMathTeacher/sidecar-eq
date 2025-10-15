"""Persistent local cache for artist and album metadata.

Stores fetched metadata (artist info, album info, lyrics) locally in JSON format
for offline access. This allows the app to work without internet and reduces
API calls.

Cache Structure:
- artists/
  - {artist_slug}.json - Artist biography, tags, similar artists, etc.
- albums/
  - {album_slug}.json - Album info, track list, etc.
- lyrics/
  - {track_hash}.json - Song lyrics (future feature)

Storage Estimate:
- Artist info: ~5-10 KB per artist
- Album info: ~3-5 KB per album
- Lyrics: ~2-5 KB per song
- 1000 artists + 1000 albums + 5000 songs ≈ 40-60 MB total
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


class MetadataCache:
    """Local persistent cache for online metadata."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize the metadata cache.
        
        Args:
            cache_dir: Directory for cache storage. If None, uses ~/.sidecar_eq/metadata_cache
        """
        if cache_dir is None:
            cache_dir = Path.home() / '.sidecar_eq' / 'metadata_cache'
        
        self.cache_dir = cache_dir
        self.artists_dir = cache_dir / 'artists'
        self.albums_dir = cache_dir / 'albums'
        self.lyrics_dir = cache_dir / 'lyrics'
        
        # Create directories if they don't exist
        for d in [self.artists_dir, self.albums_dir, self.lyrics_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def _make_slug(self, text: str) -> str:
        """Create a filesystem-safe slug from text.
        
        Args:
            text: Input text (artist name, album name, etc.)
            
        Returns:
            Lowercase alphanumeric slug with underscores
        """
        # Remove special chars, convert to lowercase
        slug = ''.join(c if c.isalnum() or c in ' -_' else '' for c in text.lower())
        # Replace spaces and hyphens with underscores
        slug = slug.replace(' ', '_').replace('-', '_')
        # Remove consecutive underscores
        while '__' in slug:
            slug = slug.replace('__', '_')
        return slug.strip('_')
    
    def _make_hash(self, *parts: str) -> str:
        """Create a hash from multiple parts for unique identification.
        
        Args:
            *parts: String parts to hash together
            
        Returns:
            Hex hash string (first 16 chars of SHA256)
        """
        combined = '|'.join(parts).encode('utf-8')
        return hashlib.sha256(combined).hexdigest()[:16]
    
    def get_artist(self, artist: str) -> Optional[Dict]:
        """Get cached artist metadata.
        
        Args:
            artist: Artist name
            
        Returns:
            Cached artist data dict or None if not found
        """
        slug = self._make_slug(artist)
        cache_file = self.artists_dir / f"{slug}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Include cache metadata
                data['_cached'] = True
                data['_cache_file'] = str(cache_file)
                return data
        except Exception as e:
            print(f"[MetadataCache] Failed to load artist cache for '{artist}': {e}")
            return None
    
    def put_artist(self, artist: str, data: Dict) -> bool:
        """Save artist metadata to cache.
        
        Args:
            artist: Artist name
            data: Artist metadata dictionary
            
        Returns:
            True if saved successfully, False otherwise
        """
        slug = self._make_slug(artist)
        cache_file = self.artists_dir / f"{slug}.json"
        
        try:
            # Add cache timestamp
            cache_data = data.copy()
            cache_data['_cached_at'] = datetime.now().isoformat()
            cache_data['_artist_slug'] = slug
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            print(f"[MetadataCache] Cached artist: {artist} -> {cache_file.name}")
            return True
        except Exception as e:
            print(f"[MetadataCache] Failed to cache artist '{artist}': {e}")
            return False
    
    def get_album(self, artist: str, album: str) -> Optional[Dict]:
        """Get cached album metadata.
        
        Args:
            artist: Artist name
            album: Album name
            
        Returns:
            Cached album data dict or None if not found
        """
        # Use hash for album since artist+album combination can be long
        album_hash = self._make_hash(artist, album)
        cache_file = self.albums_dir / f"{album_hash}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['_cached'] = True
                data['_cache_file'] = str(cache_file)
                return data
        except Exception as e:
            print(f"[MetadataCache] Failed to load album cache: {e}")
            return None
    
    def put_album(self, artist: str, album: str, data: Dict) -> bool:
        """Save album metadata to cache.
        
        Args:
            artist: Artist name
            album: Album name
            data: Album metadata dictionary
            
        Returns:
            True if saved successfully, False otherwise
        """
        album_hash = self._make_hash(artist, album)
        cache_file = self.albums_dir / f"{album_hash}.json"
        
        try:
            cache_data = data.copy()
            cache_data['_cached_at'] = datetime.now().isoformat()
            cache_data['_album_hash'] = album_hash
            cache_data['_artist'] = artist
            cache_data['_album'] = album
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            print(f"[MetadataCache] Cached album: {artist} - {album}")
            return True
        except Exception as e:
            print(f"[MetadataCache] Failed to cache album: {e}")
            return False
    
    def get_lyrics(self, artist: str, title: str) -> Optional[str]:
        """Get cached lyrics for a song.
        
        Args:
            artist: Artist name
            title: Song title
            
        Returns:
            Lyrics text or None if not found
        """
        lyrics_hash = self._make_hash(artist, title)
        cache_file = self.lyrics_dir / f"{lyrics_hash}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('lyrics', '')
        except Exception as e:
            print(f"[MetadataCache] Failed to load lyrics cache: {e}")
            return None
    
    def put_lyrics(self, artist: str, title: str, lyrics: str) -> bool:
        """Save lyrics to cache.
        
        Args:
            artist: Artist name
            title: Song title
            lyrics: Lyrics text
            
        Returns:
            True if saved successfully, False otherwise
        """
        lyrics_hash = self._make_hash(artist, title)
        cache_file = self.lyrics_dir / f"{lyrics_hash}.json"
        
        try:
            cache_data = {
                'artist': artist,
                'title': title,
                'lyrics': lyrics,
                '_cached_at': datetime.now().isoformat(),
                '_hash': lyrics_hash
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            print(f"[MetadataCache] Cached lyrics: {artist} - {title}")
            return True
        except Exception as e:
            print(f"[MetadataCache] Failed to cache lyrics: {e}")
            return False
    
    def get_cache_stats(self) -> Dict:
        """Get statistics about cache usage.
        
        Returns:
            Dictionary with cache stats (counts, total size, etc.)
        """
        stats = {
            'artists': len(list(self.artists_dir.glob('*.json'))),
            'albums': len(list(self.albums_dir.glob('*.json'))),
            'lyrics': len(list(self.lyrics_dir.glob('*.json'))),
        }
        
        # Calculate total size
        total_bytes = 0
        for d in [self.artists_dir, self.albums_dir, self.lyrics_dir]:
            for f in d.glob('*.json'):
                total_bytes += f.stat().st_size
        
        stats['total_size_mb'] = total_bytes / (1024 * 1024)
        stats['cache_dir'] = str(self.cache_dir)
        
        return stats


# Singleton instance
_cache = None

def get_metadata_cache() -> MetadataCache:
    """Get the global metadata cache instance.
    
    Returns:
        MetadataCache singleton
    """
    global _cache
    if _cache is None:
        _cache = MetadataCache()
    return _cache
