"""Plex music browser dialog for SidecarEQ."""

import os
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QLineEdit, QMessageBox, QProgressDialog
)
from PySide6.QtCore import Qt, Signal

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from plexapi.myplex import MyPlexAccount
    PLEX_AVAILABLE = True
except ImportError:
    PLEX_AVAILABLE = False


class PlexBrowserDialog(QDialog):
    """Dialog for browsing and selecting tracks from Plex server."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Browse Plex: Downstairs")
        self.resize(800, 600)
        
        self.plex = None
        self.music_section = None
        self.selected_tracks = []
        
        self._setup_ui()
        self._connect_to_plex()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Status label
        self.status_label = QLabel("Connecting to Plex...")
        layout.addWidget(self.status_label)
        
        # Search box
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search artists, albums, tracks...")
        self.search_box.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_box)
        layout.addLayout(search_layout)
        
        # Tree widget for browsing
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Type", "Count"])
        self.tree.setColumnWidth(0, 400)
        self.tree.setColumnWidth(1, 100)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.tree)
        
        # Instructions
        info_label = QLabel("💡 Double-click artists/albums to expand. Check tracks to add them to queue.")
        info_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.add_button = QPushButton("Add Selected to Queue")
        self.add_button.clicked.connect(self.accept)
        self.add_button.setEnabled(False)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
    
    def _connect_to_plex(self):
        """Connect to Plex server."""
        if not PLEX_AVAILABLE:
            self.status_label.setText("❌ PlexAPI not installed. Run: pip install plexapi")
            return
        
        token = os.getenv('PLEX_TOKEN', '')
        if not token:
            self.status_label.setText("❌ No PLEX_TOKEN in .env file")
            return
        
        try:
            # Connect via MyPlex
            account = MyPlexAccount(token=token)
            
            # Get first server
            servers = [r for r in account.resources() if r.provides == 'server']
            if not servers:
                self.status_label.setText("❌ No Plex servers found")
                return
            
            self.plex = servers[0].connect()
            
            # Get music library
            music_sections = [s for s in self.plex.library.sections() if s.type == 'artist']
            if not music_sections:
                self.status_label.setText("❌ No music libraries found")
                return
            
            self.music_section = music_sections[0]
            
            # Update status
            self.status_label.setText(f"✅ Connected to: {self.plex.friendlyName} - Library: {self.music_section.title} ({self.music_section.totalSize} items)")
            
            # Load initial view (artists)
            self._load_artists()
            
        except Exception as e:
            self.status_label.setText(f"❌ Connection failed: {e}")
            QMessageBox.warning(self, "Plex Connection Error", str(e))
    
    def _load_artists(self):
        """Load all artists into tree."""
        if not self.music_section:
            return
        
        self.tree.clear()
        
        try:
            # Show progress
            progress = QProgressDialog("Loading artists...", "Cancel", 0, 0, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            artists = self.music_section.all()
            
            progress.setMaximum(len(artists))
            
            for i, artist in enumerate(artists):
                if progress.wasCanceled():
                    break
                
                item = QTreeWidgetItem(self.tree, [
                    artist.title,
                    "Artist",
                    str(len(artist.albums()))
                ])
                item.setData(0, Qt.UserRole, artist)  # Store artist object
                
                progress.setValue(i + 1)
            
            progress.close()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load artists: {e}")
    
    def _on_item_double_clicked(self, item, column):
        """Handle double-click to expand artists/albums."""
        plex_obj = item.data(0, Qt.UserRole)
        
        if plex_obj is None:
            return
        
        # If it's an artist, load albums
        if hasattr(plex_obj, 'albums'):
            if item.childCount() == 0:  # Not yet loaded
                try:
                    for album in plex_obj.albums():
                        album_item = QTreeWidgetItem(item, [
                            album.title,
                            "Album",
                            str(len(album.tracks()))
                        ])
                        album_item.setData(0, Qt.UserRole, album)
                    
                    item.setExpanded(True)
                    
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to load albums: {e}")
            else:
                item.setExpanded(not item.isExpanded())
        
        # If it's an album, load tracks
        elif hasattr(plex_obj, 'tracks'):
            if item.childCount() == 0:  # Not yet loaded
                try:
                    for track in plex_obj.tracks():
                        track_item = QTreeWidgetItem(item, [
                            track.title,
                            "Track",
                            ""
                        ])
                        track_item.setData(0, Qt.UserRole, track)
                        track_item.setCheckState(0, Qt.Unchecked)  # Make checkable
                    
                    item.setExpanded(True)
                    
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to load tracks: {e}")
            else:
                item.setExpanded(not item.isExpanded())
    
    def _on_search(self, text):
        """Filter tree based on search text."""
        if not text:
            # Show all items
            for i in range(self.tree.topLevelItemCount()):
                self.tree.topLevelItem(i).setHidden(False)
            return
        
        text_lower = text.lower()
        
        # Hide non-matching items
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            name = item.text(0).lower()
            item.setHidden(text_lower not in name)
    
    def get_selected_tracks(self):
        """Get list of selected track URLs.
        
        Returns:
            List of stream URLs for selected tracks
        """
        selected = []
        
        def check_item(item):
            """Recursively check item and children."""
            # Check if this item is a checked track
            if item.checkState(0) == Qt.Checked:
                plex_obj = item.data(0, Qt.UserRole)
                if plex_obj and hasattr(plex_obj, 'getStreamURL'):
                    selected.append(plex_obj.getStreamURL())
            
            # Check children
            for i in range(item.childCount()):
                check_item(item.child(i))
        
        # Check all top-level items
        for i in range(self.tree.topLevelItemCount()):
            check_item(self.tree.topLevelItem(i))
        
        return selected
