# View Layout Philosophy

## Core Principle: **Consistency Across Views**

All functionality should work the same regardless of which layout preset is active. Panels may be hidden/collapsed, but:

1. **State Preservation**: Queue contents, current track, EQ settings, search results all persist
2. **Functionality Consistency**: Adding songs from search works identically in all views
3. **Visual Feedback**: Users always see confirmation when actions succeed
4. **Context Awareness**: Even in focused views (EQ Only, Search Only), users need minimal context

## Layout Presets

### **Full View** (Default)
- Queue: Visible, expanded
- EQ: Visible, expanded  
- Search: Visible, expanded
- **Use case**: Full control, see everything

### **Queue Only**
- Queue: Visible, expanded (fills space)
- EQ: Hidden
- Search: Hidden
- **Use case**: Queue management, playlist building

### **EQ Only**
- Queue: Hidden
- EQ: Visible, expanded (fills space)
- Search: Hidden
- **Use case**: Audio tuning, sound design

### **Search & Queue** (Formerly "Search Only")
- Queue: **Visible, compact at bottom** (~30% height)
- EQ: Hidden
- Search: Visible, expanded (~70% height)
- **Use case**: Music discovery and playlist building (Full View minus EQ)
- **Why queue is visible**: 
  - Shows what you're adding TO
  - Visual confirmation when songs added
  - Can still manage queue (delete, reorder)
  - Consistent with "search + queue" behavior
  - This is essentially **Full View minus EQ**

## Design Decisions

### ✅ **Why Queue is Always Accessible**
1. **Visual Feedback**: Click song → See it added immediately
2. **Context**: Know what's already queued before adding
3. **Functionality**: All add/remove/play operations work consistently
4. **Discovery**: See related songs you've already added

### ❌ **Why "Search ONLY" (literally no queue) Doesn't Work**
1. Silent failures: Click song → Nothing visible happens
2. Confusion: "Did it add? Where did it go?"
3. Broken functionality: Can't see what you're building
4. Inconsistent: Works differently than other views

## Implementation Notes

- Panels retain their state (collapsed/expanded) when hidden
- Queue table selection persists across view changes
- Search results persist across view changes
- EQ settings persist per-track
- Current playback position maintained
- Volume/master settings global

## Future Considerations

- Could add toggle to *completely* hide queue in Search view (advanced user preference)
- Could add mini-player controls in Search view for track control without showing EQ
- Could add queue preview tooltip on hover (shows next 3 tracks)
