"""Music library indexer for Sidecar EQ.

Scans local and network folders to build a hierarchical music library.
Extracts metadata (title, artist, album) and integrates with per-track
settings (play count, EQ status).

The library is saved to ~/.sidecar_eq/library.json for fast startup.
"""

from pathlib import Path
from typing import List, Optional

from mutagen import File as MutagenFile

from .library import Library, Song


# Supported audio file extensions
AUDIO_EXTS = {".wav", ".flac", ".mp3", ".ogg", ".m4a", ".aac", ".wma"}


class LibraryIndexer:
    """Scans music folders and builds hierarchical library.
    
    The library organizes songs into Artist -> Album -> Song structure.
    See library.py for the data model.
    
    Attributes:
        library: Hierarchical Library instance
    """
    
    def __init__(self):
        """Initialize the indexer."""
        self.library = Library()
        
    def save_library(self):
        """Save library to disk."""
        self.library.save()
            
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
            
            # Skip if already in library
            if self.library.get_song_by_path(path_str):
                continue
                
            # Extract metadata and create Song
            song = self._create_song(file_path)
            if song:
                self.library.add_song(song)
                added += 1
                
            # Progress feedback every 50 files
            if scanned % 50 == 0:
                print(f"[Indexer] Scanned {scanned} audio files, added {added} new tracks...")
                if progress_callback:
                    progress_callback(scanned, added)
                
        print(f"[Indexer] Scan complete: {scanned} audio files scanned, {added} new tracks added")
        
        # Save after scan
        if added > 0:
            self.save_library()
            
        return added
        
    def _create_song(self, file_path: Path) -> Optional[Song]:
        """Create a Song object from an audio file.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Song instance or None if extraction failed
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
                
            # Create Song (it will load settings from store automatically)
            path_str = str(file_path.absolute())
            song = Song(
                path=path_str,
                title=title or 'Unknown',
                artist=artist or 'Unknown Artist',
                album=album or 'Unknown Album'
            )
            
            return song
            
        except Exception as e:
            print(f"[Indexer] Failed to create song from {file_path}: {e}")
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
        """Update a single track's metadata in the library.
        
        Args:
            path: Path to track
        """
        file_path = Path(path)
        if not file_path.exists():
            # TODO: Remove from library if file no longer exists
            # (Need to implement removal logic in Library class)
            return
            
        song = self._create_song(file_path)
        if song:
            # Remove old entry if exists, add new one
            # (Library will handle duplicates)
            self.library.add_song(song)
            self.save_library()
            
    def get_library(self) -> Library:
        """Get the current library.
        
        Returns:
            Library instance
        """
        return self.library
        
    def clear_library(self):
        """Clear the entire library."""
        self.library.clear()
