"""Hierarchical music library for Sidecar EQ.

Provides Song/Album/Artist/Library classes for organizing music collections.
Designed with stem separation in mind from day 1 (v2.0 feature).

The library structure:
    Library
      └─ Artist
          └─ Album
              └─ Song (with optional stems)

Each Song can have separated stems cached on disk:
    ~/.sidecar_eq/stems/{song_hash}/
        ├─ vocals.wav
        ├─ drums.wav
        ├─ bass.wav
        ├─ guitar.wav
        └─ other.wav
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from . import store


class Song:
    """Represents a single music track.
    
    Attributes:
        path: Absolute path to the original audio file
        title: Song title
        artist: Artist name
        album: Album name
        play_count: Number of times played
        rating: User rating (0-5 stars)
        last_played: ISO timestamp of last play
        stem_settings: Per-stem volume/mute settings (for v2.0)
    """
    
    def __init__(self, path: str, title: str, artist: str, album: str = ""):
        """Initialize a Song.
        
        Args:
            path: Absolute path to audio file
            title: Song title
            artist: Artist name
            album: Album name (optional)
        """
        self.path = path
        self.title = title or "Unknown"
        self.artist = artist or "Unknown Artist"
        self.album = album or "Unknown Album"
        
        # Load persisted settings from store
        settings = store.get_record(path)
        
        if settings:
            self.play_count = settings.get('play_count', 0)
            self.rating = settings.get('rating', 0)
            self.last_played = settings.get('last_played', None)
            
            # Stem settings (v2.0 feature - stored but not used yet)
            self.stem_settings = settings.get('stem_settings', {
                'vocals': {'volume': 1.0, 'muted': False, 'eq': None},
                'drums': {'volume': 1.0, 'muted': False, 'eq': None},
                'bass': {'volume': 1.0, 'muted': False, 'eq': None},
                'guitar': {'volume': 1.0, 'muted': False, 'eq': None},
                'other': {'volume': 1.0, 'muted': False, 'eq': None},
            })
        else:
            self.play_count = 0
            self.rating = 0
            self.last_played = None
            self.stem_settings = {
                'vocals': {'volume': 1.0, 'muted': False, 'eq': None},
                'drums': {'volume': 1.0, 'muted': False, 'eq': None},
                'bass': {'volume': 1.0, 'muted': False, 'eq': None},
                'guitar': {'volume': 1.0, 'muted': False, 'eq': None},
                'other': {'volume': 1.0, 'muted': False, 'eq': None},
            }
        
        # Cache directory for stems (lazy-loaded)
        self._stem_cache_dir = None
    
    @property
    def stem_cache_dir(self) -> Path:
        """Get stem cache directory for this song.
        
        Returns:
            Path to stem cache directory (may not exist yet)
        """
        if not self._stem_cache_dir:
            # Use MD5 hash of path to create safe directory name
            path_hash = hashlib.md5(self.path.encode()).hexdigest()[:16]
            self._stem_cache_dir = Path.home() / ".sidecar_eq" / "stems" / path_hash
        return self._stem_cache_dir
    
    @property
    def has_stems(self) -> bool:
        """Check if stems have been separated and cached.
        
        Returns:
            True if all 5 stem files exist
        """
        if not self.stem_cache_dir.exists():
            return False
        
        required_stems = ['vocals.wav', 'drums.wav', 'bass.wav', 'guitar.wav', 'other.wav']
        return all((self.stem_cache_dir / stem).exists() for stem in required_stems)
    
    def get_stem_path(self, stem_name: str) -> Path:
        """Get path to a specific stem file.
        
        Args:
            stem_name: 'vocals', 'drums', 'bass', 'guitar', or 'other'
            
        Returns:
            Path to stem file (may not exist yet)
        """
        return self.stem_cache_dir / f"{stem_name}.wav"
    
    @property
    def has_eq(self) -> bool:
        """Check if this song has custom EQ settings saved.
        
        Returns:
            True if EQ settings exist in store
        """
        settings = store.get_record(self.path)
        if settings and 'eq' in settings:
            eq = settings['eq']
            return eq is not None and len(eq) > 0
        return False
    
    def to_dict(self) -> dict:
        """Serialize song to dictionary for JSON storage.
        
        Returns:
            Dictionary representation
        """
        return {
            'path': self.path,
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'play_count': self.play_count,
            'rating': self.rating,
            'last_played': self.last_played,
            'has_stems': self.has_stems,
            'stem_settings': self.stem_settings,
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'Song':
        """Deserialize song from dictionary.
        
        Args:
            data: Dictionary from JSON
            
        Returns:
            Song instance
        """
        song = Song(
            path=data['path'],
            title=data.get('title', 'Unknown'),
            artist=data.get('artist', 'Unknown Artist'),
            album=data.get('album', 'Unknown Album')
        )
        
        # Restore saved values
        song.play_count = data.get('play_count', 0)
        song.rating = data.get('rating', 0)
        song.last_played = data.get('last_played')
        song.stem_settings = data.get('stem_settings', song.stem_settings)
        
        return song
    
    def __repr__(self):
        return f"Song('{self.title}' by {self.artist})"


class Album:
    """Represents a music album (collection of songs by same artist).
    
    Attributes:
        title: Album title
        artist: Artist name
        songs: List of Song objects
    """
    
    def __init__(self, title: str, artist: str):
        """Initialize an Album.
        
        Args:
            title: Album title
            artist: Artist name
        """
        self.title = title or "Unknown Album"
        self.artist = artist or "Unknown Artist"
        self.songs: List[Song] = []
    
    def add_song(self, song: Song):
        """Add a song to this album.
        
        Args:
            song: Song to add
        """
        if song not in self.songs:
            self.songs.append(song)
    
    @property
    def total_plays(self) -> int:
        """Calculate total plays across all songs in album.
        
        Returns:
            Sum of play counts
        """
        return sum(song.play_count for song in self.songs)
    
    @property
    def average_rating(self) -> float:
        """Calculate average rating of rated songs in album.
        
        Returns:
            Average rating (0-5), or 0 if no songs are rated
        """
        rated_songs = [s.rating for s in self.songs if s.rating > 0]
        if not rated_songs:
            return 0.0
        return sum(rated_songs) / len(rated_songs)
    
    @property
    def song_count(self) -> int:
        """Get number of songs in album.
        
        Returns:
            Song count
        """
        return len(self.songs)
    
    def to_dict(self) -> dict:
        """Serialize album to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'title': self.title,
            'artist': self.artist,
            'songs': [song.to_dict() for song in self.songs]
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'Album':
        """Deserialize album from dictionary.
        
        Args:
            data: Dictionary from JSON
            
        Returns:
            Album instance
        """
        album = Album(
            title=data.get('title', 'Unknown Album'),
            artist=data.get('artist', 'Unknown Artist')
        )
        
        for song_data in data.get('songs', []):
            album.add_song(Song.from_dict(song_data))
        
        return album
    
    def __repr__(self):
        return f"Album('{self.title}' by {self.artist}, {len(self.songs)} songs)"


