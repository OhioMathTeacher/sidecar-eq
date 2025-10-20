# Layout View Rename: "Search Only" → "Search & Queue"

## Change Summary

Renamed the fourth layout preset from **"Search Only"** to **"Search & Queue"** to better reflect what the view actually shows.

## Rationale

### The Problem with "Search Only"

The name "Search Only" implied that **only** the search panel would be visible. However, the implementation shows:
- Search panel (70% of space, expanded)
- Queue panel (30% of space, compact)

This creates a misleading name that doesn't match the user's experience.

### Why "Search & Queue" is Better

1. **Accurate**: Describes what you actually see
2. **Clear intent**: This is for browsing music and building playlists
3. **Distinguishes from Full View**: It's "Full View minus EQ"
4. **Sets expectations**: Users know they'll see both search and queue

## What Changed

### User-Facing Text
- Menu item: "Search Only" → "Search & Queue"
- Dropdown combo: "Search Only" → "Search & Queue"
- Docstrings: Updated to reflect new name

### Code Comments
- Updated comments to explain: "Search & Queue View (Full View minus EQ)"
- Debug messages now say "Applied Search & Queue layout"

### Documentation
- `VIEW_LAYOUT_PHILOSOPHY.md`: Updated section heading and explanation
- `ALBUM_ARTIST_SUPPORT.md`: References remain as "Search Only view" in historical context

## Internal Implementation

The internal preset ID remains `"search_only"` to avoid breaking:
- Saved user preferences
- Settings files
- Any hardcoded references

This is fine - internal IDs don't need to match display names.

## Files Modified

- `sidecar_eq/app.py`:
  - Layout dropdown items
  - Menu action text (note: uses `"Search && Queue"` due to Qt's & escaping)
  - Comments and debug messages
  - Docstrings

- `docs/VIEW_LAYOUT_PHILOSOPHY.md`:
  - Section heading
  - Description and use case
  - Added note: "essentially Full View minus EQ"

## User Impact

Minimal - this is just a label change. Behavior is identical:
- Same keyboard shortcuts (if any)
- Same menu location
- Same layout behavior
- Saved preferences still work

Users will just see a more accurate description of what the view shows.

## Visual Change

**Before:**
```
View > Search Only        [Menu]
[Full View ▼]            [Dropdown shows: Search Only]
```

**After:**
```
View > Search & Queue     [Menu]
[Full View ▼]            [Dropdown shows: Search & Queue]
```

## Future Considerations

If we ever add a **true** "Search Only" view (search panel with NO queue), we could:
- Name it "Search Only" or "Browse Only"  
- Or better: just keep "Search & Queue" as-is since the queue visibility is essential for UX

The current design philosophy is that **visual feedback requires the queue to be visible**, so a completely isolated search panel would be an anti-pattern.
