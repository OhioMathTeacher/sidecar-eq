# Online Metadata Integration

## Overview
Sidecar EQ now fetches artist information, biographies, and metadata from multiple online sources including **Wikipedia**, **MusicBrainz**, and **Last.fm**.

## Features

### 1. **Globe Icon Lookup** (Queue Table)
- Click the **🌐** globe icon in the "Lookup" column of any track
- Opens a rich dialog showing comprehensive artist information
- Fetches data from Wikipedia (biography), MusicBrainz (structured data), and Last.fm (stats, images)
- Displays:
  - Artist biography and background
  - Formation year, country, artist type
  - Listener count and play statistics
  - Similar artists
  - Genre tags
  - Links to full artist pages
  - Local track metadata (title, album, file path)

### 2. **Search Panel Integration**
- When you select a track in search results, the info panel automatically fetches online metadata
- Shows artist bio, stats, similar artists, and tags
- Updates asynchronously without blocking the UI
- Falls back gracefully if internet connection unavailable

## Data Sources

### Wikipedia
- **Free, no API key required**
- Provides artist biographies, career information, and background
- Uses intelligent search to find the correct artist page
- Includes direct links to Wikipedia articles

### MusicBrainz
- **Free, no API key required**
- Structured music metadata database
- Provides formation dates, countries, artist types (band, person, etc.)
- Genre/tag information
- Note: May occasionally have connection issues due to rate limiting

### Last.fm *(Optional)*
- **Requires free API key** (get one at https://www.last.fm/api)
- Social music statistics (listener counts, play counts)
- Artist images and photos
- Similar artist recommendations
- User-generated tags and genres
- Currently disabled by default - to enable:
  1. Get a free API key from Last.fm
  2. Edit `sidecar_eq/online_metadata.py`
  3. Replace `YOUR_API_KEY_HERE` with your actual key

## Implementation Details

### Caching
- Results are cached in memory for 1 hour to minimize API requests
- Improves performance and respects API rate limits
- Cache is per artist (not per track)

### Non-Blocking Fetches
- All API calls are designed to not block the UI
- Search panel uses QTimer to fetch asynchronously
- Globe icon dialog shows loading state then updates

### Error Handling
- Graceful fallback if internet unavailable
- Shows error messages in the UI
- Prints debug info to console for troubleshooting

## User Experience

### What to Expect
1. **First click**: May take 1-2 seconds to fetch data from APIs
2. **Subsequent clicks**: Instant (data cached for 1 hour)
3. **No internet**: Shows error message, app continues working normally
4. **API failures**: Falls back to available sources (e.g., if MusicBrainz fails, Wikipedia still works)

### HTML Formatting
- Rich HTML display with proper styling
- Dark theme compatible colors
- Clickable links to full artist pages
- Icons and emojis for visual clarity
- Organized sections (bio, stats, tags, similar artists)

## Technical Architecture

### Module: `sidecar_eq/online_metadata.py`
- `OnlineMetadataFetcher` class handles all API communication
- Methods for each data source: `_fetch_wikipedia_artist()`, `_fetch_musicbrainz_artist()`, `_fetch_lastfm_artist()`
- `fetch_artist_info()` aggregates data from all sources
- `format_artist_info_html()` generates rich HTML for display
- Singleton pattern via `get_metadata_fetcher()`

### Integration Points
1. **app.py**: `_on_metadata_lookup()` - Globe icon click handler
2. **search.py**: `_display_track_info()` - Search result display

### Dependencies
- Uses only Python standard library (`urllib`, `json`, `html`)
- No additional packages required
- PySide6's QTextBrowser for HTML display

## Future Enhancements

### Potential Additions
- [ ] **Genius API** for lyrics
- [ ] **Discogs API** for release information, labels, producers
- [ ] **AllMusic** for detailed album reviews and ratings
- [ ] **Album art fetching** and display
- [ ] **Persistent cache** (save to disk between sessions)
- [ ] **Metadata editing** - allow updating local tags with fetched data
- [ ] **Multiple result selection** when artist name is ambiguous
- [ ] **Background worker thread** for truly async fetches

### Configuration Options
- [ ] User preference for which APIs to use
- [ ] Cache duration setting
- [ ] API key management UI
- [ ] Toggle online lookups on/off

## Testing

### Manual Testing
1. Run the app: `Task: Run Sidecar EQ`
2. Search for "Bob Marley" or any artist in your library
3. Click a result to see online metadata in the info panel
4. Click the 🌐 globe icon on a track in the queue
5. Verify rich artist information appears

### Automated Testing
Run the test script:
```bash
.venv/bin/python test_online_metadata.py
```

Should show successful fetches from Wikipedia for Bob Marley, The Beatles, and Pink Floyd.

## Troubleshooting

### "Connection reset by peer" for MusicBrainz
- This is normal - MusicBrainz has strict rate limiting
- Wikipedia data will still be fetched
- Wait a minute and try again if you need MusicBrainz data

### No data appears
- Check your internet connection
- Look at console output for specific error messages
- Try the test script to isolate the issue

### Wrong artist information
- Wikipedia search prioritizes exact title matches
- Some artist names may be ambiguous
- Future update will allow selecting from multiple results

## API Rate Limits

### Wikipedia
- Generally very permissive
- No hard limits for reasonable use
- Includes User-Agent header to be respectful

### MusicBrainz
- 1 request per second recommended
- May throttle or temporarily block if exceeded
- We include appropriate delays and respect limits

### Last.fm
- 5 requests per second per API key
- Daily limit varies by key type (free tier: sufficient for personal use)
- Disabled by default to avoid requiring API keys

## Privacy & Data
- All API requests are HTTPS (except Last.fm which uses HTTP)
- No personal data transmitted
- Only artist/track names sent to public APIs
- No data collection or tracking
- Fetched data stored only in app memory (cache)

---

**Status**: ✅ **Implemented and Working**
**Version**: Introduced in current session (January 2025)
**Dependencies**: Python standard library only
**Testing**: Verified with Wikipedia (working), MusicBrainz (intermittent), Last.fm (requires API key)
