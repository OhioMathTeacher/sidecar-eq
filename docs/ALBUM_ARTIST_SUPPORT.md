# Album and Artist Support in Search Results

## Problem Statement

Previously, when clicking on search results:
1. **Albums**: Only the first song from the album was added to queue
2. **Artists**: Only the first song by the artist was added to queue  
3. **Error in Search Only view**: "Could not add file to queue" error when trying to add songs

## Root Causes

### Issue 1: Incomplete Album/Artist Handling
The search results stored only the path to the **first song** in albums/artists:

```python
# OLD CODE - Albums
path = album.songs[0].path if album.songs else None
item.setData(Qt.ItemDataRole.UserRole, path)  # Only first song!

# OLD CODE - Artists  
all_songs = artist.get_all_songs()
path = all_songs[0].path if all_songs else None
item.setData(Qt.ItemDataRole.UserRole, path)  # Only first song!
```

When clicked, only this single path was emitted to `_on_search_result_selected()`, so only one song was added.

### Issue 2: Files on Unmounted Volume
The library was indexed with files on `/Volumes/Music`, which is currently unmounted. When trying to add these files:
- `Path(file_path).exists()` returns `False`
- Queue model rejects non-existent files
- Error: "Could not add file to queue"

## Solution

### Change 1: Store All Paths with Metadata

Updated search results to store a **dictionary with type and all paths**:

```python
# NEW CODE - Songs
song_data = {
    'type': 'song',
    'title': song.title,
    'artist': song.artist,
    'paths': [song.path]
}
item.setData(Qt.ItemDataRole.UserRole, song_data)

# NEW CODE - Albums
album_data = {
    'type': 'album',
    'title': album.title,
    'artist': album.artist,
    'paths': [song.path for song in album.songs]  # ALL songs!
}
item.setData(Qt.ItemDataRole.UserRole, album_data)

# NEW CODE - Artists
artist_data = {
    'type': 'artist',
    'name': artist.name,
    'paths': [song.path for song in all_songs]  # ALL songs!
}
item.setData(Qt.ItemDataRole.UserRole, artist_data)
```

### Change 2: Update Signal Type

Changed the signal to accept either a path string (legacy) or dict:

```python
# OLD
result_selected = Signal(str, bool)  # (file_path, play_immediately)

# NEW  
result_selected = Signal(object, bool)  # (data, play_immediately)
```

This maintains backward compatibility while supporting the new format.

### Change 3: Enhanced Handler in app.py

Updated `_on_search_result_selected()` to:
1. Handle both legacy (string) and new (dict) formats
2. Process **multiple file paths** at once
3. Filter out missing files and show helpful errors
4. Display appropriate messages based on type (song/album/artist)

```python
def _on_search_result_selected(self, data, play_immediately: bool):
    # Handle both legacy (string path) and new (dict) formats
    if isinstance(data, str):
        file_paths = [data]
        result_type = 'song'
    elif isinstance(data, dict):
        file_paths = data.get('paths', [])
        result_type = data.get('type', 'song')
    
    # Filter out files that don't exist
    existing_paths = []
    missing_paths = []
    
    for file_path in file_paths:
        if Path(file_path).exists():
            existing_paths.append(file_path)
        else:
            missing_paths.append(file_path)
    
    # Show error for missing files
    if missing_paths:
        self._show_missing_file_dialog(missing_paths[0])
        
        # If ALL files are missing, don't add anything
        if not existing_paths:
            return
    
    # Add existing files to queue
    count = self.model.add_paths(existing_paths)
    
    # Show appropriate message based on type
    if result_type == 'album':
        album_title = data.get('title', 'Unknown Album')
        self.statusBar().showMessage(
            f"✅ Added Album to Queue: {album_title} ({count} tracks)", 
            3000
        )
    # ... similar for artist and song
```

## Expected Behavior Now

### Single Song
- **Single-click**: Adds 1 song to queue (blue notification)
- **Double-click**: Adds 1 song and plays immediately (green notification)

### Album (e.g., "Black Sabbath Vol. 4")
- **Single-click**: Adds ALL album tracks to queue (e.g., "✅ Added Album to Queue: Volume 4 (10 tracks)")
- **Double-click**: Adds ALL album tracks and plays first track (e.g., "▶️ Playing Album: Volume 4 (10 tracks)")

### Artist (e.g., "Black Sabbath")
- **Single-click**: Adds ALL songs by artist to queue (e.g., "✅ Added Artist to Queue: Black Sabbath (42 tracks)")
- **Double-click**: Adds ALL songs and plays first track (e.g., "▶️ Playing Artist: Black Sabbath (42 tracks)")

## Error Handling

### Missing Files
If files are on an unmounted volume or have been moved:

1. **Some files missing**: Shows warning, adds available files only
   - Status: "⚠️ 5 file(s) not found, adding 5 available"

2. **All files missing**: Shows error dialog with volume detection
   - Dialog explains the volume is unmounted
   - Offers to re-index library
   - Status: "❌ All files not found!"

3. **Error Dialog Content**:
   ```
   Cannot access file on unmounted volume
   
   Volume: Music
   File: 01. Black Sabbath - Wheels of Confusion.flac
   
   This file is on an external drive or network share 
   that is not currently connected.
   
   Solutions:
   • Mount the volume and try again
   • Re-index your library to update file locations
   • Remove this track from your library
   
   [Re-index Library...] [OK]
   ```

## Testing

To test album/artist support:

1. **Mount `/Volumes/Music`** (if available):
   ```bash
   # Connect external drive or network share
   ```

2. **Or use local test files**:
   ```bash
   # Add some local WAV/MP3 files to test with
   ```

3. **Search for an album**:
   - Type "Black Sabbath Vol. 4"
   - Single-click on the album result
   - Verify ALL 10 tracks are added to queue

4. **Search for an artist**:
   - Type "Black Sabbath"
   - Double-click on the artist result
   - Verify ALL artist tracks are added and first one plays

5. **Test missing files**:
   - Try adding songs from `/Volumes/Music` (unmounted)
   - Verify helpful error dialog appears
   - Verify status bar shows appropriate message

## Files Modified

- `sidecar_eq/search.py`:
  - Changed `result_selected` signal type
  - Updated `_populate_top_plays_from_songs()` to store dict
  - Updated `_populate_matching_songs()` to store dict
  - Updated `_populate_albums_from_results()` to store dict with all paths
  - Updated `_populate_related_artists()` to store dict with all paths
  - Updated `_on_category_item_clicked()` to emit data
  - Updated `_on_category_item_double_clicked()` to emit data
  - Updated `_on_return_pressed()` to use new data format

- `sidecar_eq/app.py`:
  - Rewrote `_on_search_result_selected()` to handle both formats
  - Added multi-file support with existence checking
  - Added type-specific status messages (song/album/artist)
  - Enhanced error handling for missing files

## Future Improvements

1. **Smart album ordering**: Add tracks in album order (track number)
2. **Artist sorting**: Sort artist's songs by album, then track number
3. **Partial album selection**: Shift+click to select range of songs
4. **Queue deduplication**: Detect and skip songs already in queue
5. **Batch error handling**: Show summary dialog for multiple missing files

## Related Documentation

- [VIEW_LAYOUT_PHILOSOPHY.md](VIEW_LAYOUT_PHILOSOPHY.md) - Why queue should always be visible
- [EQ_IMPLEMENTATION.md](../EQ_IMPLEMENTATION.md) - AudioEngine and EQ system
- [ROADMAP.md](../ROADMAP.md) - Overall project direction
