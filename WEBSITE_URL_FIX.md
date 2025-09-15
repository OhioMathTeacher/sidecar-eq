# Website URL Playback Fix

## Problem
Website URLs were being added to the queue but wouldn't play when selected. The issue occurred because:

1. **URL Path Conversion**: The `QueueModel.add_paths()` method was calling `os.path.abspath()` on URLs, converting them to invalid local file paths like `/Users/todd/sidecar-eq/https:/example.com/audio.mp3`

2. **Source Type Detection**: URLs were being treated as local files in the playback logic, causing them to go through audio analysis instead of being handled as streaming sources.

## Solution

### 1. Fixed URL Path Preservation
**File**: `sidecar_eq/queue_model.py`
**Change**: Modified `add_paths()` to detect URLs and preserve them without converting to absolute paths:

```python
# Don't convert URLs to absolute paths  
if p.startswith(('http://', 'https://')):
    ap = p  # Keep URL as-is
else:
    ap = os.path.abspath(p)  # Convert local paths to absolute
```

### 2. Enhanced Source Type Detection  
**File**: `sidecar_eq/app.py`
**Change**: Updated `_play_row()` method to properly detect and handle three source types:

```python
# Determine source type and playbook URL
if track_info.get('stream_url'):
    # Plex track
    playback_url = track_info['stream_url']
    identifier = track_info['stream_url'] 
    source_type = 'plex'
elif path.startswith(('http://', 'https://')):
    # Website URL
    playback_url = path
    identifier = path
    source_type = 'url'
else:
    # Local file
    playback_url = path
    identifier = path
    source_type = 'local'
```

### 3. Improved Streaming Source Handling
**Change**: URLs now skip audio analysis (like Plex streams) and can load/save EQ settings:

```python
# For streaming sources (Plex and URLs), we can't do audio analysis
if source_type in ('plex', 'url'):
    # Try to load saved EQ for this streaming track
    eq_data = self.load_eq_for_track(identifier)
    if eq_data:
        self._apply_eq_settings(eq_data.get('gains_db', [0]*10))
        if 'suggested_volume' in eq_data:
            self._apply_volume_setting(eq_data['suggested_volume'])
```

### 4. Enhanced Status Messages
**Change**: Clear source type indication in status bar:

```python
source_labels = {'local': '', 'url': 'from URL', 'plex': 'from Plex'}
source_label = source_labels.get(source_type, '')
status_msg = f"Playing: {title}" + (f" ({source_label})" if source_label else "")
```

## Testing Results

### Integration Tests Pass
- ✅ URLs preserved correctly in queue (no path conversion)
- ✅ Source type detection works for local files, URLs, and Plex tracks  
- ✅ Player handles HTTP/HTTPS URLs via `QUrl()` constructor
- ✅ EQ/volume save/load functionality works with URL identifiers
- ✅ Status messages show appropriate source labels

### User Experience
- **Add URLs**: Select "Website URL" source, enter HTTP/HTTPS URL → adds to queue correctly
- **Play URLs**: Click play → streams audio without attempting local file analysis  
- **EQ Settings**: Can save and load EQ/volume settings for specific URLs
- **Status Display**: Shows "Playing: filename (from URL)" to indicate source type

## Key Benefits

1. **Unified Multi-Source Support**: Local files, Website URLs, and Plex streams all work seamlessly
2. **Proper Streaming Handling**: URLs skip inappropriate local file operations  
3. **Settings Persistence**: EQ and volume settings save/load for all source types
4. **Clear User Feedback**: Status messages indicate source type for clarity
5. **Performance**: No wasted analysis attempts on streaming sources

## Usage
1. Set source knob to "Website URL"
2. Click "Add Files" button  
3. Enter any HTTP/HTTPS audio URL
4. Click play → streams immediately with "(from URL)" status
5. Adjust EQ/volume and save → settings persist for that specific URL