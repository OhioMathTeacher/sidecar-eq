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
        self.search_input.setPlaceholderText("Search songs, artists, albums... (or try HELP)")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: #2a2a2a;
                color: #ffffff;
                border: 2px solid #404040;
                border-radius: 6px;
                padding: 10px 14px;
                font-size: 14px;
                selection-background-color: #4a9eff;
            }
            QLineEdit:focus {
                border: 2px solid #5a9eff;
                background: #303030;
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
        
        # Split view: Results (left) | Info panel (right)
        self.split_view = QSplitter(Qt.Horizontal)
        self.split_view.setHandleWidth(1)
        self.split_view.setStyleSheet("""
            QSplitter::handle {
                background: #404040;
            }
        """)
        self.split_view.hide()  # Hidden until search results appear
        
        # LEFT: Results list (compact - just title & artist)
        results_widget = QWidget()
        results_layout = QVBoxLayout()
        results_layout.setContentsMargins(0, 0, 0, 0)
        results_layout.setSpacing(0)
        
        self.results_list = QListWidget()
        self.results_list.setStyleSheet("""
            QListWidget {
                background: #2a2a2a;
                color: #ffffff;
                border: 1px solid #404040;
                border-top: none;
                outline: none;
            }
            QListWidget::item {
                padding: 8px 14px;
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
        self.results_list.itemClicked.connect(self._on_result_clicked)
        self.results_list.currentItemChanged.connect(self._on_result_highlighted)
        results_layout.addWidget(self.results_list)
        results_widget.setLayout(results_layout)
        
        # RIGHT: Info panel (artist/song info)
        info_widget = QWidget()
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(8, 8, 8, 8)
        info_layout.setSpacing(8)
        
        # Info panel header
        self.info_header = QLabel("Select a track to see info")
        self.info_header.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 12px;
                font-style: italic;
            }
        """)
        info_layout.addWidget(self.info_header)
        
        # Info browser (shows artist/song details from web)
        self.info_browser = QTextBrowser()
        self.info_browser.setStyleSheet("""
            QTextBrowser {
                background: #252525;
                color: #e0e0e0;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        self.info_browser.setOpenExternalLinks(True)
        self.info_browser.setHtml("<p style='color: #666'>Highlight a search result to see details...</p>")
        info_layout.addWidget(self.info_browser)
        
        # Add to queue button (explicit action)
        self.add_button = QPushButton("➕ Add to Queue")
        self.add_button.setStyleSheet("""
            QPushButton {
                background: #0d4f8f;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #1a5fa0;
            }
            QPushButton:pressed {
                background: #0a3d70;
            }
            QPushButton:disabled {
                background: #333;
                color: #666;
            }
        """)
        self.add_button.clicked.connect(self._on_add_to_queue)
        self.add_button.setEnabled(False)  # Disabled until item selected
        info_layout.addWidget(self.add_button)
        
        info_widget.setLayout(info_layout)
        
        # Add both widgets to splitter (30% results, 70% info)
        self.split_view.addWidget(results_widget)
        self.split_view.addWidget(info_widget)
        self.split_view.setSizes([300, 700])  # 30/70 split
        
        layout.addWidget(self.split_view)
        
        # Spacer to push everything up
        layout.addStretch()
        
        self.setLayout(layout)
        
        # Timer for debounced search (wait 150ms after typing stops)
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._perform_search)
        
        # Track currently selected item for info fetching
        self._current_selection = None
        
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
            self.split_view.hide()
            
    def _perform_search(self):
        """Execute the search and display results."""
        query = self.search_input.text().strip()
        
        if not query:
            self.split_view.hide()
            return
            
        # Check if it's a command (starts with uppercase word)
        if self._is_command(query):
            self._show_command_hint(query)
            return
            
        # Perform fuzzy search
        results = self._fuzzy_search(query, max_results=20)
        
        if results:
            self._display_results(results)
        else:
            self._show_no_results()
            
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
        self.results_list.addItem(item)
        self.split_view.show()
        
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
            self.results_list.hide()
            return
            
        # If results are showing, play the first one
        if self.split_view.isVisible() and self.results_list.count() > 0:
            first_item = self.results_list.item(0)
            path = first_item.data(Qt.UserRole)
            if path:
                self.result_selected.emit(path, True)  # Add and play immediately
                self.search_input.clear()
                self.split_view.hide()
                
    def _on_result_highlighted(self, current, previous):
        """Handle highlighting a search result (populate info panel).
        
        Args:
            current: Currently highlighted item
            previous: Previously highlighted item
        """
        if not current:
            self._current_selection = None
            self.add_button.setEnabled(False)
            self.info_browser.setHtml("<p style='color: #666'>Highlight a search result to see details...</p>")
            self.info_header.setText("Select a track to see info")
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
        
        # Update header
        self.info_header.setText(f"{title} - {artist}")
        
        # Build rich HTML info
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #e0e0e0;">
            <h2 style="color: #4a9eff; margin-bottom: 8px;">{title}</h2>
            <h3 style="color: #888; margin-top: 0; font-weight: normal;">{artist}</h3>
            
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
                🚧 Artist/song information from AllMusic or Wikipedia will appear here in a future update.
                For now, this shows your local library metadata.
            </p>
        </body>
        </html>
        """
        
        self.info_browser.setHtml(html)
        
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
