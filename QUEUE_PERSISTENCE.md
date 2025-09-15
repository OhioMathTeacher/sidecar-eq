# Queue Persistence Feature

## Overview
Added persistent queue functionality to maintain the music queue across application sessions. Songs remain in the queue when you close and reopen Sidecar EQ, and can only be removed through explicit user actions.

## Key Features

### 1. **Automatic Queue Save/Load**
- Queue automatically saved when closing the application
- Queue automatically restored when starting the application
- Supports all file types: local audio, local video, Plex tracks, and URLs

### 2. **Smart File Validation**
- Missing files are automatically skipped during queue restoration
- Only existing files are loaded back into the queue
- Clear logging shows which files were skipped and why

### 3. **Exclusive Removal Control**
- **Trash Button**: Click the trash icon to remove selected items
- **Delete Key**: Press Delete or Backspace to remove selected items  
- **No Auto-Clearing**: Adding folders/files never clears existing queue items

### 4. **Cross-Session Continuity**
- Maintains play counts, metadata, and source information
- Video files preserve their "(video)" designation
- Plex tracks retain their stream URLs and source info

## Technical Implementation

### Queue Storage Location
```
~/.sidecar_eq/queue_state.json
```

### Storage Format
```json
{
  "version": "1.0",
  "rows": [
    {
      "path": "/Users/user/Music/song.mp3",
      "title": "Song Title",
      "artist": "Artist Name", 
      "album": "Album Name",
      "play_count": 5,
      "source": "local"
    },
    {
      "path": "/Users/user/Videos/music_video.mp4",
      "title": "Music Video (video)",
      "artist": "Video Artist",
      "album": "",
      "play_count": 2,
      "source": "local",
      "is_video": true
    },
    {
      "path": "",
      "title": "Plex Track",
      "artist": "Plex Artist",
      "album": "Plex Album", 
      "play_count": 0,
      "source": "plex",
      "stream_url": "http://plex-server/audio/12345"
    }
  ]
}
```

### Core Components

#### 1. QueueModel Persistence Methods (`sidecar_eq/queue_model.py`)

**`save_queue_state(file_path)`**
- Serializes entire queue to JSON format
- Preserves all metadata including video flags and stream URLs
- Creates backup-friendly human-readable format

**`load_queue_state(file_path)`**  
- Loads and validates saved queue data
- Skips files that no longer exist (with logging)
- Restores exact queue state including metadata

**`clear_queue()`**
- Completely empties the queue
- Used for explicit clearing (not called automatically)

#### 2. MainWindow Integration (`sidecar_eq/app.py`)

**Initialization (`__init__`)**
```python
# Load saved queue state after model creation
self._load_queue_state()
```

**Cleanup (`closeEvent`)**
```python
# Save queue state before application exit  
self._save_queue_state()
```

**Queue File Management**
```python
def _get_queue_state_file(self):
    home = Path.home()
    sidecar_dir = home / ".sidecar_eq" 
    sidecar_dir.mkdir(exist_ok=True)
    return sidecar_dir / "queue_state.json"
```

#### 3. Enhanced Queue Removal (`QueueTableView`)

**Custom Key Handling**
```python
class QueueTableView(QTableView):
    delete_key_pressed = Signal()
    
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_key_pressed.emit()
```

**Unified Removal Logic**
- Trash button and Delete key both call `on_remove_selected()`
- Only way to remove items from queue
- Multi-selection support for batch removal

### File Type Support

#### Local Audio Files
```python
{
  "path": "/path/to/song.flac",
  "title": "Song Title",
  "source": "local"
}
```

#### Video Files  
```python
{
  "path": "/path/to/video.mp4", 
  "title": "Video Title (video)",
  "source": "local",
  "is_video": true
}
```

#### Plex Tracks
```python
{
  "path": "",
  "stream_url": "http://plex-server/audio/track-id",
  "title": "Plex Song",
  "source": "plex"
}  
```

#### Web URLs
```python
{
  "path": "https://example.com/stream.mp3",
  "title": "Web Stream", 
  "source": "url"
}
```

## User Workflow

### Session Persistence
1. **Add Files**: Use "Add Audio/Video Files" or "Add Folder" to build your queue
2. **Listen & Organize**: Play music, build your perfect playlist
3. **Close App**: Queue automatically saved on exit
4. **Restart App**: Queue automatically restored with all your music intact

