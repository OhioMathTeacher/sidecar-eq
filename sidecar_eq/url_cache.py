"""URL Cache Manager - Downloads and caches HTTP audio streams for local playback.

This module manages a temporary cache of downloaded audio files from HTTP URLs (Plex streams).
Cached files are stored with hash-based filenames and can be cleaned up automatically.
"""

import hashlib
import os
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional


class URLCache:
    """Manages cached downloads of HTTP audio streams."""
    
    def __init__(self, cache_dir: Optional[Path] = None, max_size_mb: int = 500):
        """Initialize URL cache.
        
        Args:
            cache_dir: Directory for cache storage (defaults to system temp)
            max_size_mb: Maximum cache size in megabytes
        """
        if cache_dir is None:
            # Use system temp directory
            self.cache_dir = Path(tempfile.gettempdir()) / "sidecar_eq_cache"
        else:
            self.cache_dir = Path(cache_dir)
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        
        print(f"[URLCache] Cache directory: {self.cache_dir}")
        print(f"[URLCache] Max size: {max_size_mb} MB")
    
    def _url_to_filename(self, url: str) -> str:
        """Convert URL to a stable cache filename using hash."""
        # Create hash of URL for stable filename
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        
        # Try to extract file extension from URL
        url_path = url.split('?')[0]  # Remove query params
        ext = Path(url_path).suffix
        if not ext or len(ext) > 5:
            ext = '.cache'
        
        return f"{url_hash}{ext}"
    
    def get_cached_path(self, url: str) -> Optional[Path]:
        """Get cached file path if it exists.
        
        Args:
            url: The HTTP URL
            
        Returns:
            Path to cached file, or None if not cached
        """
        filename = self._url_to_filename(url)
        cache_path = self.cache_dir / filename
        
        if cache_path.exists():
            return cache_path
        return None
    
    def download_and_cache(self, url: str, progress_callback=None) -> Optional[Path]:
        """Download URL and cache it locally.
        
        Args:
            url: The HTTP URL to download
            progress_callback: Optional callback(bytes_downloaded, total_bytes)
            
        Returns:
            Path to cached file, or None on error
        """
        # Check if already cached
        cached = self.get_cached_path(url)
        if cached:
            print(f"[URLCache] ✅ Using cached file: {cached.name}")
            return cached
        
        # Download to cache
        filename = self._url_to_filename(url)
        cache_path = self.cache_dir / filename
        temp_path = cache_path.with_suffix(cache_path.suffix + '.tmp')
        
        try:
            print(f"[URLCache] Downloading: {url[:60]}...")
            
            # Download with progress tracking
            def reporthook(block_num, block_size, total_size):
                if progress_callback and total_size > 0:
                    downloaded = block_num * block_size
                    progress_callback(downloaded, total_size)
            
            urllib.request.urlretrieve(url, temp_path, reporthook=reporthook)
            
            # Move temp file to final location
            temp_path.rename(cache_path)
            
            size_mb = cache_path.stat().st_size / (1024 * 1024)
            print(f"[URLCache] ✅ Downloaded: {cache_path.name} ({size_mb:.1f} MB)")
            
            # Clean up if cache is too large
            self._cleanup_if_needed()
            
            return cache_path
            
        except Exception as e:
            print(f"[URLCache] ❌ Download failed: {e}")
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()
            return None
    
    def _cleanup_if_needed(self):
        """Remove oldest cached files if cache exceeds max size."""
        # Get all cache files with their sizes and modification times
        cache_files = []
        total_size = 0
        
        for file_path in self.cache_dir.glob('*'):
            if file_path.is_file() and not file_path.name.endswith('.tmp'):
                size = file_path.stat().st_size
                mtime = file_path.stat().st_mtime
                cache_files.append((file_path, size, mtime))
                total_size += size
        
        # If under limit, nothing to do
        if total_size <= self.max_size_bytes:
            return
        
        print(f"[URLCache] Cache size {total_size / (1024*1024):.1f} MB exceeds limit, cleaning up...")
        
        # Sort by modification time (oldest first)
        cache_files.sort(key=lambda x: x[2])
        
        # Remove oldest files until under limit
        for file_path, size, _ in cache_files:
            if total_size <= self.max_size_bytes:
                break
            
            print(f"[URLCache] Removing old cache file: {file_path.name}")
            file_path.unlink()
            total_size -= size
    
    def clear_all(self):
        """Remove all cached files."""
        count = 0
        for file_path in self.cache_dir.glob('*'):
            if file_path.is_file():
                file_path.unlink()
                count += 1
        
        print(f"[URLCache] Cleared {count} cached files")
    
    def get_cache_size(self) -> int:
        """Get total size of cache in bytes."""
        total = 0
        for file_path in self.cache_dir.glob('*'):
            if file_path.is_file() and not file_path.name.endswith('.tmp'):
                total += file_path.stat().st_size
        return total
