# J. Geils Band MP3 Playback Issue - Root Cause & Fix

## Problem Summary
The J. Geils Band track "J-Geils-Band-Monkey-Island" was being detected as a "streaming source" instead of a local file, causing it to skip audio analysis and then fail to play with an FFmpeg error: `Invalid data found when processing input`.

## Root Cause Analysis

### Investigation Results
Using diagnostic tools, we discovered:

1. **File Type Mismatch**: The "J. Geils Band" files are actually **MP4 video files**, not MP3 audio files
2. **File Locations**:
   - `/Volumes/Music/****Need to process/J Geils Band Monkey Island.mp4` (102MB)
   - `/Volumes/Music/****Need to process/J Geils Band Self Titled.mp4` (90MB)
3. **FFmpeg Error**: The media player was trying to play video files as audio, causing the "Invalid data found" error

### Why MP4 Files Were in the Queue
The app has proper file filtering in place:
- **File Dialog**: Filters to `"Audio Files (*.wav *.flac *.mp3 *.ogg *.m4a)"`
- **Folder Addition**: Checks `AUDIO_EXTS = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}`

The MP4 files likely entered the queue through:
1. **Drag-and-drop** (if implemented without filtering)
2. **Previous session persistence** (before filtering was added)
3. **Manual playlist loading** that referenced these files

### Source Detection Confusion
The source detection logic was correctly identifying the files as local, but the error message suggested they were "streaming sources" because:
1. The files failed FFmpeg validation (video format)
2. Error handling wasn't distinguishing between "streaming source with no saved EQ" vs "invalid local file"

## Solution Implemented

### 1. Enhanced File Type Validation
**File**: `sidecar_eq/queue_model.py`
**Change**: Added validation to `add_paths()` method to reject non-audio files:

```python
# Valid audio file extensions
AUDIO_EXTS = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}

# Validate file extension for local files (skip validation for URLs)
if Path(ap).suffix.lower() not in AUDIO_EXTS:
    print(f"[Warning] Skipping non-audio file: {ap}")
    continue
```

### 2. Improved Queue Path Handling
**File**: `sidecar_eq/queue_model.py`  
**Change**: Enhanced `paths()` method to handle edge cases:

```python
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
```

### 3. Robust Source Detection
**File**: `sidecar_eq/app.py`
**Change**: Enhanced source detection with validation:

```python
# Robust source detection with validation
stream_url = track_info.get('stream_url')

if stream_url and stream_url.strip() and stream_url.startswith(('http://', 'https://')):
    # Plex track - has valid stream URL
    playback_url = stream_url
    identifier = stream_url
    source_type = 'plex'
elif path and path.startswith(('http://', 'https://')):
    # Website URL - path is HTTP/HTTPS URL
    playback_url = path
    identifier = path
    source_type = 'url'  
elif path and path.strip():
    # Local file - has valid file path
    playback_url = path
    identifier = path
    source_type = 'local'
else:
    # Invalid/empty path - this shouldn't happen
    print(f"[Error] Invalid path/URL for row {row}: path='{path}', track_info={track_info}")
    raise ValueError(f"Invalid path for playback: '{path}'")
```

## Testing Results

### File Validation Test
```
✅ MP3, FLAC, WAV files allowed
❌ MP4, AVI, PDF files rejected  
✅ HTTP/HTTPS URLs allowed (for streaming)
```

### Diagnostic Findings
```
Found problematic file: J Geils Band Monkey Island.mp4
  Extension: .mp4
  Size: 102194215 bytes
  New validation would: ✅ Reject
```

## User Impact

### Before Fix
- MP4 video files could be added to audio queue
- Playback failed with cryptic FFmpeg errors
- Source type confusion in error messages
- Poor user experience with non-obvious failures

### After Fix
- **Prevention**: Non-audio files automatically rejected during addition
- **Clear Feedback**: Warning messages when skipping invalid files
- **Robust Playback**: Only valid audio files and URLs reach the player
- **Better Diagnostics**: Clear error messages for edge cases

## Recommendations

### For Users
1. **Remove Existing Invalid Files**: Clear the queue of any existing MP4/video files
2. **Use Audio Files**: Ensure you're adding actual audio files (MP3, FLAC, WAV, OGG, M4A)
3. **Check File Extensions**: Verify file types before adding to queue

### For Future Development
1. **Enhanced Error Messages**: More specific error messages distinguishing file format issues from network problems
2. **File Type Detection**: Use mutagen or similar to validate file content, not just extensions
3. **Drag-and-Drop Filtering**: Ensure drag-and-drop operations also validate file types
4. **Queue Cleanup**: Add a "Remove Invalid Entries" function to clean existing queues

## Summary

The J. Geils Band playback issue was caused by **MP4 video files being treated as audio files**. The fix implements comprehensive file type validation to prevent non-audio files from entering the queue, plus improved error handling for edge cases. This ensures a better user experience and prevents similar issues in the future.