### Queue Management  
1. **Remove Items**: Select unwanted tracks and press Delete or click trash button
2. **Multi-Remove**: Select multiple tracks (Ctrl+click) and delete all at once
3. **Add More**: New files added to existing queue (never replaces)
4. **Preserve Queue**: Adding folders never clears your existing selections

### Missing File Handling
- **Automatic Cleanup**: Files that no longer exist are silently skipped
- **Informed User**: Console shows which files were skipped during load
- **Graceful Degradation**: Queue loads successfully even with some missing files

## Error Handling & Edge Cases

### Missing Files
```
[QueueModel] Skipping missing file: /old/path/song.mp3
[QueueModel] Loaded 4 items from saved queue (skipped 1 missing files)
```

### Corrupted Queue File
```
[QueueModel] Invalid queue format in ~/.sidecar_eq/queue_state.json
[QueueModel] Failed to load queue: [error details]
```

### Permission Issues
```  
[QueueModel] Failed to save queue: [PermissionError details]
[App] Failed to save queue state: [error details]
```

### Recovery Behavior
- **Save Fails**: App continues running normally, no queue persistence for that session
- **Load Fails**: App starts with empty queue, user can rebuild normally
- **Partial Load**: Successfully loads valid items, skips problematic entries

## Benefits for Users

### Immediate Value
- **No Lost Work**: Your carefully curated queue survives app restarts
- **Resume Sessions**: Pick up exactly where you left off
- **Flexible Workflow**: Build playlists over multiple sessions

### Long-Term Benefits
- **Queue as Workspace**: Treat queue as persistent project workspace
- **Reduced Friction**: Less time re-adding the same files repeatedly  
- **Better Organization**: Build and refine queues without losing progress

### Power User Features
- **Cross-Device Sync**: Copy `queue_state.json` between devices
- **Backup Integration**: Queue file included in home directory backups
- **Manual Editing**: JSON format allows power users to edit queues externally

## Testing Results

### Functionality Tests
```
✅ Queue saves automatically on app exit
✅ Queue restores automatically on app startup  
✅ Missing files handled gracefully (skipped with logging)
✅ Delete key removes selected items
✅ Trash button removes selected items
✅ Multi-selection removal works
✅ Adding files/folders preserves existing queue
✅ All file types supported (audio, video, Plex, URLs)
```

### Cross-Session Test
```
Session 1: Add 5 audio files + 2 video files → Close app
Session 2: App starts with all 7 files in queue
Session 3: Delete 2 files → Add 3 more → Close app  
Session 4: App starts with 8 files (5 original + 3 new)
```

### Resilience Test
```
✅ Delete queue file manually → App starts with empty queue
✅ Corrupt queue file → App starts with empty queue + error message
✅ Move music files → App skips missing files, loads remaining ones
✅ Mixed file types → All types (local/Plex/URL) persist correctly
```

## Configuration

### Default Settings
- **Queue File**: `~/.sidecar_eq/queue_state.json`
- **Auto-Save**: Enabled (on app exit)
- **Auto-Load**: Enabled (on app start)
- **Missing File Handling**: Skip with logging

### Manual Control
- **Clear Queue**: Use trash button to select all items and delete
- **Backup Queue**: Copy `~/.sidecar_eq/queue_state.json` to safe location  
- **Restore Queue**: Replace queue file and restart app
- **Reset Queue**: Delete queue file and restart app

## Future Enhancements

### Potential Improvements
1. **Multiple Queue Slots**: Save/load different named queue configurations
2. **Auto-Backup**: Keep multiple queue file versions for recovery
3. **Sync Integration**: Cloud storage sync for cross-device queues
4. **Import/Export**: Convert queues to/from M3U/PLS playlist formats

### Advanced Features  
1. **Queue History**: Track and restore previous queue states
2. **Smart Validation**: Auto-relocate moved files using metadata matching
3. **Partial Recovery**: Attempt to find moved files in common locations
4. **Queue Statistics**: Show queue size, total duration, file type breakdown

## Summary

The queue persistence feature fundamentally changes how users interact with Sidecar EQ by treating the queue as a persistent workspace rather than a temporary list. Users can now:

- **Build complex queues over multiple sessions** without losing work
- **Resume listening exactly where they left off** after restarting
- **Maintain careful organization** without fear of accidental clearing  
- **Work with mixed media types** (audio, video, Plex, URLs) seamlessly

The implementation is robust, handling edge cases gracefully while maintaining excellent performance and user experience. The feature works transparently - users benefit automatically without changing their workflow, while power users can leverage the JSON storage format for advanced queue management.