"""Audio Source Plugin System for SidecarEQ.

This module provides a universal, plugin-based architecture for handling
multiple audio sources (local files, streaming URLs, Plex, S3, etc.).

Design Principles:
- One unified Player interface
- Pluggable audio sources
- Easy to add new formats
- Source-agnostic metadata handling

Architecture:
    Player
      ↓
    AudioRepository (picks best source)
      ↓
    AudioSource (plugin interface)
      ↓
    [LocalFileSource, PlexSource, S3Source, StreamSource, ...]
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, List, Any, Union
from dataclasses import dataclass, field
import hashlib


# ============================================================================
# Track ID System - Universal identifier independent of source
# ============================================================================

def generate_track_id(title: str, artist: str, album: str) -> str:
    """Generate a unique, stable track ID from metadata.
    
    This ID stays constant even if the file moves, gets renamed,
    or is available from multiple sources.
    
    Args:
        title: Song title
        artist: Artist name
        album: Album name
        
    Returns:
        16-character hex string (MD5 hash)
        
    Example:
        >>> generate_track_id("Money", "Pink Floyd", "Dark Side of the Moon")
        'a1b2c3d4e5f6g7h8'
    """
    # Normalize metadata for consistent IDs
    normalized = f"{title}|{artist}|{album}".lower().strip()
    hash_obj = hashlib.md5(normalized.encode('utf-8'))
    return hash_obj.hexdigest()[:16]


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class AudioSourceInfo:
    """Information about a single audio source for a track.
    
    A track can have multiple sources (local file + Plex + S3 backup).
    The AudioRepository picks the best available source.
    
    Attributes:
        source_type: Type identifier ("local", "plex", "s3", "stream", "youtube")
        location: How to access this source (path, URL, etc.)
        quality: Audio quality info (bitrate, format, sample_rate)
        available: Whether this source is currently accessible
        metadata: Source-specific metadata
    """
    source_type: str  # "local" | "plex" | "s3" | "stream" | "youtube" | "spotify"
    location: str  # File path, URL, S3 key, etc.
    quality: Dict[str, Any]  # {"bitrate": 320, "format": "flac", "sample_rate": 44100}
    available: bool = True
    metadata: Optional[Dict[str, Any]] = None  # Source-specific extras
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Track:
    """Universal track representation.
    
    Contains metadata and multiple possible audio sources.
    The player doesn't care which source is used.
    
    Attributes:
        track_id: Unique identifier (independent of source)
        title: Song title
        artist: Artist name
        album: Album name
        sources: List of available audio sources
        metadata: Additional track metadata
    """
    track_id: str
    title: str
    artist: str
    album: str
    sources: List[AudioSourceInfo]
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @classmethod
    def from_metadata(cls, title: str, artist: str, album: str, 
                      sources: List[AudioSourceInfo], **metadata) -> 'Track':
        """Create a track from metadata.
        
        Args:
            title: Song title
            artist: Artist name
            album: Album name
            sources: List of available audio sources
            **metadata: Additional metadata (year, genre, etc.)
            
        Returns:
            Track instance with generated track_id
        """
        track_id = generate_track_id(title, artist, album)
        return cls(
            track_id=track_id,
            title=title,
            artist=artist,
            album=album,
            sources=sources,
            metadata=metadata
        )
    
    def get_best_source(self) -> Optional[AudioSourceInfo]:
        """Get the best available source for playback.
        
        Priority order:
        1. Local files (fastest, no network)
        2. Plex (local network, fast)
        3. S3/Cloud (requires internet)
        4. Streaming services (requires auth)
        
        Returns:
            Best available AudioSourceInfo or None
        """
        # Define priority order
        priority = ["local", "plex", "s3", "stream", "youtube", "spotify"]
        
        for source_type in priority:
            for source in self.sources:
                if source.source_type == source_type and source.available:
                    return source
        
        # Fallback: return any available source
        for source in self.sources:
            if source.available:
                return source
        
        return None


# ============================================================================
# Audio Source Plugin Interface
# ============================================================================

class AudioSource(ABC):
    """Abstract base class for audio source plugins.
    
    Each audio source (local files, Plex, S3, etc.) implements this interface.
    The Player uses these plugins without knowing the underlying source type.
    
    To add a new audio source:
    1. Subclass AudioSource
    2. Implement all abstract methods
    3. Register in AudioRepository
    4. Done! Player automatically supports it.
    """
    
    @abstractmethod
    def can_handle(self, source_info: AudioSourceInfo) -> bool:
        """Check if this plugin can handle the given source.
        
        Args:
            source_info: Audio source information
            
        Returns:
            True if this plugin can handle this source
        """
        pass
    
    @abstractmethod
    def get_playback_url(self, source_info: AudioSourceInfo) -> str:
        """Get a playback URL for the audio source.
        
        This should return a URL that Qt Multimedia can play:
        - Local files: "file:///path/to/file.mp3"
        - HTTP streams: "http://server.com/stream.mp3"
        - Signed URLs: "https://s3.amazonaws.com/...?signature=..."
        
        Args:
            source_info: Audio source information
            
        Returns:
            Playback URL string
        """
        pass
    
    @abstractmethod
    def is_available(self, source_info: AudioSourceInfo) -> bool:
        """Check if this source is currently available.
        
        Args:
            source_info: Audio source information
            
        Returns:
            True if source is accessible right now
        """
        pass
    
    def get_stream_metadata(self, source_info: AudioSourceInfo) -> Dict[str, Any]:
        """Get additional metadata about the stream (optional).
        
        Args:
            source_info: Audio source information
            
        Returns:
            Dictionary with stream info (bitrate, format, etc.)
        """
        return {}


# ============================================================================
# Built-in Audio Source Plugins
# ============================================================================

class LocalFileSource(AudioSource):
    """Plugin for local audio files."""
    
    def can_handle(self, source_info: AudioSourceInfo) -> bool:
        return source_info.source_type == "local"
    
    def get_playback_url(self, source_info: AudioSourceInfo) -> str:
        """Convert local path to file:// URL."""
        path = Path(source_info.location)
        # Qt expects file:// URLs for local files
        return path.as_uri()
    
    def is_available(self, source_info: AudioSourceInfo) -> bool:
        """Check if file exists on disk."""
        return Path(source_info.location).exists()


