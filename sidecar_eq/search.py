"""Search functionality for Sidecar EQ.

Provides a search bar widget with instant fuzzy matching and a dropdown
results list. Users can search their music library by typing song names,
artists, or albums - just like YouTube or Spotify.

Key features:
- Fuzzy matching across title, artist, album
- Real-time results as you type
- Shows play count and EQ status (⭐) for each result
- Click to add to queue, Enter to play immediately
- Command parsing (HELP, PLAYLIST, EQ EXPORT, etc.)
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple

from PySide6.QtCore import Qt, Signal, QTimer, QStringListModel
from PySide6.QtGui import QIcon, QKeyEvent
from PySide6.QtWidgets import (
    QWidget, QLineEdit, QListWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QListWidgetItem, QFrame, QCompleter, QSplitter,
    QTextBrowser, QPushButton, QSizePolicy
)


class SearchBar(QWidget):
    """Search bar with fuzzy matching and dropdown results.
    
    This widget provides a YouTube/Spotify-style search experience for
    local music libraries. As users type, it performs fuzzy matching
    against an indexed music library and shows results in a dropdown.
    
    Signals:
        result_selected: Emitted when user selects a result (path, play_now)
        command_entered: Emitted when user enters a command (command_string)
    
    Attributes:
        search_input: QLineEdit for text entry
        results_list: QListWidget showing search results
        index: Current music library index (dict of tracks)
    """
    
    # Signals
    result_selected = Signal(str, bool)  # (file_path, play_immediately)
    command_entered = Signal(str)  # command string
    
    def __init__(self, parent=None):
        """Initialize the search bar widget.
        
        Args:
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.index = {}  # Will be populated by library indexer
        self.completer = None  # Will be set up when index is populated
        self._setup_ui()
        
    def _setup_ui(self):
        """Build the search bar UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Search input container with icon and text field
        search_container = QWidget()
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(8, 8, 8, 8)
        search_layout.setSpacing(8)
        
        # Search icon (placeholder - will use custom icon when available)
        self.search_icon = QLabel("🔍")
        self.search_icon.setStyleSheet("""
            QLabel {
                font-size: 20px;
                padding: 4px;
            }
        """)
        search_layout.addWidget(self.search_icon)
        
        # Search input field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search your library...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: #1e1e1e;
                color: #ffffff;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                selection-background-color: #4a9eff;
            }
            QLineEdit:focus {
                border: 1px solid #5a9eff;
                background: #222222;
            }
        """)
        self.search_input.textChanged.connect(self._on_text_changed)
        self.search_input.returnPressed.connect(self._on_return_pressed)
        search_layout.addWidget(self.search_input, stretch=1)
        
        search_container.setLayout(search_layout)
        search_container.setStyleSheet("""
            QWidget {
                background: #252525;
                border-bottom: 1px solid #333;
            }
        """)
        layout.addWidget(search_container)
        
        # Scrollable results area with multiple categorized columns
        from PySide6.QtWidgets import QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: #1a1a1a;
                border: none;
            }
            QScrollBar:vertical {
                background: #1a1a1a;
                width: 12px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #404040;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #505050;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Container for all category columns
        results_container = QWidget()
        results_container_layout = QHBoxLayout()
        results_container_layout.setContentsMargins(8, 8, 8, 8)
        results_container_layout.setSpacing(8)
        results_container_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        # Create category list widgets
        self.category_lists = {}
        categories = [
            ("Top Plays", "🔥"),
            ("Matching Songs", "🎵"),
            ("Albums", "💿"),
            ("Related Artists", "👥"),
        ]
        
        for category_name, icon in categories:
            category_widget = self._create_category_list(category_name, icon)
            self.category_lists[category_name] = category_widget
            results_container_layout.addWidget(category_widget)
        
        results_container_layout.addStretch()
        results_container.setLayout(results_container_layout)
        
        scroll_area.setWidget(results_container)
        scroll_area.hide()  # Hidden until search results appear
        self.results_scroll_area = scroll_area
        
        layout.addWidget(scroll_area)
        
        # Welcome/help panel (shows when no search performed)
        self.welcome_panel = self._create_welcome_panel()
        layout.addWidget(self.welcome_panel)
        
        self.setLayout(layout)
        
        # Timer for debounced search (wait 150ms after typing stops)
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._perform_search)
        
        # Track current selection and last search query
        self._current_selection = None
        self._last_search_query = None
    
    def _create_welcome_panel(self) -> QWidget:
        """Create welcome/help panel shown before first search."""
        from PySide6.QtWidgets import QTextBrowser
        
        panel = QTextBrowser()
        panel.setOpenExternalLinks(False)
        panel.setStyleSheet("""
            QTextBrowser {
                background: #1a1a1a;
                color: #e0e0e0;
                border: none;
                padding: 20px;
                font-size: 13px;
                line-height: 1.6;
            }
        """)
        
        html = """
        <div style='max-width: 600px; margin: 0 auto; padding: 15px;'>
            <p style='color: #4a9eff; font-size: 14px; margin-bottom: 15px;'>Welcome to SidecarEQ</p>
            
            <p style='color: #c0c0c0; font-size: 11px; line-height: 1.6; margin-bottom: 10px;'>
                Type artist names, song titles, or album names in the search box above. Results appear in categories: 
                Top Plays, Matching Songs, Albums, and Related Artists.
            </p>
            
            <p style='color: #c0c0c0; font-size: 11px; line-height: 1.6; margin-bottom: 10px;'>
                EQ Features: 7-band EQ with LED meters. Settings save automatically per track. 
                Use the save button to manually save (turns green when saved).
            </p>
            
            <p style='color: #c0c0c0; font-size: 11px; line-height: 1.6; margin-bottom: 10px;'>
                Quick Keys: Space = Play/Pause, Enter = Play first result, Double-click = Play from results
            </p>
            
            <p style='color: #c0c0c0; font-size: 11px; line-height: 1.6; margin-bottom: 10px;'>
                Queue Tips: Click the globe icon to fetch online metadata. Drag rows to reorder. 
                Right-click column headers to show/hide columns.
            </p>
            
            <p style='color: #808080; font-size: 10px; font-style: italic; margin-top: 15px;'>
                Start by searching for an artist or song above, or select a track from your queue.
            </p>
        </div>
        """
        
        panel.setHtml(html)
        return panel
    
    def _create_category_list(self, title: str, icon: str) -> QWidget:
        """Create a categorized results list widget.
        
        Args:
            title: Category title (e.g., "Top Plays")
            icon: Emoji icon for the category
            
        Returns:
            QWidget containing the category list
        """
        container = QWidget()
        container.setFixedWidth(220)  # Fixed width for uniform columns
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # Category header
        header = QLabel(f"{icon} {title}")
        header.setStyleSheet("""
            QLabel {
                color: #4a9eff;
                font-size: 11px;
                font-weight: bold;
                padding: 8px 10px;
                background: #252525;
                border: 1px solid #333;
                border-radius: 4px 4px 0 0;
            }
        """)
        container_layout.addWidget(header)
        
        # Results list for this category
        list_widget = QListWidget()
        list_widget.setFixedHeight(300)  # Fixed height for uniform appearance
        list_widget.setStyleSheet("""
            QListWidget {
                background: #2a2a2a;
                color: #ffffff;
                border: 1px solid #333;
                border-top: none;
                border-radius: 0 0 4px 4px;
                outline: none;
                font-family: 'Helvetica Neue', 'Helvetica', 'Arial Narrow', 'Liberation Sans Narrow', sans-serif;
                font-size: 10px;
            }
            QListWidget::item {
                padding: 5px 8px;
                border-bottom: 1px solid #333;
            }
            QListWidget::item:hover {
                background: #3a3a3a;
            }
            QListWidget::item:selected {
                background: #4a9eff;
                color: #ffffff;
            }
        """)
        list_widget.itemDoubleClicked.connect(self._on_category_item_double_clicked)
        container_layout.addWidget(list_widget)
        
        container.setLayout(container_layout)
        
        # Store reference to the list widget
        setattr(container, 'list_widget', list_widget)
        
        return container
        
    def set_icon(self, icon_path: str):
        """Set custom search icon from file path.
        
        Args:
            icon_path: Path to icon file (SVG, PNG, etc.)
        """
        if Path(icon_path).exists():
            icon = QIcon(icon_path)
            pixmap = icon.pixmap(24, 24)
            self.search_icon.setPixmap(pixmap)
            self.search_icon.setStyleSheet("QLabel { padding: 4px; }")
    
    def set_index(self, index: Dict[str, Dict]):
        """Update the music library index for searching.
        
        Args:
            index: Dictionary mapping file paths to track metadata
                   Format: {path: {title, artist, album, play_count, has_eq}}
        """
        self.index = index
        self._update_autocomplete()
    
    def set_search_text(self, text: str):
        """Set the search text programmatically and trigger search.
        
        Args:
            text: Search query to set
        """
        self.search_input.setText(text)
        # Immediately trigger search (bypass debounce timer)
        self._perform_search()
        
    def _on_text_changed(self, text: str):
        """Handle search input text changes with debouncing.
        
        Args:
            text: Current search text
        """
        # Restart the debounce timer
        self._search_timer.stop()
        if text.strip():
            self._search_timer.start(150)  # Wait 150ms before searching
        else:
            self.results_scroll_area.hide()
            
    def _perform_search(self):
        """Execute the search and display categorized results."""
        query = self.search_input.text().strip()
        
        if not query:
            self.results_scroll_area.hide()
            self.welcome_panel.show()
            return
        
        # Cache this search query
        self._last_search_query = query
            
        # Clear all category lists
        for category_widget in self.category_lists.values():
            category_widget.list_widget.clear()
            
        # Perform fuzzy search on all indexed tracks
        query_lower = query.lower()
        matching_tracks = []
        
        for path, meta in self.index.items():
            title = meta.get('title', '').lower()
            artist = meta.get('artist', '').lower()
            album = meta.get('album', '').lower()
            
            # Calculate match score
            score = 0
            if query_lower in title:
                score += 10
            if query_lower in artist:
                score += 8
            if query_lower in album:
                score += 5
            
            if score > 0:
                matching_tracks.append((path, meta, score))
        
        if not matching_tracks:
            self.results_scroll_area.hide()
            self.welcome_panel.show()
            return
        
        # Sort by score
        matching_tracks.sort(key=lambda x: x[2], reverse=True)
        
        # Populate categories
        self._populate_top_plays(matching_tracks)
        self._populate_matching_songs(matching_tracks)
        self._populate_albums(matching_tracks)
        self._populate_related_artists(matching_tracks)
        
        # Hide welcome panel and show results
        self.welcome_panel.hide()
        self.results_scroll_area.show()
        
        print(f"[SearchBar] Found {len(matching_tracks)} matches for '{query}'")
    
    def _populate_top_plays(self, matching_tracks: List[Tuple[str, Dict, int]]):
        """Populate Top Plays category (top 10 by play count)."""
        list_widget = self.category_lists["Top Plays"].list_widget
        
        # Sort by play count
        sorted_tracks = sorted(matching_tracks, key=lambda x: x[1].get('play_count', 0), reverse=True)
        
        for i, (path, meta, _) in enumerate(sorted_tracks[:10]):
            title = meta.get('title', 'Unknown')
            artist = meta.get('artist', 'Unknown')
            plays = meta.get('play_count', 0)
            
            item = QListWidgetItem(f"{i+1}. {title[:25]}{'...' if len(title) > 25 else ''}\n   {artist[:20]} • {plays} plays")
            item.setData(Qt.UserRole, path)
            list_widget.addItem(item)
    
    def _populate_matching_songs(self, matching_tracks: List[Tuple[str, Dict, int]]):
        """Populate Matching Songs category (top 10 by search score)."""
        list_widget = self.category_lists["Matching Songs"].list_widget
        
        for i, (path, meta, score) in enumerate(matching_tracks[:10]):
            title = meta.get('title', 'Unknown')
            artist = meta.get('artist', 'Unknown')
            
            item = QListWidgetItem(f"{i+1}. {title[:25]}{'...' if len(title) > 25 else ''}\n   {artist[:20]}")
            item.setData(Qt.UserRole, path)
            list_widget.addItem(item)
    
    def _populate_albums(self, matching_tracks: List[Tuple[str, Dict, int]]):
        """Populate Albums category (unique albums from matches)."""
        list_widget = self.category_lists["Albums"].list_widget
        
        # Group by album
        albums = {}
        for path, meta, score in matching_tracks:
            album = meta.get('album', 'Unknown Album')
            artist = meta.get('artist', 'Unknown')
            if album not in albums:
                albums[album] = {'artist': artist, 'count': 0, 'path': path}
            albums[album]['count'] += 1
        
        # Sort by track count
        sorted_albums = sorted(albums.items(), key=lambda x: x[1]['count'], reverse=True)
        
        for i, (album, info) in enumerate(sorted_albums[:10]):
            item = QListWidgetItem(f"{i+1}. {album[:25]}{'...' if len(album) > 25 else''}\n   {info['artist'][:20]} • {info['count']} tracks")
            item.setData(Qt.UserRole, info['path'])
            list_widget.addItem(item)
    
    def _populate_related_artists(self, matching_tracks: List[Tuple[str, Dict, int]]):
        """Populate Related Artists category (artists from matching tracks)."""
        list_widget = self.category_lists["Related Artists"].list_widget
        
        # Group by artist
        artists = {}
        for path, meta, score in matching_tracks:
            artist = meta.get('artist', 'Unknown')
            if artist not in artists:
                artists[artist] = {'count': 0, 'plays': 0, 'path': path}
            artists[artist]['count'] += 1
            artists[artist]['plays'] += meta.get('play_count', 0)
        
        # Sort by track count
        sorted_artists = sorted(artists.items(), key=lambda x: x[1]['count'], reverse=True)
        
        for i, (artist, info) in enumerate(sorted_artists[:10]):
            item = QListWidgetItem(f"{i+1}. {artist[:30]}{'...' if len(artist) > 30 else ''}\n   {info['count']} tracks • {info['plays']} plays")
            item.setData(Qt.UserRole, info['path'])
            list_widget.addItem(item)
    
    def _on_category_item_double_clicked(self, item):
        """Handle double-click on category item - add to queue."""
        path = item.data(Qt.UserRole)
        if path:
            self.result_selected.emit(path, True)  # True = play immediately
            
    def _is_command(self, text: str) -> bool:
        """Check if input looks like a command.
        
        Args:
            text: Input text
            
        Returns:
            True if it's a command pattern (WORD ...)
        """
        words = text.split()
        if words and words[0].isupper() and len(words[0]) > 1:
            return True
        return False
        
    def _show_command_hint(self, text: str):
        """Show hint about command syntax.
        
        Args:
            text: Command text
        """
        self.results_list.clear()
        
        cmd = text.split()[0].upper()
        hints = {
            'HELP': 'Press Enter to see available commands',
            'PLAYLIST': 'Usage: PLAYLIST local',
            'EQ': 'Usage: EQ export',
        }
        
        hint = hints.get(cmd, 'Press Enter to execute command')
        item = QListWidgetItem(f"💡 {hint}")
        item.setData(Qt.UserRole, None)  # No file path
        # Note: results_list doesn't exist in category-based search
        # self.results_list.addItem(item)
        # self.results_scroll_area.show()  # Show results if needed
        
    def _fuzzy_search(self, query: str, max_results: int = 20) -> List[Tuple[str, Dict, int]]:
        """Perform fuzzy search across the music index.
        
        Uses simple substring matching with scoring based on:
        - Exact matches score higher than partial
        - Title matches score higher than artist/album
        - Tracks with saved EQ get bonus points
        - More plays get small bonus
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of (path, metadata, score) tuples, sorted by score desc
        """
        query_lower = query.lower()
        query_words = query_lower.split()
        results = []
        
        for path, meta in self.index.items():
            score = 0
            title = meta.get('title', '').lower()
            artist = meta.get('artist', '').lower()
            album = meta.get('album', '').lower()
            
            # Score each query word
            for word in query_words:
                if word in title:
                    score += 10  # Title match is most important
                if word in artist:
                    score += 7   # Artist match is important
                if word in album:
                    score += 5   # Album match is nice
                    
            # Bonus for exact phrase match
            if query_lower in title:
                score += 20
            elif query_lower in artist:
                score += 15
                
            # Bonus for tracks you've customized
            if meta.get('has_eq'):
                score += 3  # Saved EQ = you care about this track
            if meta.get('play_count', 0) > 0:
                score += min(meta['play_count'], 5)  # More plays = more relevant
                
            if score > 0:
                results.append((path, meta, score))
                
        # Sort by score descending
        results.sort(key=lambda x: x[2], reverse=True)
        return results[:max_results]
        
    def _display_results(self, results: List[Tuple[str, Dict, int]]):
        """Display search results in the dropdown list.
        
        Args:
            results: List of (path, metadata, score) tuples
        """
        self.results_list.clear()
        
        for path, meta, _score in results:
            # Format: Title - Artist (just compact info for left panel)
            title = meta.get('title', 'Unknown')
            artist = meta.get('artist', 'Unknown Artist')
            has_eq = meta.get('has_eq', False)
            
            # Build compact display text
            text = f"{title} - {artist}"
            if has_eq:
                text += "  ⭐"
                
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, path)  # Store file path
            self.results_list.addItem(item)
            
        self.split_view.show()
        
        # Auto-select first item to show info
        if self.results_list.count() > 0:
            self.results_list.setCurrentRow(0)
        
    def _show_no_results(self):
        """Show 'no results' message."""
        self.results_list.clear()
        
        if not self.index:
            # No index at all - user needs to index their music
            item = QListWidgetItem("📂 No music indexed yet! Go to File → Index Music Folder for Search...")
        else:
            # Index exists but no matches
            item = QListWidgetItem("No results found. Try different keywords or index more folders!")
            
        item.setData(Qt.UserRole, None)
        self.results_list.addItem(item)
        self.split_view.show()
        
    def _on_result_clicked(self, item: QListWidgetItem):
        """Handle click on a search result - NO LONGER adds to queue automatically.
        User must click 'Add to Queue' button.
        
        Args:
            item: Clicked list item
        """
        # Just highlight it - the button will handle adding
        pass
            
    def _on_return_pressed(self):
        """Handle Enter key in search input."""
        query = self.search_input.text().strip()
        
        if not query:
            return
            
        # Check if it's a command
        if self._is_command(query):
            self.command_entered.emit(query)
            self.search_input.clear()
            # Note: results_list doesn't exist in category-based search
            # self.results_list.hide()
            return
            
        # If results are showing, play the first result from any visible category
        if self.results_scroll_area.isVisible():
            # Find first non-empty category and play its first item
            for category_name, category_widget in self.category_lists.items():
                list_widget = category_widget.findChild(QListWidget)
                if list_widget and list_widget.count() > 0:
                    first_item = list_widget.item(0)
                    path = first_item.data(Qt.UserRole)
                    if path:
                        self.result_selected.emit(path, True)  # Add and play immediately
                        # Keep search results visible so user can browse related tracks
                        break
                
    def _on_result_highlighted(self, current, previous):
        """Handle highlighting a search result (populate info panel).
        
        Args:
            current: Currently highlighted item
            previous: Previously highlighted item
        """
        if not current:
            self._current_selection = None
            self.add_button.setEnabled(False)
            self.info_browser.setHtml("<p style='color: #666; font-size: 11px; padding: 8px;'>Highlight a search result to see details...</p>")
            return
            
        path = current.data(Qt.UserRole)
        if not path:
            self._current_selection = None
            self.add_button.setEnabled(False)
            return
            
        # Enable add button
        self._current_selection = path
        self.add_button.setEnabled(True)
        
        # Fetch and display info
        self._display_track_info(path)
        
    def _display_track_info(self, path: str):
        """Display information about the selected track.
        
        Args:
            path: File path of selected track
        """
        if path not in self.index:
            return
            
        meta = self.index[path]
        title = meta.get('title', 'Unknown')
        artist = meta.get('artist', 'Unknown Artist')
        album = meta.get('album', 'Unknown Album')
        play_count = meta.get('play_count', 0)
        has_eq = meta.get('has_eq', False)
        
        # Build rich HTML info (uniform font, no title captions)
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #e0e0e0; font-size: 11px; padding: 8px;">
            <p style="margin: 4px 0;"><b>{title}</b> by {artist}</p>
            
            <p style="color: #999; margin: 8px 0;">
                <b>Album:</b> {album}
            </p>
            
            <p style="color: #999; margin: 8px 0;">
                <b>Plays:</b> {play_count}
                {"<span style='color: #4a9eff;'> ⭐ EQ Saved</span>" if has_eq else ""}
            </p>
            
            <p style="color: #999; margin: 8px 0;">
                <b>File:</b> <span style="font-size: 11px; color: #666;">{Path(path).name}</span>
            </p>
            
            <hr style="border: none; border-top: 1px solid #404040; margin: 16px 0;">
            
            <p style="color: #666; font-style: italic; font-size: 12px;">
                � Fetching artist information from Wikipedia, MusicBrainz, and Last.fm...
            </p>
        </body>
        </html>
        """
        
        self.info_browser.setHtml(html)
        
        # Fetch online metadata in the background
        # Use a timer to avoid blocking the UI during search
        from PySide6.QtCore import QTimer
        
        def fetch_and_update():
            try:
                from .online_metadata import get_metadata_fetcher
                fetcher = get_metadata_fetcher()
                info = fetcher.fetch_artist_info(artist, title)
                
                local_meta = {
                    'title': title,
                    'artist': artist,
                    'album': album,
                    'path': path
                }
                
                # Format and update the HTML
                html_updated = fetcher.format_artist_info_html(info, local_meta)
                self.info_browser.setHtml(html_updated)
            except Exception as e:
                print(f"[Search] Failed to fetch online metadata: {e}")
                # Show error in the info panel
                error_html = f"""
                <html>
                <body style="font-family: Arial, sans-serif; color: #e0e0e0;">
                    <h2 style="color: #4a9eff;">{title}</h2>
                    <h3 style="color: #888;">{artist}</h3>
                    <p style="color: #999;"><b>Album:</b> {album}</p>
                    <p style="color: #999;"><b>Plays:</b> {play_count}</p>
                    <hr style="border: none; border-top: 1px solid #404040; margin: 16px 0;">
                    <p style="color: #ff6b6b;">❌ Could not fetch online metadata: {str(e)}</p>
                    <p style="color: #666; font-size: 11px;">Check your internet connection.</p>
                </body>
                </html>
                """
                self.info_browser.setHtml(error_html)
        
        # Fetch after a short delay to let the UI update first
        QTimer.singleShot(100, fetch_and_update)
        
    def _on_add_to_queue(self):
        """Handle clicking 'Add to Queue' button."""
        if self._current_selection:
            self.result_selected.emit(self._current_selection, False)  # Add, don't play
            # Keep search open so user can add multiple tracks
                
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard navigation in search.
        
        Args:
            event: Key event
        """
        # Arrow keys navigate results
        if event.key() in (Qt.Key_Down, Qt.Key_Up):
            if self.results_list.isVisible() and self.results_list.count() > 0:
                if event.key() == Qt.Key_Down:
                    current = self.results_list.currentRow()
                    next_row = (current + 1) % self.results_list.count()
                    self.results_list.setCurrentRow(next_row)
                else:  # Up
                    current = self.results_list.currentRow()
                    prev_row = (current - 1) % self.results_list.count()
                    self.results_list.setCurrentRow(prev_row)
                return
                
        # Escape closes results
        if event.key() == Qt.Key_Escape:
            self.split_view.hide()
            return
            
        super().keyPressEvent(event)
        
    def focus_search(self):
        """Give focus to the search input field."""
        self.search_input.setFocus()
        self.search_input.selectAll()
    
    def set_search_text(self, text: str, trigger_search: bool = False):
        """Set the search input text and optionally trigger a search.
        
        Args:
            text: Text to set in the search box
            trigger_search: If True, immediately trigger search and show results
        """
        self.search_input.setText(text)
        if trigger_search:
            self._on_text_changed(text)
    
    def search_for_track(self, title: str, artist: str = "", album: str = ""):
        """Search for a specific track and show results.
        
        This is useful for auto-searching the currently playing track to show
        related songs from the same artist/album.
        
        Args:
            title: Song title
            artist: Artist name (optional)
            album: Album name (optional)
        """
        # Use the most specific info available: prioritize artist, then title, then album
        # This makes the search bar look cleaner and more intentional
        if artist and artist.strip() and artist != "Unknown Artist":
            query = artist.strip()
        elif title and title.strip() and title != "Unknown":
            query = title.strip()
        elif album and album.strip():
            query = album.strip()
        else:
            query = "Unknown"
        
        # Set text and trigger search
        self.set_search_text(query, trigger_search=True)
        
        print(f"[SearchBar] Auto-search for: {query}")
        
    def _update_autocomplete(self):
        """Build autocomplete suggestions from the index."""
        if not self.index:
            return
            
        # Collect unique artists, albums, and popular song titles
        suggestions = set()
        
        for meta in self.index.values():
            # Add artists (most important for autocomplete)
            artist = meta.get('artist', '').strip()
            if artist and artist != 'Unknown Artist':
                suggestions.add(artist)
                
            # Add albums
            album = meta.get('album', '').strip()
            if album:
                suggestions.add(album)
                
            # Add song titles for tracks you've played or customized
            if meta.get('play_count', 0) > 0 or meta.get('has_eq', False):
                title = meta.get('title', '').strip()
                if title and title != 'Unknown':
                    suggestions.add(title)
        
        # Sort suggestions alphabetically
        suggestion_list = sorted(list(suggestions))
        
        # Create completer with case-insensitive matching
        self.completer = QCompleter(suggestion_list, self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setFilterMode(Qt.MatchContains)  # Match anywhere in string
        
        # Style the popup
        popup = self.completer.popup()
        popup.setStyleSheet("""
            QListView {
                background: #2a2a2a;
                color: #ffffff;
                border: 2px solid #5a9eff;
                selection-background-color: #4a9eff;
                font-size: 13px;
                padding: 4px;
            }
        """)
        
        self.search_input.setCompleter(self.completer)
        
        print(f"[SearchBar] Autocomplete ready with {len(suggestion_list)} suggestions")
