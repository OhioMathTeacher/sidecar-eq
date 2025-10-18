# Initial Search & Default Track

## What Was Implemented

### 1. **Automatic Initial Search**
When the app launches, it now automatically populates the search panel:

**If queue has tracks:**
- Searches for the first track's artist (preferred)
- Falls back to album name if no artist
- Falls back to title if neither artist nor album
- Example: If "Rotten Apple" by Alice in Chains is in queue → searches for "Alice in Chains"

**If queue is empty:**
- Loads bundled MLK "I Have a Dream" speech (`sidecar_eq/MLKDream_64kb.mp3`)
- Adds it to the queue automatically
- Searches for "MLK" to show related content
- Provides immediate content to demo the app

### 2. **New SearchBar Method**
Added `set_search_text(text: str)` method to programmatically trigger searches:
```python
def set_search_text(self, text: str):
    """Set the search text programmatically and trigger search."""
    self.search_input.setText(text)
    self._perform_search()  # Bypass debounce timer
```

### 3. **Smart Search Term Selection**
Priority order for automatic search:
1. **Artist** - Most likely to find related tracks
2. **Album** - Good for finding album mates
3. **Title** - Last resort

This ensures the search panel always shows relevant, interesting content.

## User Experience

### Before:
- Search panel was empty on launch
- User had to manually type a search query
- If queue was empty, nothing was visible

### After:
- Search panel is immediately populated with relevant results
- If queue has tracks → shows related artists/albums
- If queue is empty → MLK speech provides demo content
- No manual search needed to see the feature

## Technical Details

### Default Track: MLK "I Have a Dream" Speech
- **Location**: `sidecar_eq/MLKDream_64kb.mp3` (bundled with app)
- **Format**: MP3, 64 kbps (small file size)
- **Purpose**: 
  - Demonstrates audio playback
  - Provides historical/educational content
  - Shows EQ working on speech (different from music)
  - Always available (doesn't depend on user's music library)

### Code Flow:
```python
# app.py - _do_initial_selection()
if self.model.rowCount() > 0:
    # Get first track's metadata
    artist = row_data.get('artist', '')
    if artist:
        self.search_bar.set_search_text(artist)
else:
    # Load MLK speech
    default_path = Path(__file__).parent / "MLKDream_64kb.mp3"
    self.model.add_paths([str(default_path)])
    self.search_bar.set_search_text("MLK")
```

## Benefits

1. **Better First Impression**: App looks active and populated immediately
2. **Educational**: MLK speech is historically significant content
3. **Demo-Ready**: App can be demoed without requiring user's music library
4. **Discoverability**: Users immediately see how search works
5. **Context**: Search results relate to what's playing

## Files Modified

1. **`sidecar_eq/app.py`**
   - Updated `_do_initial_selection()` to check queue state
   - Added logic to load MLK speech if queue is empty
   - Added smart search term selection (artist > album > title)

2. **`sidecar_eq/search.py`**
   - Added `set_search_text(text)` method
   - Allows programmatic search triggering

3. **`sidecar_eq/MLKDream_64kb.mp3`** (Bundled asset)
   - Default audio file for empty queue scenario

## Testing Checklist

- [x] App launches with populated queue → searches for first artist
- [ ] App launches with empty queue → loads MLK speech
- [ ] MLK speech appears in queue table
- [ ] Search panel shows "MLK" search results
- [ ] MLK speech plays correctly when clicked
- [ ] EQ controls work on speech audio

## Example Scenarios

**Scenario 1: User has Alice in Chains in queue**
```
[App] Auto-search for: Alice in Chains
→ Search shows: Alice in Chains albums, related grunge bands, etc.
```

**Scenario 2: Empty queue on first launch**
```
[App] Queue is empty, loading default track: MLK 'I Have a Dream' speech
[App] Added default track to queue: .../MLKDream_64kb.mp3
[App] Auto-search for: MLK
→ Search shows: MLK-related content, speeches, historical recordings
```

**Scenario 3: Track has no artist metadata**
```
Artist: (none)
Album: "Master of Reality"
→ Auto-search for: Master of Reality
```

---

**Result:** The app now feels alive and populated from the moment it launches, with educational default content and smart automatic search! 🎙️
