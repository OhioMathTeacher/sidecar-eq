# Search Bar Quick Start Guide

## 🎸 Getting Started with Search

### Step 1: Index Your Music Library

Before you can search, you need to tell Sidecar EQ where your music is:

1. **Go to**: `File → Index Music Folder for Search...`
2. **Select**: Your main music folder (e.g., `/Users/todd/Music`)
3. **Wait**: Indexing will take a few moments depending on library size
4. **Done!**: You'll see a message showing how many tracks were indexed

### Step 2: Search for Music

Now you can search just like YouTube or Spotify!

#### Basic Search:
- Type artist names: `Black Sabbath`
- Type song titles: `War Pigs`
- Type album names: `Paranoid`

#### Autocomplete:
- As you type, you'll see suggestions
- Press `↓` to select from suggestions
- Press `Tab` or `Enter` to accept

#### Search Results:
- **⭐** = You've saved custom EQ for this track
- **▶42** = Play count (how many times you've played it)
- **Click** result = Add to queue
- **Press Enter** = Add and play immediately

### Step 3: Commands

Search bar also supports power user commands:

- **HELP** - Show help dialog
- **PLAYLIST local** - Load .m3u playlist
- **EQ export** - Export current track's EQ settings

### Keyboard Shortcuts

- **Cmd+F** (Mac) / **Ctrl+F** (Windows/Linux) - Focus search bar
- **Escape** - Close search results
- **↑↓** - Navigate results
- **Enter** - Play first result

### Tips

1. **Search prioritizes YOUR music**: Tracks you've played or customized with EQ appear first!
2. **Fuzzy matching**: Don't worry about exact spelling - "sabbath" finds "Sabbath"
3. **Multiple folders**: You can index multiple folders - just use the menu item again
4. **Re-index**: If you add new music, re-run `Index Music Folder` to update the search

---

## 🔍 What Happens When You Index

The indexer:
1. Scans all audio files (`.mp3`, `.flac`, `.wav`, `.ogg`, `.m4a`, `.aac`, `.wma`)
2. Extracts metadata (title, artist, album) using mutagen
3. Checks your saved settings (play count, EQ status)
4. Builds a searchable database at `~/.sidecar_eq/library_index.json`
5. Updates autocomplete with artists, albums, and your favorite songs

**Note**: First-time indexing may take a minute for large libraries (10k+ tracks). This will be faster in future versions with background/async indexing!
