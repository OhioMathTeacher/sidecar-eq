"""Plex music browser dialog for SidecarEQ."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QLineEdit, QMessageBox, QProgressDialog
)

from .logging_config import get_logger
import os

logger = get_logger(__name__)

try:
    from plexapi.server import PlexServer
    PLEX_AVAILABLE = True
except ImportError:
    PLEX_AVAILABLE = False


class PlexBrowserDialog(QDialog):
    """Dialog for browsing and selecting tracks from Plex server."""

    def __init__(self, parent=None, server_config=None, username: str | None = None):
        super().__init__(parent)

        self.server_config = server_config or {}
        self.username = username or ""
        self.server_display_name = self.server_config.get('name', 'Plex')

        self.setWindowTitle(f"Browse Plex: {self.server_display_name}")
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
        self.search_box.setEnabled(False)
        search_layout.addWidget(self.search_box)
        layout.addLayout(search_layout)
        
        # Tree widget for browsing
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Type", "Count"])
        self.tree.setColumnWidth(0, 400)
        self.tree.setColumnWidth(1, 100)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.setEnabled(False)
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
        """Connect to Plex server using stored configuration."""
        if not PLEX_AVAILABLE:
            self.status_label.setText("❌ PlexAPI not installed. Run: pip install plexapi")
            return

        host = self.server_config.get('host')
        port = self.server_config.get('port', '32400')
        token = self.server_config.get('token')

        if not host or not token:
            self.status_label.setText("❌ Missing Plex server details.")
            self._show_token_help_dialog()
            return

        if not self.username:
            # Default to first stored user if none explicitly provided
            users = self.server_config.get('users') or []
            if users:
                self.username = users[0].get('username', '')

        if not self.username:
            self.status_label.setText("❌ No Plex user selected. Update server configuration to include at least one user.")
            return

        baseurl = f"http://{host}:{port}"

        try:
            # Connect to Plex server using admin token
            # For now, we skip home user switching and just use the admin token directly
            logger.info(f"Connecting to Plex server at {baseurl} as {self.username}")
            self.plex = PlexServer(baseurl, token=token, timeout=10)
            
            if getattr(self.plex, 'friendlyName', None):
                self.server_display_name = self.plex.friendlyName
                self.setWindowTitle(f"Browse Plex: {self.server_display_name}")

            music_sections = [s for s in self.plex.library.sections() if s.type == 'artist']
            if not music_sections:
                self.status_label.setText("❌ No music libraries found for this user")
                return

            self.music_section = music_sections[0]
            total_items = getattr(self.music_section, 'totalSize', '?')
            self.status_label.setText(
                f"✅ {self.server_display_name}: {self.music_section.title} ({total_items} items)"
            )
            self.add_button.setEnabled(True)
            self.search_box.setEnabled(True)
            self.tree.setEnabled(True)
            self._load_artists()

        except Exception as exc:
            self.add_button.setEnabled(False)
            self.status_label.setText(f"❌ Connection failed: {exc}")
            QMessageBox.warning(self, "Plex Connection Error", str(exc))
    
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
            logger.debug("Double-clicked item has no Plex object attached")
            return
        
        obj_type = item.text(1)  # "Artist", "Album", or "Track"
        obj_name = item.text(0)
        logger.debug(f"Double-clicked {obj_type}: {obj_name}")
        
        # If it's an artist, load albums
        if obj_type == "Artist" or hasattr(plex_obj, 'albums'):
            if item.childCount() == 0:  # Not yet loaded
                try:
                    logger.info(f"Loading albums for artist: {obj_name}")
                    albums = plex_obj.albums()
                    logger.debug(f"Found {len(albums)} albums for {obj_name}")
                    
                    for album in albums:
                        album_item = QTreeWidgetItem(item, [
                            album.title,
                            "Album",
                            str(len(album.tracks()))
                        ])
                        album_item.setData(0, Qt.UserRole, album)
                    
                    item.setExpanded(True)
                    logger.info(f"Successfully loaded {len(albums)} albums for {obj_name}")
                    
                except Exception as e:
                    logger.exception(f"Failed to load albums for {obj_name}")
                    QMessageBox.warning(self, "Error", f"Failed to load albums: {e}")
            else:
                item.setExpanded(not item.isExpanded())
        
        # If it's an album, load tracks
        elif obj_type == "Album" or hasattr(plex_obj, 'tracks'):
            if item.childCount() == 0:  # Not yet loaded
                try:
                    logger.info(f"Loading tracks for album: {obj_name}")
                    tracks = plex_obj.tracks()
                    logger.debug(f"Found {len(tracks)} tracks for {obj_name}")
                    
                    for track in tracks:
                        track_item = QTreeWidgetItem(item, [
                            track.title,
                            "Track",
                            ""
                        ])
                        track_item.setData(0, Qt.UserRole, track)
                        track_item.setCheckState(0, Qt.Unchecked)  # Make checkable
                    
                    item.setExpanded(True)
                    logger.info(f"Successfully loaded {len(tracks)} tracks for {obj_name}")
                    
                except Exception as e:
                    logger.exception(f"Failed to load tracks for {obj_name}")
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
        """Get list of selected Plex track objects with metadata.
        
        Returns:
            List of dicts with track metadata and stream URL
        """
        selected = []
        prefer_flac = os.getenv("PLEX_PREFER_FLAC", "0") in ("1", "true", "True", "yes", "YES")
        
        def check_item(item):
            """Recursively check item and children."""
            # Check if this item is a checked track
            if item.checkState(0) == Qt.Checked:
                plex_obj = item.data(0, Qt.UserRole)
                if plex_obj and hasattr(plex_obj, 'getStreamURL'):
                    try:
                        # Get DIRECT download URL instead of HLS stream (better Qt compatibility)
                        # Use media parts to get the actual file instead of transcoded stream
                        stream_url = None
                        # Prefer FLAC transcode when requested
                        if prefer_flac:
                            try:
                                stream_url = plex_obj.getStreamURL(audioCodec='flac', audioContainer='flac')
                                logger.debug(f"Using FLAC transcode stream for {plex_obj.title}: {str(stream_url)[:100]}...")
                            except Exception as _e:
                                logger.debug(f"FLAC transcode not available for {plex_obj.title}, falling back: {_e}")
                        if hasattr(plex_obj, 'media') and plex_obj.media:
                            media = plex_obj.media[0]
                            if hasattr(media, 'parts') and media.parts:
                                part = media.parts[0]
                                # Get direct file URL with authentication token
                                if not stream_url:
                                    stream_url = plex_obj._server.url(part.key, includeToken=True)
                                logger.debug(f"Got DIRECT file URL for {plex_obj.title}: {stream_url[:100]}...")
                        
                        # Fallback to HLS stream if direct URL not available
                        if not stream_url:
                            if prefer_flac:
                                try:
                                    stream_url = plex_obj.getStreamURL(audioCodec='flac', audioContainer='flac')
                                except Exception:
                                    stream_url = plex_obj.getStreamURL()
                            else:
                                stream_url = plex_obj.getStreamURL()
                            logger.debug(f"Using HLS stream URL for {plex_obj.title}: {stream_url[:100]}...")
                        
                        if not isinstance(stream_url, str):
                            logger.error(f"Stream URL is {type(stream_url)} instead of str: {stream_url}")
                            return
                        
                        # Extract comprehensive metadata from Plex track
                        track_info = {
                            "path": stream_url,
                            "stream_url": stream_url,  # CRITICAL: Add stream_url field for queue model
                            "title": plex_obj.title,
                            "artist": getattr(plex_obj, 'grandparentTitle', '') or getattr(plex_obj, 'originalTitle', ''),
                            "album": getattr(plex_obj, 'parentTitle', ''),
                            "year": getattr(plex_obj, 'year', None),
                            "duration": getattr(plex_obj, 'duration', 0) / 1000.0 if hasattr(plex_obj, 'duration') else None,  # Plex uses ms
                            "bitrate": f"{getattr(plex_obj, 'bitrate', 0)} kbps" if hasattr(plex_obj, 'bitrate') else None,
                            "rating": getattr(plex_obj, 'userRating', 0) or 0,
                            "source": "plex",
                            "is_video": False,
                            "play_count": 0,
                        }
                    except Exception as e:
                        logger.exception(f"Failed to get stream URL for track {plex_obj.title}: {e}")
                        return
                    
                    # Add media info if available
                    if hasattr(plex_obj, 'media') and plex_obj.media:
                        media = plex_obj.media[0]
                        if hasattr(media, 'audioCodec'):
                            track_info["format"] = media.audioCodec.upper()
                        if hasattr(media, 'audioChannels'):
                            track_info["channels"] = media.audioChannels
                        if hasattr(media, 'parts') and media.parts:
                            part = media.parts[0]
                            if hasattr(part, 'container'):
                                track_info["container"] = part.container.upper()
                    
                    selected.append(track_info)
            
            # Check children
            for i in range(item.childCount()):
                check_item(item.child(i))
        
        # Check all top-level items
        for i in range(self.tree.topLevelItemCount()):
            check_item(self.tree.topLevelItem(i))
        
        return selected

    def _show_token_help_dialog(self):
        """Show helpful dialog explaining how to get Plex token and configure server."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Plex Server Configuration Required")
        msg.setText("🔑 Plex Token Required")
        msg.setInformativeText(
            "To browse and play music from Plex, you need to configure your server with a valid token.\n\n"
            "The easiest way to get your Plex token:\n"
            "  1. Sign in to plex.tv in your browser\n"
            "  2. Visit: https://plex.tv/devices.xml\n"
            "  3. Find your token in the XML response\n\n"
            "Click 'Configure Server' below to open the Plex Server Manager and enter your token."
        )

        # Add Configure button
        configure_btn = msg.addButton("Configure Server", QMessageBox.ButtonRole.AcceptRole)
        msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

        msg.exec()

        # If user clicked Configure, open the Plex Account Manager
        if msg.clickedButton() == configure_btn:
            # Close this dialog and signal parent to open manager
            self.reject()
            # Try to get parent app and open manager
            parent = self.parent()
            if parent and hasattr(parent, '_open_plex_account_manager'):
                parent._open_plex_account_manager()  # type: ignore