class PlexSource(AudioSource):
    """Plugin for Plex Media Server streams."""
    
    def can_handle(self, source_info: AudioSourceInfo) -> bool:
        return source_info.source_type == "plex"
    
    def get_playback_url(self, source_info: AudioSourceInfo) -> str:
        """Return Plex stream URL with auth token."""
        # Plex URLs are already in the right format
        # They include the auth token: http://plex:32400/...?X-Plex-Token=xyz
        return source_info.location
    
    def is_available(self, source_info: AudioSourceInfo) -> bool:
        """Check if Plex server is reachable."""
        # TODO: Ping Plex server or check cache
        # For now, assume available if metadata says so
        return source_info.available


class StreamSource(AudioSource):
    """Plugin for HTTP/HTTPS audio streams."""
    
    def can_handle(self, source_info: AudioSourceInfo) -> bool:
        return source_info.source_type == "stream"
    
    def get_playback_url(self, source_info: AudioSourceInfo) -> str:
        """Return stream URL directly."""
        return source_info.location
    
    def is_available(self, source_info: AudioSourceInfo) -> bool:
        """Assume streams are available (could add ping check)."""
        return True


class S3Source(AudioSource):
    """Plugin for S3/cloud storage audio files."""
    
    def __init__(self, s3_client=None):
        """Initialize with optional S3 client.
        
        Args:
            s3_client: boto3 S3 client (optional, created if needed)
        """
        self.s3_client = s3_client
    
    def can_handle(self, source_info: AudioSourceInfo) -> bool:
        return source_info.source_type == "s3"
    
    def get_playback_url(self, source_info: AudioSourceInfo) -> str:
        """Generate presigned S3 URL for playback."""
        # Parse S3 location: "s3://bucket/key/path.mp3"
        if not source_info.location.startswith("s3://"):
            return source_info.location
        
        # Extract bucket and key
        parts = source_info.location[5:].split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        
        # Generate presigned URL (valid for 1 hour)
        if self.s3_client:
            try:
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket, 'Key': key},
                    ExpiresIn=3600  # 1 hour
                )
                return url
            except Exception as e:
                print(f"[S3Source] Failed to generate presigned URL: {e}")
        
        # Fallback: return public S3 URL (won't work for private buckets)
        return f"https://{bucket}.s3.amazonaws.com/{key}"
    
    def is_available(self, source_info: AudioSourceInfo) -> bool:
        """Check if S3 object exists."""
        # TODO: Add S3 head_object check
        # For now, assume available
        return True


# ============================================================================
# Audio Repository - Source Manager
# ============================================================================

