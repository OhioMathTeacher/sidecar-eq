from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from pathlib import Path
try:
    from mutagen import File as MutagenFile
except Exception:
    MutagenFile = None
import os
import json
from . import store
from .metadata import read_tags

COLUMNS = ["Title", "Artist", "Album", "Play Count"]

class QueueModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        # each row: {path, title, artist, album, play_count}
        self._rows = []
        self._paths_set = set()

    # --- Qt model API ---
    def rowCount(self, parent=QModelIndex()):
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return len(COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole,):
            return None
        row = self._rows[index.row()]
        col = index.column()
        if col == 0:
            return row.get("title") or Path(row["path"]).name
        elif col == 1:
            return row.get("artist") or ""
        elif col == 2:
            return row.get("album") or ""
        elif col == 3:
            return str(row.get("play_count", 0))
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return COLUMNS[section]
        return str(section + 1)

    def flags(self, index):
        default = super().flags(index)
        return default | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled

    def supportedDropActions(self):
        return Qt.MoveAction
    
    def mimeTypes(self):
        """Return list of supported MIME types for drag-drop."""
        return ['application/x-qabstractitemmodeldatalist']
    
    def mimeData(self, indexes):
        """Create MIME data for dragged items."""
        mimeData = super().mimeData(indexes)
        return mimeData
    
    def dropMimeData(self, data, action, row, column, parent):
        """Handle drop of MIME data (enables drag-drop reordering)."""
        if action == Qt.IgnoreAction:
            return True
        
        if not data.hasFormat('application/x-qabstractitemmodeldatalist'):
            return False
        
        # Get the source row from the selection (we'll handle this via moveRows)
        # Qt will call moveRows() automatically when this returns True
        return super().dropMimeData(data, action, row, column, parent)

    def moveRows(self, sourceParent, sourceRow, count, destinationParent, destinationChild):
        """Move rows to reorder the queue via drag & drop.
        
        destinationChild is the row index where items should be inserted.
        When dropping between rows, Qt gives us the index where the drop indicator appears.
        """
        if sourceRow < 0 or sourceRow >= len(self._rows):
            return False
        if destinationChild < 0 or destinationChild > len(self._rows):
            return False
        
        # If source and destination are the same, no move needed
        if sourceRow == destinationChild or sourceRow == destinationChild - 1:
            return False
        
        # Calculate actual destination index after removal
        actual_dest = destinationChild
        if destinationChild > sourceRow:
            # Moving down - the destination index shifts up by the number of removed items
            actual_dest = destinationChild - count
        
        # Perform the move
        self.beginMoveRows(sourceParent, sourceRow, sourceRow + count - 1, 
                          destinationParent, actual_dest)
        
        # Extract rows to move
        rows_to_move = self._rows[sourceRow:sourceRow + count]
        
        # Remove from original position
        del self._rows[sourceRow:sourceRow + count]
        
        # Insert at destination
        for i, row in enumerate(rows_to_move):
            self._rows.insert(actual_dest + i, row)
        
        self.endMoveRows()
        return True
    
    def sort(self, column, order=Qt.AscendingOrder):
        """Sort the queue by the specified column."""
        self.layoutAboutToBeChanged.emit()
        
        reverse = (order == Qt.DescendingOrder)
        
        if column == 0:  # Title
            self._rows.sort(key=lambda r: (r.get("title") or Path(r["path"]).name).lower(), reverse=reverse)
        elif column == 1:  # Artist
            self._rows.sort(key=lambda r: (r.get("artist") or "").lower(), reverse=reverse)
        elif column == 2:  # Album
            self._rows.sort(key=lambda r: (r.get("album") or "").lower(), reverse=reverse)
        elif column == 3:  # Play Count
            self._rows.sort(key=lambda r: r.get("play_count", 0), reverse=reverse)
        
        self.layoutChanged.emit()

    # --- Helpers ---
    def add_paths(self, paths):
        # Valid audio and video file extensions
        AUDIO_EXTS = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}
        
        added = 0
        for p in paths:
            # Don't convert URLs to absolute paths
            if p.startswith(('http://', 'https://')):
                ap = p  # Keep URL as-is
            else:
                ap = os.path.abspath(p)  # Convert local paths to absolute
                
                # Check if file is audio or video (video files will have audio extracted)
                from .video_extractor import is_video_file
                file_ext = Path(ap).suffix.lower()
                
                if file_ext not in AUDIO_EXTS and not is_video_file(ap):
                    print(f"[Warning] Skipping unsupported file: {ap}")
                    continue
                    
            if ap in self._paths_set:
                continue
            rec = store.get_record(ap) or {}
            
            # Check if this is a video file that needs audio extraction
            is_video = is_video_file(ap) if not ap.startswith(('http://', 'https://')) else False
            
            row = {
                "path": ap,
                "title": None,
                "artist": None,
                "album": None,
                "play_count": rec.get("play_count", 0),
                "is_video": is_video  # Flag to indicate video file
            }
            # Try to read metadata
            if is_video:
                # For video files, use filename as title and add video indicator
                video_stem = Path(ap).stem
                row["title"] = f"{video_stem} (video)"
                row["artist"] = "Video File"
                row["album"] = ""
            elif MutagenFile and not ap.startswith(('http://', 'https://')):
                # For audio files, try to read tags via mutagen
                try:
                    # Try reading with mutagen - handles MP3, FLAC, OGG, M4A, etc.
                    mf = MutagenFile(ap)
                    if mf:
                        # Extract metadata - mutagen uses different tag names for different formats
                        # MP3 (ID3): TIT2, TPE1, TALB
                        # FLAC/OGG: title, artist, album
                        # M4A: ©nam, ©ART, ©alb
                        
                        title = None
                        artist = None
                        album = None
                        
                        # Try common tag names across formats
                        if hasattr(mf, 'tags') and mf.tags:
                            tags = mf.tags
                            
                            # Title
                            for key in ['TIT2', 'title', '©nam', 'TITLE']:
                                if key in tags:
                                    val = tags[key]
                                    title = str(val[0]) if isinstance(val, list) else str(val)
                                    break
                            
                            # Artist
                            for key in ['TPE1', 'artist', '©ART', 'ARTIST']:
                                if key in tags:
                                    val = tags[key]
                                    artist = str(val[0]) if isinstance(val, list) else str(val)
                                    break
                            
                            # Album
                            for key in ['TALB', 'album', '©alb', 'ALBUM']:
                                if key in tags:
                                    val = tags[key]
                                    album = str(val[0]) if isinstance(val, list) else str(val)
                                    break
                        
                        # Fallback to easy tags if regular tags didn't work
                        if not any([title, artist, album]):
                            try:
                                easy = MutagenFile(ap, easy=True)
                                if easy:
                                    title = easy.get("title", [None])[0]
                                    artist = easy.get("artist", [None])[0]
                                    album = easy.get("album", [None])[0]
                            except:
                                pass
                        
                        row["title"] = title or Path(ap).stem
                        row["artist"] = artist or ""
                        row["album"] = album or ""
                    else:
                        # Fallback to filename if mutagen can't read the file
                        row["title"] = Path(ap).stem
                except Exception as e:
                    # Fallback to filename on any error
                    row["title"] = Path(ap).stem
                    print(f"[QueueModel] Failed to read metadata for {Path(ap).name}: {e}")
            
            self.beginInsertRows(QModelIndex(), len(self._rows), len(self._rows))
            self._rows.append(row)
            self._paths_set.add(ap)
            self.endInsertRows()
            added += 1
        return added

    def paths(self):
        result = []
        for r in self._rows:
            # Prioritize stream_url for Plex tracks, but ensure we don't return None or empty strings
            stream_url = r.get("stream_url")
            path = r.get("path", "")
            
            if stream_url and stream_url.strip():
                # Use stream_url for Plex tracks (should contain http/https)
                result.append(stream_url)
            elif path and path.strip():
                # Use path for local files
                result.append(path)
            else:
                # Fallback - this shouldn't happen but prevents errors
                result.append("")
                print(f"[Warning] Empty path for row: {r}")
        
        return result

    def remove_rows(self, rows):
        for r in sorted(set(rows), reverse=True):
            self.beginRemoveRows(QModelIndex(), r, r)
            ap = self._rows[r]["path"]
            self._rows.pop(r)
            self._paths_set.discard(ap)
            self.endRemoveRows()

    def add_track(self, track):
        """Add a single track dict (from Plex or local), expects keys: title, artist, album, stream_url or file."""
        # Normalize to your internal row format:
        row = {
            "path": track.get("file", ""),    # Will be blank for Plex (use stream_url instead)
            "title": track.get("title", ""),
            "artist": track.get("artist", ""),
            "album": track.get("album", ""),
            "play_count": 0,
            "stream_url": track.get("stream_url", None),  # This is for Plex tracks
            "source": track.get("source", "local"),
        }
        self.beginInsertRows(QModelIndex(), len(self._rows), len(self._rows))
        self._rows.append(row)
        self._paths_set.add(row["path"] or row["stream_url"])
        self.endInsertRows()
        return 1

    def save_queue_state(self, file_path):
        """Save the current queue state to a JSON file."""
        try:
            queue_data = {
                "version": "1.0",
                "rows": self._rows.copy()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(queue_data, f, indent=2, ensure_ascii=False)
            
            print(f"[QueueModel] Saved queue with {len(self._rows)} items to {file_path}")
            return True
        except Exception as e:
            print(f"[QueueModel] Failed to save queue: {e}")
            return False

    def load_queue_state(self, file_path):
        """Load queue state from a JSON file."""
        try:
            if not os.path.exists(file_path):
                print(f"[QueueModel] No saved queue found at {file_path}")
                return False

            with open(file_path, 'r', encoding='utf-8') as f:
                queue_data = json.load(f)
            
            if not isinstance(queue_data, dict) or 'rows' not in queue_data:
                print(f"[QueueModel] Invalid queue format in {file_path}")
                return False

            # Clear current queue
            self.beginResetModel()
            old_count = len(self._rows)
            self._rows.clear()
            self._paths_set.clear()
            
            # Load saved rows, validating that files still exist
            loaded_rows = []
            for row in queue_data['rows']:
                # Ensure row has required keys
                if not isinstance(row, dict) or 'path' not in row:
                    continue
                
                # Check if file still exists (skip validation for URLs and Plex streams)
                path = row.get('path', '')
                stream_url = row.get('stream_url', '')
                source = row.get('source', 'local')
                
                if source == 'local' and path:
                    # For local files, check if they still exist
                    if not os.path.exists(path):
                        print(f"[QueueModel] Skipping missing file: {path}")
                        continue
                
                # Add valid row
                self._rows.append(row)
                self._paths_set.add(path or stream_url)
                loaded_rows.append(row)
            
            self.endResetModel()
            
            print(f"[QueueModel] Loaded {len(loaded_rows)} items from saved queue (skipped {len(queue_data['rows']) - len(loaded_rows)} missing files)")
            return True
            
        except Exception as e:
            print(f"[QueueModel] Failed to load queue: {e}")
            # Reset to empty state on error
            self.beginResetModel()
            self._rows.clear()
            self._paths_set.clear()
            self.endResetModel()
            return False

    def clear_queue(self):
        """Clear all items from the queue."""
        if self._rows:
            self.beginResetModel()
            self._rows.clear()
            self._paths_set.clear()
            self.endResetModel()