class Artist:
    """Represents a music artist (collection of albums).
    
    Attributes:
        name: Artist name
        albums: Dictionary of album_title -> Album
    """
    
    def __init__(self, name: str):
        """Initialize an Artist.
        
        Args:
            name: Artist name
        """
        self.name = name or "Unknown Artist"
        self.albums: Dict[str, Album] = {}
    
    def add_album(self, album: Album):
        """Add an album to this artist.
        
        Args:
            album: Album to add
        """
        if album.title not in self.albums:
            self.albums[album.title] = album
    
    def get_or_create_album(self, album_title: str) -> Album:
        """Get existing album or create new one.
        
        Args:
            album_title: Album title
            
        Returns:
            Album instance
        """
        if album_title not in self.albums:
            self.albums[album_title] = Album(album_title, self.name)
        return self.albums[album_title]
    
    @property
    def total_plays(self) -> int:
        """Calculate total plays across all albums.
        
        Returns:
            Sum of all album plays
        """
        return sum(album.total_plays for album in self.albums.values())
    
    @property
    def song_count(self) -> int:
        """Get total number of songs by this artist.
        
        Returns:
            Total song count across all albums
        """
        return sum(album.song_count for album in self.albums.values())
    
    @property
    def album_count(self) -> int:
        """Get number of albums by this artist.
        
        Returns:
            Album count
        """
        return len(self.albums)
    
    @property
    def top_album(self) -> Optional[Album]:
        """Get most-played album by this artist.
        
        Returns:
            Album with most plays, or None if no albums
        """
        if not self.albums:
            return None
        return max(self.albums.values(), key=lambda a: a.total_plays)
    
    def get_all_songs(self) -> List[Song]:
        """Get all songs by this artist across all albums.
        
        Returns:
            List of all songs
        """
        all_songs = []
        for album in self.albums.values():
            all_songs.extend(album.songs)
        return all_songs
    
    def to_dict(self) -> dict:
        """Serialize artist to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'name': self.name,
            'albums': {title: album.to_dict() for title, album in self.albums.items()}
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'Artist':
        """Deserialize artist from dictionary.
        
        Args:
            data: Dictionary from JSON
            
        Returns:
            Artist instance
        """
        artist = Artist(data.get('name', 'Unknown Artist'))
        
        for album_data in data.get('albums', {}).values():
            artist.add_album(Album.from_dict(album_data))
        
        return artist
    
    def __repr__(self):
        return f"Artist('{self.name}', {len(self.albums)} albums, {self.song_count} songs)"


class Library:
    """Top-level music library (collection of artists).
    
    Provides hierarchical organization and search capabilities.
    
    Attributes:
        artists: Dictionary of artist_name -> Artist
        library_path: Path to library.json file
    """
    
    def __init__(self):
        """Initialize the Library."""
        self.artists: Dict[str, Artist] = {}
        
        # Library storage location
        config_dir = Path.home() / ".sidecar_eq"
        config_dir.mkdir(exist_ok=True)
        self.library_path = config_dir / "library.json"
        
        # Load existing library if available
        self._load()
    
    def add_song(self, song: Song):
        """Add a song to the library (creates artist/album as needed).
        
        Args:
            song: Song to add
        """
        # Get or create artist
        if song.artist not in self.artists:
            self.artists[song.artist] = Artist(song.artist)
        
        artist = self.artists[song.artist]
        
        # Get or create album
        album = artist.get_or_create_album(song.album)
        
        # Add song to album
        album.add_song(song)
    
    def get_song_by_path(self, path: str) -> Optional[Song]:
        """Find a song by its file path.
        
        Args:
            path: File path to search for
            
        Returns:
            Song instance or None if not found
        """
        for artist in self.artists.values():
            for album in artist.albums.values():
                for song in album.songs:
                    if song.path == path:
                        return song
        return None
    
    def get_top_songs(self, limit: int = 10) -> List[Song]:
        """Get top songs by play count.
        
        Args:
            limit: Maximum number of songs to return
            
        Returns:
            List of top songs, sorted by play count descending
        """
        all_songs = []
        for artist in self.artists.values():
            all_songs.extend(artist.get_all_songs())
        
        return sorted(all_songs, key=lambda s: s.play_count, reverse=True)[:limit]
    
    def get_top_albums(self, limit: int = 5) -> List[Album]:
        """Get top albums by total plays.
        
        Args:
            limit: Maximum number of albums to return
            
        Returns:
            List of top albums, sorted by total plays descending
        """
        all_albums = []
        for artist in self.artists.values():
            all_albums.extend(artist.albums.values())
        
        return sorted(all_albums, key=lambda a: a.total_plays, reverse=True)[:limit]
    
    def get_top_artists(self, limit: int = 5) -> List[Artist]:
        """Get top artists by total plays.
        
        Args:
            limit: Maximum number of artists to return
            
        Returns:
            List of top artists, sorted by total plays descending
        """
        return sorted(self.artists.values(), key=lambda a: a.total_plays, reverse=True)[:limit]
    
    def get_recently_played(self, limit: int = 10) -> List[Song]:
        """Get recently played songs.
        
        Args:
            limit: Maximum number of songs to return
            
        Returns:
            List of songs, sorted by last_played descending
        """
        all_songs = []
        for artist in self.artists.values():
            all_songs.extend(artist.get_all_songs())
        
        # Filter songs that have been played
        played_songs = [s for s in all_songs if s.last_played]
        
        return sorted(played_songs, key=lambda s: s.last_played or '', reverse=True)[:limit]
    
    def search(self, query: str, limit: int = 50) -> Dict[str, List]:
        """Search library for artists, albums, and songs.
        
        Uses fuzzy matching across all fields.
        
        Args:
            query: Search query string
            limit: Maximum results per category
            
        Returns:
            Dictionary with 'artists', 'albums', 'songs' keys containing results
        """
        query_lower = query.lower()
        
        matching_artists = []
        matching_albums = []
        matching_songs = []
        
        for artist in self.artists.values():
            artist_matches = query_lower in artist.name.lower()
            
            if artist_matches:
                matching_artists.append(artist)
            
            for album in artist.albums.values():
                album_matches = (
                    query_lower in album.title.lower() or
                    artist_matches  # Include if artist matches
                )
                
                if album_matches:
                    matching_albums.append(album)
                
                for song in album.songs:
                    song_matches = (
                        query_lower in song.title.lower() or
                        artist_matches or
                        album_matches
                    )
                    
                    if song_matches:
                        matching_songs.append(song)
        
        # Sort results by relevance
        # Artists: by total plays
        matching_artists.sort(key=lambda a: a.total_plays, reverse=True)
        
        # Albums: by total plays
        matching_albums.sort(key=lambda a: a.total_plays, reverse=True)
        
        # Songs: by play count
        matching_songs.sort(key=lambda s: s.play_count, reverse=True)
        
        return {
            'artists': matching_artists[:limit],
            'albums': matching_albums[:limit],
            'songs': matching_songs[:limit],
        }
    
    @property
    def total_songs(self) -> int:
        """Get total number of songs in library.
        
        Returns:
            Total song count
        """
        return sum(artist.song_count for artist in self.artists.values())
    
    @property
    def total_albums(self) -> int:
        """Get total number of albums in library.
        
        Returns:
            Total album count
        """
        return sum(artist.album_count for artist in self.artists.values())
    
    @property
    def total_artists(self) -> int:
        """Get total number of artists in library.
        
        Returns:
            Artist count
        """
        return len(self.artists)
    
    def save(self):
        """Save library to disk (library.json)."""
        try:
            data = {
                'version': '1.0',
                'saved_at': datetime.now().isoformat(),
                'stats': {
                    'total_artists': self.total_artists,
                    'total_albums': self.total_albums,
                    'total_songs': self.total_songs,
                },
                'artists': {name: artist.to_dict() for name, artist in self.artists.items()}
            }
            
            with open(self.library_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"[Library] Saved {self.total_songs} songs, {self.total_albums} albums, {self.total_artists} artists")
        except Exception as e:
            print(f"[Library] Failed to save: {e}")
    
    def _load(self):
        """Load library from disk."""
        if not self.library_path.exists():
            print("[Library] No existing library found, starting fresh")
            return
        
        try:
            with open(self.library_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Load artists
            for artist_name, artist_data in data.get('artists', {}).items():
                self.artists[artist_name] = Artist.from_dict(artist_data)
            
            print(f"[Library] Loaded {self.total_songs} songs, {self.total_albums} albums, {self.total_artists} artists")
        except Exception as e:
            print(f"[Library] Failed to load library: {e}")
            self.artists = {}
    
    def clear(self):
        """Clear the entire library."""
        self.artists = {}
        self.save()
    
    def __repr__(self):
        return f"Library({self.total_artists} artists, {self.total_albums} albums, {self.total_songs} songs)"