class AudioRepository:
    """Central registry for audio source plugins.
    
    The repository:
    1. Manages registered audio source plugins
    2. Selects best available source for a track
    3. Provides unified playback URLs to the Player
    
    Usage:
        repo = AudioRepository()
        repo.register_source(LocalFileSource())
        repo.register_source(PlexSource())
        
        # Later:
        url = repo.get_playback_url(track)
        player.play(url)
    """
    
    def __init__(self):
        """Initialize with default plugins."""
        self.sources: List[AudioSource] = []
        
        # Register built-in sources
        self.register_source(LocalFileSource())
        self.register_source(PlexSource())
        self.register_source(StreamSource())
        self.register_source(S3Source())
    
    def register_source(self, source: AudioSource):
        """Register a new audio source plugin.
        
        Args:
            source: AudioSource plugin instance
        """
        self.sources.append(source)
    
    def get_playback_url(self, track: Track) -> Optional[str]:
        """Get a playback URL for a track.
        
        Automatically selects the best available source and
        returns a URL the player can use.
        
        Args:
            track: Track to play
            
        Returns:
            Playback URL string or None if no sources available
        """
        # Get best source for this track
        source_info = track.get_best_source()
        if not source_info:
            return None
        
        # Find plugin that can handle this source
        for source_plugin in self.sources:
            if source_plugin.can_handle(source_info):
                # Check availability
                if not source_plugin.is_available(source_info):
                    continue
                
                # Get playback URL
                try:
                    return source_plugin.get_playback_url(source_info)
                except Exception as e:
                    print(f"[AudioRepository] Failed to get URL from {type(source_plugin).__name__}: {e}")
                    continue
        
        return None
    
    def check_availability(self, track: Track) -> Dict[str, bool]:
        """Check which sources are currently available for a track.
        
        Args:
            track: Track to check
            
        Returns:
            Dictionary mapping source type to availability
        """
        availability = {}
        
        for source_info in track.sources:
            for source_plugin in self.sources:
                if source_plugin.can_handle(source_info):
                    available = source_plugin.is_available(source_info)
                    availability[source_info.source_type] = available
                    break
        
        return availability


# ============================================================================
# Helper Functions for Backward Compatibility
# ============================================================================

def create_track_from_path(file_path: str, title: Optional[str] = None, 
                          artist: Optional[str] = None, album: Optional[str] = None) -> Track:
    """Create a Track from a local file path (backward compatibility).
    
    Args:
        file_path: Path to local audio file
        title: Song title (extracted from file if not provided)
        artist: Artist name
        album: Album name
        
    Returns:
        Track with local file source
    """
    # If metadata not provided, extract from file
    if not title:
        title = Path(file_path).stem
    if not artist:
        artist = "Unknown Artist"
    if not album:
        album = "Unknown Album"
    
    # Create source info for local file
    source = AudioSourceInfo(
        source_type="local",
        location=str(file_path),
        quality={
            "format": Path(file_path).suffix[1:],
        }
    )
    
    # Create track
    return Track.from_metadata(
        title=title,
        artist=artist,
        album=album,
        sources=[source]
    )


def create_track_from_plex(stream_url: str, title: str, artist: str, album: str,
                          **metadata) -> Track:
    """Create a Track from Plex stream info.
    
    Args:
        stream_url: Plex stream URL with auth token
        title: Song title
        artist: Artist name
        album: Album name
        **metadata: Additional metadata
        
    Returns:
        Track with Plex source
    """
    source = AudioSourceInfo(
        source_type="plex",
        location=stream_url,
        quality=metadata.get('quality', {}),
        metadata=metadata
    )
    
    return Track.from_metadata(
        title=title,
        artist=artist,
        album=album,
        sources=[source],
        **metadata
    )


# ============================================================================
# Usage Example
# ============================================================================

if __name__ == "__main__":
    # Example: Track available from multiple sources
    track = Track.from_metadata(
        title="Money",
        artist="Pink Floyd",
        album="Dark Side of the Moon",
        sources=[
            AudioSourceInfo(
                source_type="local",
                location="/Music/Pink Floyd/Money.flac",
                quality={"bitrate": 1411, "format": "flac", "sample_rate": 44100}
            ),
            AudioSourceInfo(
                source_type="plex",
                location="http://plex.local:32400/library/metadata/12345?X-Plex-Token=abc",
                quality={"bitrate": 320, "format": "mp3", "sample_rate": 44100}
            ),
            AudioSourceInfo(
                source_type="s3",
                location="s3://my-music-backup/pink-floyd/money.flac",
                quality={"bitrate": 1411, "format": "flac", "sample_rate": 44100}
            ),
        ],
        year=1973,
        genre="Progressive Rock"
    )
    
    print(f"Track ID: {track.track_id}")
    print(f"Title: {track.title}")
    print(f"Available sources: {len(track.sources)}")
    
    # Get playback URL
    repo = AudioRepository()
    url = repo.get_playback_url(track)
    print(f"Playback URL: {url}")
    
    # Check availability
    availability = repo.check_availability(track)
    print(f"Source availability: {availability}")
