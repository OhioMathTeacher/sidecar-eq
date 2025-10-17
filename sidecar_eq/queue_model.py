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
from .metadata_extractor import extract_comprehensive_metadata

# Expanded columns for professional music management
COLUMNS = [
    "Lookup",      # Metadata lookup (globe icon)
    "Status",      # Play status indicator (radio button)
    "Title", 
    "Artist", 
    "Album",
    "Year",
    "Label",
    "Producer",
    "Rating",      # 1-5 stars
    "Bitrate",
    "Format",
    "Sample Rate",
    "Bit Depth",
    "Duration",
    "Play Count"
]

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
        if not index.isValid():
            return None
            
        row_data = self._rows[index.row()]
        col = index.column()
        
        # Handle different roles
        if role == Qt.DisplayRole:
            # Column 0: Lookup (globe icon - handled by delegate)
            if col == 0:
                return "🌐"  # Globe emoji as fallback
            # Column 1: Status (play indicator - handled by delegate)
            elif col == 1:
                return ""  # Delegate will draw the radio button
            # Column 2: Title
            elif col == 2:
                return row_data.get("title") or Path(row_data["path"]).stem
            # Column 3: Artist
            elif col == 3:
                return row_data.get("artist") or ""
            # Column 4: Album
            elif col == 4:
                return row_data.get("album") or ""
            # Column 5: Year
            elif col == 5:
                return row_data.get("year") or ""
            # Column 6: Label
            elif col == 6:
                return row_data.get("label") or ""
            # Column 7: Producer
            elif col == 7:
                return row_data.get("producer") or ""
            # Column 8: Rating (1-5 stars) - Return number for delegate
            elif col == 8:
                return row_data.get("rating", 0)
            # Column 9: Bitrate
            elif col == 9:
                return row_data.get("bitrate") or ""
            # Column 10: Format
            elif col == 10:
                return row_data.get("format") or Path(row_data["path"]).suffix.upper()[1:]
            # Column 11: Sample Rate
            elif col == 11:
                return row_data.get("sample_rate") or ""
            # Column 12: Bit Depth
            elif col == 12:
                return row_data.get("bit_depth") or ""
            # Column 13: Duration
            elif col == 13:
                duration = row_data.get("duration")
                if duration:
                    mins = int(duration // 60)
                    secs = int(duration % 60)
                    return f"{mins}:{secs:02d}"
                return ""
            # Column 14: Play Count
            elif col == 14:
                return str(row_data.get("play_count", 0))
        
        # UserRole returns the full path (for internal use)
        elif role == Qt.UserRole:
            return row_data.get("path")
        
        # EditRole for editable fields
        elif role == Qt.EditRole:
            if col == 2:  # Title
                return row_data.get("title") or Path(row_data["path"]).stem
            elif col == 3:  # Artist
                return row_data.get("artist") or ""
            elif col == 4:  # Album
                return row_data.get("album") or ""
            elif col == 5:  # Year
                return row_data.get("year") or ""
            elif col == 6:  # Label
                return row_data.get("label") or ""
            elif col == 7:  # Producer
                return row_data.get("producer") or ""
            elif col == 8:  # Rating (return number 0-5)
                return row_data.get("rating", 0)
        
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return COLUMNS[section]
        return str(section + 1)

    def flags(self, index):
        default = super().flags(index)
        flags = default | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled
        
        # Make columns 2-8 editable (Title, Artist, Album, Year, Label, Producer, Rating)
        # Columns 0-1 (Lookup, Status) are not editable
        col = index.column()
        if 2 <= col <= 8:
            flags |= Qt.ItemIsEditable
        
        return flags
    
    def setData(self, index, value, role=Qt.EditRole):
        """Allow editing of metadata fields."""
        if not index.isValid() or role != Qt.EditRole:
            return False
        
        row_data = self._rows[index.row()]
        col = index.column()
        changed = False
        
        # Column mapping based on COLUMNS list:
        # 0: Lookup, 1: Status, 2: Title, 3: Artist, 4: Album, 5: Year, 6: Label, 7: Producer, 8: Rating, ...
        if col == 2:  # Title (was 1, now 2 due to Status column)
            row_data["title"] = str(value) if value else ""
            changed = True
        elif col == 3:  # Artist (was 2, now 3)
            row_data["artist"] = str(value) if value else ""
            changed = True
        elif col == 4:  # Album (was 3, now 4)
            row_data["album"] = str(value) if value else ""
            changed = True
        elif col == 5:  # Year (was 4, now 5)
            row_data["year"] = str(value) if value else ""
            changed = True
        elif col == 6:  # Label (was 5, now 6)
            row_data["label"] = str(value) if value else ""
            changed = True
        elif col == 7:  # Producer (was 6, now 7)
            row_data["producer"] = str(value) if value else ""
            changed = True
        elif col == 8:  # Rating (was 7, now 8 - 0-5 stars)
            try:
                rating = max(0, min(5, int(value)))
                row_data["rating"] = rating
                changed = True
            except (ValueError, TypeError):
                return False
        
        if changed:
            # Emit dataChanged signal
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
            
            # Save updated metadata to file tags (if it's a local file)
            path = row_data.get("path", "")
            if path and not path.startswith(('http://', 'https://')):
                self._save_metadata_to_file(path, row_data)
            
            return True
        
        return False
    
    def _save_metadata_to_file(self, file_path, row_data):
        """Write updated metadata back to the audio file tags."""
        if not MutagenFile or not os.path.exists(file_path):
            return
        
        try:
            audio = MutagenFile(file_path)
            if not audio or not hasattr(audio, 'tags'):
                return
            
            # Get or create tags
            if audio.tags is None:
                audio.add_tags()
            
            tags = audio.tags
            
            # Map our fields to appropriate tag names (handles MP3, FLAC, etc.)
            # Title
            title = row_data.get("title")
            if title:
                for key in ['TIT2', 'title', '©nam']:
                    try:
                        tags[key] = title
                        break
                    except:
                        continue
            
            # Artist
            artist = row_data.get("artist")
            if artist:
                for key in ['TPE1', 'artist', '©ART']:
                    try:
                        tags[key] = artist
                        break
                    except:
                        continue
            
            # Album
            album = row_data.get("album")
            if album:
                for key in ['TALB', 'album', '©alb']:
                    try:
                        tags[key] = album
                        break
                    except:
                        continue
            
            # Year/Date
            year = row_data.get("year")
            if year:
                for key in ['TDRC', 'date', '©day']:
                    try:
                        tags[key] = str(year)
                        break
                    except:
                        continue
            
            # Save changes
            audio.save()
            print(f"[QueueModel] Saved metadata to {Path(file_path).name}")
            
        except Exception as e:
            print(f"[QueueModel] Failed to save metadata to {Path(file_path).name}: {e}")

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
        try:
            # Validate inputs
            if sourceRow < 0 or sourceRow >= len(self._rows):
                print(f"[QueueModel] Invalid sourceRow: {sourceRow} (total: {len(self._rows)})")
                return False
            if count <= 0 or sourceRow + count > len(self._rows):
                print(f"[QueueModel] Invalid count: {count} (sourceRow: {sourceRow}, total: {len(self._rows)})")
                return False
            if destinationChild < 0 or destinationChild > len(self._rows):
                print(f"[QueueModel] Invalid destinationChild: {destinationChild} (total: {len(self._rows)})")
                return False
            
            # If source and destination are the same, no move needed
            if sourceRow == destinationChild:
                return False
            # If dropping right after the source, also no move needed
            if destinationChild == sourceRow + count:
                return False
            
            # Calculate the actual destination after accounting for removal
            # When we remove items, indices shift
            if destinationChild > sourceRow:
                # Moving down - destination shifts up because we remove items first
                actual_dest = destinationChild - count
            else:
                # Moving up - destination stays the same
                actual_dest = destinationChild
            
            # Ensure actual_dest is valid
            if actual_dest < 0 or actual_dest > len(self._rows) - count:
                print(f"[QueueModel] Invalid actual_dest: {actual_dest}")
                return False
            
            print(f"[QueueModel] Moving rows: source={sourceRow}, count={count}, dest={destinationChild} -> actual={actual_dest}")
            
            # Signal that we're about to move rows
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
            print(f"[QueueModel] Successfully moved {count} row(s)")
            return True
            
        except Exception as e:
            print(f"[QueueModel] ERROR in moveRows: {e}")
            import traceback
            traceback.print_exc()
            return False
    
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
            
            # Initialize row with comprehensive metadata
            row = {
                "path": ap,
                "play_count": rec.get("play_count", 0),
                "is_video": is_video,
                # Initialize all metadata fields
                "title": None,
                "artist": None,
                "album": None,
                "year": None,
                "label": None,
                "producer": None,
                "rating": 0,
                "bitrate": None,
                "format": None,
                "sample_rate": None,
                "bit_depth": None,
                "duration": None,
            }
            
            # Extract metadata
            if is_video:
                # For video files, use filename as title and add video indicator
                video_stem = Path(ap).stem
                row["title"] = f"{video_stem} (video)"
                row["artist"] = "Video File"
                row["album"] = ""
                row["format"] = Path(ap).suffix.upper()[1:]
            elif not ap.startswith(('http://', 'https://')):
                # For local audio files, extract comprehensive metadata
                metadata = extract_comprehensive_metadata(ap)
                row.update(metadata)  # Merge all extracted metadata into row
            else:
                # For URLs, use basic info
                row["title"] = Path(ap).stem
                row["format"] = "Stream"
            
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
        """Remove specified rows from the queue.
        
        If this would empty the queue, automatically loads the welcome track instead.
        
        Args:
            rows: List of row indices to remove
        """
        # Remove rows in reverse order to maintain indices
        for r in sorted(set(rows), reverse=True):
            self.beginRemoveRows(QModelIndex(), r, r)
            ap = self._rows[r]["path"]
            self._rows.pop(r)
            self._paths_set.discard(ap)
            self.endRemoveRows()
        
        # If queue is now empty, load the welcome track
        if len(self._rows) == 0:
            self._load_welcome_track()
    
    def _load_welcome_track(self):
        """Load the welcome/introduction track when queue is empty.
        
        Looks for introduction.mp3 in the sidecar_eq package directory.
        If not found, creates a placeholder entry.
        """
        # Get the path to the sidecar_eq package directory
        package_dir = Path(__file__).parent
        intro_path = package_dir / "introduction.mp3"
        
        # If introduction.mp3 doesn't exist yet, try to find any sample audio
        if not intro_path.exists():
            # Look for MLKDream as a fallback (temporary until we create the real intro)
            fallback_path = package_dir / "MLKDream_64kb.mp3"
            if fallback_path.exists():
                intro_path = fallback_path
            else:
                # Create a placeholder entry if no audio file found
                row = {
                    "path": "",
                    "title": "Welcome to SideCarAI",
                    "artist": "SideCarAI Team",
                    "album": "System Audio",
                    "play_count": 0,
                    "stream_url": None,
                    "source": "local",
                }
                self.beginInsertRows(QModelIndex(), 0, 0)
                self._rows.append(row)
                self.endInsertRows()
                return
        
        # Load the intro track using add_paths
        self.add_paths([str(intro_path)])

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
                # Load welcome track if no saved queue exists
                self._load_welcome_track()
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
            
            # If queue is empty after loading, add the welcome track
            if len(self._rows) == 0:
                self._load_welcome_track()
            
            return True
            
        except Exception as e:
            print(f"[QueueModel] Failed to load queue: {e}")
            # Reset to empty state on error
            self.beginResetModel()
            self._rows.clear()
            self._paths_set.clear()
            self.endResetModel()
            # Load welcome track after error
            self._load_welcome_track()
            return False

    def clear_queue(self):
        """Clear all items from the queue."""
        if self._rows:
            self.beginResetModel()
            self._rows.clear()
            self._paths_set.clear()
            self.endResetModel()
