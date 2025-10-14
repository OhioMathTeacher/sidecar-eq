"""Music library indexer for Sidecar EQ.

Scans local and network folders to build a searchable index of audio files.
Extracts metadata (title, artist, album) and integrates with per-track
settings (play count, EQ status).

The index is saved to ~/.sidecar_eq/library_index.json for fast startup.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from mutagen import File as MutagenFile

from . import store


# Supported audio file extensions
AUDIO_EXTS = {".wav", ".flac", ".mp3", ".ogg", ".m4a", ".aac", ".wma"}


class LibraryIndexer:
    """Scans music libraries and builds searchable index.
    
    The index maps file paths to metadata:
    {
        "/path/to/song.mp3": {
            "title": "Song Title",
            "artist": "Artist Name",
            "album": "Album Name",
            "play_count": 42,
            "has_eq": True
        }
    }
    
    Attributes:
        index_path: Path to save/load the index JSON
        index: Current index dictionary
    """
    
    def __init__(self):
        """Initialize the indexer."""
        config_dir = Path.home() / ".sidecar_eq"
        config_dir.mkdir(exist_ok=True)
        self.index_path = config_dir / "library_index.json"
        self.index = {}
        
        # Load existing index if available
        self._load_index()
        
    def _load_index(self):
        """Load index from disk."""
        if self.index_path.exists():
            try:
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    self.index = json.load(f)
                print(f"[Indexer] Loaded {len(self.index)} tracks from index")
            except Exception as e:
                print(f"[Indexer] Failed to load index: {e}")
                self.index = {}
                
    def save_index(self):
        """Save index to disk."""
        try:
            with open(self.index_path, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, indent=2, ensure_ascii=False)
            print(f"[Indexer] Saved {len(self.index)} tracks to index")
        except Exception as e:
            print(f"[Indexer] Failed to save index: {e}")
            
    def scan_folder(self, folder_path: str, recursive: bool = True, progress_callback=None) -> int:
        """Scan a folder and add tracks to the index.
        
        Args:
            folder_path: Path to folder to scan
            recursive: If True, scan subfolders recursively
            progress_callback: Optional callback(scanned, added) for progress updates
            
        Returns:
            Number of new tracks added
        """
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            print(f"[Indexer] Folder not found: {folder_path}")
            return 0
            
        added = 0
        scanned = 0
        
        if recursive:
            files = list(folder.rglob("*"))  # Convert to list for counting
        else:
            files = list(folder.glob("*"))
            
        total_files = len(files)
        print(f"[Indexer] Found {total_files} total files to scan...")
            
        for file_path in files:
            if file_path.suffix.lower() not in AUDIO_EXTS:
                continue
                
            # Skip hidden files
            if file_path.name.startswith(".") or file_path.name.startswith("._"):
                continue
                
            scanned += 1
            path_str = str(file_path.absolute())
            
            # Skip if already indexed
            if path_str in self.index:
                continue
                
            # Extract metadata
            metadata = self._extract_metadata(file_path)
            if metadata:
                self.index[path_str] = metadata
                added += 1
                
            # Progress feedback every 50 files
            if scanned % 50 == 0:
                print(f"[Indexer] Scanned {scanned} audio files, added {added} new tracks...")
                if progress_callback:
                    progress_callback(scanned, added)
                
        print(f"[Indexer] Scan complete: {scanned} audio files scanned, {added} new tracks added")
        
        # Save after scan
        if added > 0:
            self.save_index()
            
        return added
        
    def _extract_metadata(self, file_path: Path) -> Optional[Dict]:
        """Extract metadata from an audio file.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Metadata dictionary or None if extraction failed
        """
        try:
            mutagen_file = MutagenFile(str(file_path), easy=True)
            if not mutagen_file:
                return None
                
            # Extract basic metadata
            title = self._get_tag(mutagen_file, ['title', 'TIT2'])
            artist = self._get_tag(mutagen_file, ['artist', 'TPE1', 'albumartist'])
            album = self._get_tag(mutagen_file, ['album', 'TALB'])
            
            # Use filename as fallback for title
            if not title:
                title = file_path.stem
                
            # Check if track has saved settings
            path_str = str(file_path.absolute())
            settings = store.get_record(path_str)
            
            play_count = 0
            has_eq = False
            
            if settings:
                play_count = settings.get('play_count', 0)
                has_eq = 'eq' in settings and settings['eq'] is not None
                
            return {
                'title': title or 'Unknown',
                'artist': artist or 'Unknown Artist',
                'album': album or '',
                'play_count': play_count,
                'has_eq': has_eq
            }
            
        except Exception as e:
            print(f"[Indexer] Failed to extract metadata from {file_path}: {e}")
            return None
            
    def _get_tag(self, mutagen_file, tag_names: List[str]) -> str:
        """Get first available tag from list of possible names.
        
        Args:
            mutagen_file: Mutagen file object
            tag_names: List of tag names to try
            
        Returns:
            Tag value or empty string
        """
        for tag_name in tag_names:
            try:
                value = mutagen_file.get(tag_name)
                if value:
                    # Handle list values
                    if isinstance(value, list) and len(value) > 0:
                        return str(value[0])
                    return str(value)
            except:
                continue
        return ''
        
    def update_track(self, path: str):
        """Update a single track's metadata in the index.
        
        Args:
            path: Path to track
        """
        file_path = Path(path)
        if not file_path.exists():
            # Remove from index if file no longer exists
            if path in self.index:
                del self.index[path]
                self.save_index()
            return
            
        metadata = self._extract_metadata(file_path)
        if metadata:
            self.index[path] = metadata
            self.save_index()
            
    def get_index(self) -> Dict[str, Dict]:
        """Get the current index.
        
        Returns:
            Index dictionary mapping paths to metadata
        """
        return self.index
        
    def clear_index(self):
        """Clear the entire index."""
        self.index = {}
        self.save_index()
