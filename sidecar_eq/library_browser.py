"""Local library browser widget for SidecarEQ."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QLineEdit, QSplitter
)


class LibraryBrowserWidget(QWidget):
    """Widget for browsing local music library with optional artist info pane."""
    
    # Signal emitted when user wants to add tracks to queue
    tracks_selected = Signal(list)  # List of file paths
    
    # Signal emitted when an artist is clicked (for info pane)
    artist_clicked = Signal(str, str)  # artist_name, album_name (or empty string)
    
    def __init__(self, library=None, artist_info_widget=None, parent=None):
        """Initialize the library browser.
        
        Args:
            library: Library object from indexer (has artists, albums, songs)
            artist_info_widget: Optional artist info widget to show in split view
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.library = library
        self.artist_info_widget = artist_info_widget
        self.show_info_pane = False  # Toggle between browser-only and split view
        
        self._setup_ui()
        if self.library:
            self._populate_tree()
    
    def _setup_ui(self):
        """Setup the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Top toolbar
        toolbar = QWidget()
        toolbar.setStyleSheet("QWidget { background: #2a2a2a; padding: 8px; }")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 4, 8, 4)
        
        # Search box
        search_label = QLabel("🔍")
        toolbar_layout.addWidget(search_label)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search artists, albums, tracks...")
        self.search_box.textChanged.connect(self._on_search)
        self.search_box.setStyleSheet("""
            QLineEdit {
                background: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 6px;
                font-size: 13px;
            }
        """)
        toolbar_layout.addWidget(self.search_box, 1)
        
        # Toggle info pane button
        self.toggle_info_btn = QPushButton("Show Info")
        self.toggle_info_btn.setCheckable(True)
        self.toggle_info_btn.setChecked(False)
        self.toggle_info_btn.clicked.connect(self._toggle_info_pane)
        self.toggle_info_btn.setStyleSheet("""
            QPushButton {
                background: #3a3a3a;
                color: #e0e0e0;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover { background: #4a4a4a; }
            QPushButton:checked { background: #4a9eff; color: white; }
        """)
        if not self.artist_info_widget:
            self.toggle_info_btn.setVisible(False)  # Hide if no info widget provided
        toolbar_layout.addWidget(self.toggle_info_btn)
        
        # Add selected button
        self.add_button = QPushButton("➕ Add Selected")
        self.add_button.clicked.connect(self._on_add_selected)
        self.add_button.setStyleSheet("""
            QPushButton {
                background: #4a9eff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background: #5aa9ff; }
            QPushButton:pressed { background: #3a8eef; }
        """)
        toolbar_layout.addWidget(self.add_button)
        
        layout.addWidget(toolbar)
        
        # Main content: splitter for browser + optional info pane
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Top: Tree browser
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Type", "Count"])
        self.tree.setColumnWidth(0, 350)
        self.tree.setColumnWidth(1, 80)
        self.tree.setColumnWidth(2, 60)
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.itemExpanded.connect(self._on_item_expanded)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background: #1e1e1e;
                color: #e0e0e0;
                border: none;
                font-size: 13px;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:hover {
                background: #2a2a2a;
            }
            QTreeWidget::item:selected {
                background: #4a9eff;
            }
        """)
        self.splitter.addWidget(self.tree)
        
        # Bottom: Artist info pane (initially hidden)
        if self.artist_info_widget:
            self.artist_info_widget.setVisible(False)
            self.splitter.addWidget(self.artist_info_widget)
        
        layout.addWidget(self.splitter, 1)
        
        # Status bar
        self.status_label = QLabel("💿 Ready to browse")
        self.status_label.setStyleSheet("QLabel { color: #888; font-size: 11px; padding: 4px 8px; }")
        layout.addWidget(self.status_label)
    
    def set_library(self, library):
        """Update the library and refresh the tree."""
        self.library = library
        self._populate_tree()
    
    def _populate_tree(self):
        """Populate the tree with artists from the library."""
        self.tree.clear()
        
        if not self.library or not hasattr(self.library, 'artists'):
            self.status_label.setText("⚠️ No library loaded")
            return
        
        artists = self.library.artists
        if not artists:
            self.status_label.setText("⚠️ Library is empty. Use File → Index Music Folder to scan your music collection")
            return
        
        # Create artist items
        for artist_name in sorted(artists.keys(), key=str.lower):
            artist = artists[artist_name]
            artist_item = QTreeWidgetItem(self.tree)
            artist_item.setText(0, artist.name)
            artist_item.setText(1, "Artist")
            artist_item.setText(2, str(len(artist.albums)))
            artist_item.setCheckState(0, Qt.CheckState.Unchecked)
            artist_item.setData(0, Qt.UserRole, {"type": "artist", "name": artist.name})
            
            # Lazy load albums (will expand when arrow is clicked)
            artist_item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
        
        self.status_label.setText(f"💿 {len(artists)} artists in library")
    
    def _on_item_expanded(self, item):
        """Handle item expansion: lazy-load albums for artists, tracks for albums."""
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        
        item_type = data.get("type")
        
        if item_type == "artist" and item.childCount() == 0:
            # Lazy load albums for this artist
            artist_name = data.get("name")
            artist = self.library.artists.get(artist_name)
            if artist:
                for album_title in sorted(artist.albums.keys(), key=str.lower):
                    album = artist.albums[album_title]
                    album_item = QTreeWidgetItem(item)
                    album_item.setText(0, album.title or "Unknown Album")
                    album_item.setText(1, "Album")
                    album_item.setText(2, str(len(album.songs)))
                    album_item.setCheckState(0, Qt.CheckState.Unchecked)
                    album_item.setData(0, Qt.UserRole, {
                        "type": "album",
                        "artist": artist_name,
                        "album": album.title
                    })
                    album_item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
        
        elif item_type == "album" and item.childCount() == 0:
            # Lazy load tracks for this album
            artist_name = data.get("artist")
            album_title = data.get("album")
            print(f"[LibraryBrowser] Loading tracks for {artist_name} - {album_title}")
            artist = self.library.artists.get(artist_name)
            if artist:
                album = artist.albums.get(album_title)
                if album:
                    print(f"[LibraryBrowser] Found album with {len(album.songs)} songs")
                    for song in sorted(album.songs, key=lambda s: s.title or ""):
                        track_item = QTreeWidgetItem(item)
                        track_item.setText(0, song.title or "Unknown Track")
                        track_item.setText(1, "Track")
                        track_item.setText(2, "")
                        track_item.setCheckState(0, Qt.CheckState.Unchecked)
                        track_item.setData(0, Qt.UserRole, {
                            "type": "track",
                            "path": song.path
                        })
                    print(f"[LibraryBrowser] Added {item.childCount()} tracks to album item")
                else:
                    print(f"[LibraryBrowser] Album not found: {album_title}")
            else:
                print(f"[LibraryBrowser] Artist not found: {artist_name}")

    def _on_item_clicked(self, item, column):
        """Handle single click: emit artist_clicked signal for info pane update."""
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        
        item_type = data.get("type")
        
        if item_type == "artist":
            artist_name = data.get("name")
            print(f"[LibraryBrowser] Artist clicked: {artist_name}")
            self.artist_clicked.emit(artist_name, "")  # Empty album means show artist info
        elif item_type == "album":
            artist_name = data.get("artist")
            album_title = data.get("album")
            print(f"[LibraryBrowser] Album clicked: {artist_name} - {album_title}")
            self.artist_clicked.emit(artist_name, album_title)
    
    def _on_search(self, text):
        """Filter tree items based on search text."""
        if not text:
            # Show all items
            for i in range(self.tree.topLevelItemCount()):
                self.tree.topLevelItem(i).setHidden(False)
            return
        
        text_lower = text.lower()
        
        # Hide/show artists based on match
        for i in range(self.tree.topLevelItemCount()):
            artist_item = self.tree.topLevelItem(i)
            artist_name = artist_item.text(0).lower()
            artist_item.setHidden(text_lower not in artist_name)
    
    def _on_add_selected(self):
        """Collect all checked tracks and emit tracks_selected signal."""
        selected_paths = []
        
        # Iterate through all items to find checked tracks
        def collect_checked(item):
            if item.checkState(0) == Qt.CheckState.Checked:
                data = item.data(0, Qt.UserRole)
                if data and data.get("type") == "track":
                    path = data.get("path")
                    if path:
                        selected_paths.append(path)
            
            # Recursively check children
            for i in range(item.childCount()):
                collect_checked(item.child(i))
        
        # Check all top-level items
        for i in range(self.tree.topLevelItemCount()):
            collect_checked(self.tree.topLevelItem(i))
        
        if selected_paths:
            self.tracks_selected.emit(selected_paths)
            self.status_label.setText(f"✅ Added {len(selected_paths)} track(s) to queue")
            # Uncheck all items
            self._uncheck_all()
        else:
            self.status_label.setText("⚠️ No tracks selected")
    
    def _uncheck_all(self):
        """Uncheck all items in the tree."""
        def uncheck_item(item):
            item.setCheckState(0, Qt.CheckState.Unchecked)
            for i in range(item.childCount()):
                uncheck_item(item.child(i))
        
        for i in range(self.tree.topLevelItemCount()):
            uncheck_item(self.tree.topLevelItem(i))
    
    def _toggle_info_pane(self, checked):
        """Toggle the artist info pane visibility."""
        if not self.artist_info_widget:
            return
        
        self.show_info_pane = checked
        self.artist_info_widget.setVisible(checked)
        
        if checked:
            self.toggle_info_btn.setText("Hide Info")
            # Set splitter sizes: 60% browser (top), 40% info (bottom)
            total_height = self.splitter.height()
            self.splitter.setSizes([int(total_height * 0.6), int(total_height * 0.4)])
        else:
            self.toggle_info_btn.setText("Show Info")
