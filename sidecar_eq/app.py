"""Sidecar EQ - Educational audio player with thermometer-style EQ interface.

This is the main application module containing the MainWindow class and
the primary UI logic. The application provides:

- Multi-source playback (local files, YouTube URLs, Plex media servers)
- 7-band thermometer EQ interface with per-track persistence
- Background audio analysis (frequency response, tempo, etc.)
- Queue management with drag-and-drop support
- Recently played tracks history
- Save/load playlist functionality

The UI is built using PySide6 (Qt6) and consists of:
- Top toolbar with playback controls and source selector
- Central queue table showing tracks
- Right side panel with volume knob, EQ faders, and recently played
- Bottom status bar with seek slider and time display
"""

"""Sidecar EQ - Educational audio player with thermometer-style EQ interface.

This is the main application module containing the MainWindow class and
the primary UI logic. The application provides:

- Multi-source playback (local files, YouTube URLs, Plex media servers)
- 7-band thermometer EQ interface with per-track persistence
- Background audio analysis (frequency response, tempo, etc.)
- Queue management with drag-and-drop support
- Recently played tracks history
- Save/load playlist functionality

The UI is built using PySide6 (Qt6) and consists of:
- Top toolbar with playback controls and source selector
- Central queue table showing tracks
- Right side panel with volume knob, EQ faders, and recently played
- Bottom status bar with seek slider and time display
"""

# Standard library imports
import json
import math
import os
import sys
from pathlib import Path
from typing import Optional

# Third-party imports
import logging
from dotenv import load_dotenv
from plexapi.server import PlexServer
from PySide6.QtCore import QDateTime, QModelIndex, QObject, QSize, Qt, QThread, QTimer, Signal, QPoint
from PySide6.QtGui import QAction, QIcon, QKeyEvent, QKeySequence, QPainter, QPixmap, QColor
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDial,
    QFileDialog,
    QHeaderView,
    QInputDialog,
    QLabel,
    QFrame,
    QDialog,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QSplitter,
    QStyle,
    QTableView,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

# Local imports
from .logging_config import configure_logging, get_logger
from . import playlist, store
from .collapsible_panel import CollapsiblePanel
from .indexer import LibraryIndexer
try:
    from .modern_ui import SystemFonts, ModernColors, IconManager, Typography
    USE_MODERN_UI = True
except ImportError:
    USE_MODERN_UI = False
from .music_metadata import MusicMetadataFetcher
from .player import Player
from .queue_model import QueueModel
from .plex_helpers import get_playlist_titles, get_tracks_for_playlist
from .scrolling_label import ScrollingLabel
from .star_rating_delegate import StarRatingDelegate
from .ui import IconButton, KnobWidget, QueueTableView, SnapKnobWidget, WaveformProgress
from .settings_panel import SettingsDialog
from .rack import RackView
from .workers import BackgroundAnalysisWorker

# Media file extensions
AUDIO_EXTS = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".flv", ".m4v", ".webm", ".wmv", ".3gp"}
MEDIA_EXTS = AUDIO_EXTS | VIDEO_EXTS


# Configure logging early in application startup
configure_logging()
logger = get_logger(__name__)


class MetadataLoaderWorker(QObject):
    """Background worker for loading metadata asynchronously."""

    metadata_loaded = Signal(int, dict)  # row_index, metadata_dict
    finished = Signal()

    def __init__(self, model, row_indices):
        super().__init__()
        self.model = model
        self.row_indices = row_indices
        self._should_stop = False

    def stop(self):
        """Signal the worker to stop processing."""
        self._should_stop = True

    def run(self):
        """Extract metadata for all rows that need it."""
        from .metadata_extractor import extract_comprehensive_metadata

        for row_index in self.row_indices:
            if self._should_stop:
                break

            # Extract metadata (this is the slow I/O operation)
            metadata = self.model.extract_metadata_for_row(row_index)

            if metadata:
                # Emit signal with results
                self.metadata_loaded.emit(row_index, metadata)

        self.finished.emit()


class ArtistMetadataWorker(QObject):
    """Background worker for fetching artist metadata from network."""

    finished = Signal(dict, str, str)  # artist_info, artwork_url, tracks_data
    error = Signal(str)

    def __init__(self, metadata_fetcher, artist, album):
        super().__init__()
        self.metadata_fetcher = metadata_fetcher
        self.artist = artist
        self.album = album

    def run(self):
        """Fetch artist metadata (runs in background thread)."""
        try:
            # Fetch artist info
            artist_info = self.metadata_fetcher.get_artist_info(self.artist, self.album)

            # Fetch artwork
            artwork_url = None
            if self.album:
                artwork_url = self.metadata_fetcher.get_album_artwork(self.artist, self.album)

            # Fetch tracklist
            tracks_data = None
            if self.album:
                tracks_data = self.metadata_fetcher.get_album_tracklist(self.artist, self.album)

            # Emit all results together
            result = {
                'artist_info': artist_info,
                'artwork_url': artwork_url,
                'tracks': tracks_data
            }
            self.finished.emit(result, self.artist, self.album)

        except Exception as e:
            print(f"[App] [BG] Failed to fetch artist metadata: {e}")
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))


class CustomTableHeader(QHeaderView):
    """Custom table header with column management via context menu.

    Features:
    - Right-click context menu to hide/show columns
    - Drag-to-reorder columns (built-in QHeaderView feature)
    - Visual indicator (⋮) on hover
    """

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.setSectionsMovable(True)  # Enable drag-to-reorder
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)

        # Store column names for menu
        self.column_names = [
            "Lookup", "Status", "Title", "Artist", "Album", "Year",
            "Label", "Producer", "Rating", "Bitrate", "Format",
            "Sample Rate", "Bit Depth", "Duration", "Play Count"
        ]

    def _show_context_menu(self, pos: QPoint):
        """Show context menu with column visibility options."""
        logical_index = self.logicalIndexAt(pos)

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #404040;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px 6px 12px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background: #4a9eff;
            }
            QMenu::separator {
                height: 1px;
                background: #404040;
                margin: 4px 8px;
            }
        """)

        # Add "Show/Hide Columns" submenu
        columns_menu = menu.addMenu("⋮ Columns")

        # Don't allow hiding first two columns (Lookup and Status)
        for col in range(2, self.count()):
            col_name = self.column_names[col] if col < len(self.column_names) else f"Column {col}"
            action = columns_menu.addAction(col_name)
            action.setCheckable(True)
            action.setChecked(not self.isSectionHidden(col))
            action.triggered.connect(lambda checked, c=col: self._toggle_column(c, checked))

        columns_menu.addSeparator()

        # Add "Reset Columns" option
        reset_action = columns_menu.addAction("Reset to Default")
        reset_action.triggered.connect(self._reset_columns)

        menu.exec(self.mapToGlobal(pos))

    def _toggle_column(self, col: int, visible: bool):
        """Toggle column visibility."""
        self.setSectionHidden(col, not visible)

    def _reset_columns(self):
        """Reset all columns to visible and default order."""
        # Show all columns
        for col in range(self.count()):
            self.setSectionHidden(col, False)

        # Reset to original order (requires moving sections back)
        for visual_index in range(self.count()):
            logical_index = self.logicalIndex(visual_index)
            if logical_index != visual_index:
                self.moveSection(self.visualIndex(visual_index), visual_index)


class _StripesOverlay(QWidget):
    """A transparent overlay that paints subtle stripes to suggest rows when the queue is empty."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._stripe_h = 24
        self._c1 = QColor(255, 255, 255, 6)  # very subtle
        self._c2 = QColor(255, 255, 255, 0)

        # Optional hint label
        self._hint = QLabel("Drop songs here or use Add", self)
        self._hint.setStyleSheet("color: rgba(255,255,255,0.35); font-size: 11px; padding: 4px 8px;")
        self._hint.move(12, 12)

    def resizeEvent(self, event):
        self._hint.move(12, 12)
        return super().resizeEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        y = 0
        h = self.height()
        w = self.width()
        toggle = False
        while y < h:
            p.fillRect(0, y, w, self._stripe_h, self._c1 if toggle else self._c2)
            toggle = not toggle
            y += self._stripe_h
        p.end()


class MainWindow(QMainWindow):
    """Main application window for Sidecar EQ.

    This class orchestrates the entire UI, building the toolbar with playback
    controls, the central queue table, the side panel with EQ controls, and
    the status bar. It manages:

    - Audio playback via Player wrapper (QMediaPlayer)
    - Queue model (add, remove, reorder tracks)
    - Background analysis workers for audio processing
    - Per-track EQ settings persistence
    - Recently played tracks history
    - Plex server integration (optional)

    The window layout consists of:
    - Top: Toolbar (play, stop, add, source selector, etc.)
    - Center: Queue table view
    - Right: Dock with volume knob, 7-band EQ faders, recently played list
    - Bottom: Status bar with seek slider and time display

    Attributes:
        model: QueueModel managing the playlist/queue
        table: QueueTableView displaying the queue
        player: Player instance wrapping QMediaPlayer
        current_row: Currently playing row index (or None)

    Args:
        parent: Parent widget (optional).
    """

    def __init__(self, parent=None):
        """Initialize the main window and build the UI.

        Creates the queue model, player, and table view, then calls builder
        methods to construct the toolbar, side panel, and status bar. Finally
        wires all signals and applies dock sizing.

        Args:
            parent: Parent widget, defaults to None.
        """
        super().__init__(parent)
        try:
            # On macOS, ensure toolbar doesn't merge into title bar invisibly
            self.setUnifiedTitleAndToolBarOnMac(False)
        except Exception:
            pass
        # Basic state
        self.current_row = None
        self._current_position = "00:00"
        self._current_duration = "00:00"
        self._current_position_ms = 0
        self._current_duration_ms = 0

        # Master volume (multiplier for all tracks, default 100%)
        self._master_volume = 1.0  # 0.0 to 1.0

        # Play state tracking for radio button indicators
        from .play_state_delegate import PlayStateDelegate
        self._play_state = PlayStateDelegate.PLAY_STATE_STOPPED

        # Background analysis management
        self._analysis_worker = None
        self._pending_analysis_path = None
        self._user_adjusted_volume = False  # Track manual volume changes

        # EQ debounce timer to prevent rapid updates
        self._eq_update_timer = QTimer()
        self._eq_update_timer.setSingleShot(True)
        self._eq_update_timer.timeout.connect(self._apply_pending_eq_update)
        self._pending_eq_values = None

        # Library indexer
        try:
            self.indexer = LibraryIndexer()
        except Exception as e:
            print(f"[SidecarEQ] Indexer failed: {e}")
            self.indexer = None

        # Music metadata fetcher for artist info
        try:
            self.metadata_fetcher = MusicMetadataFetcher()
        except Exception as e:
            print(f"[SidecarEQ] Metadata fetcher failed: {e}")
            self.metadata_fetcher = None

        # Artist info panel will be created in UI setup - no search bar needed

        # Model / table
        try:
            self.model = QueueModel()
            self.active_playlist_path = None  # Track currently loaded playlist for auto-save
            self.table = QueueTableView()
            self.table.setModel(self.model)
            self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.table.setSelectionMode(QAbstractItemView.SingleSelection)  # Allow single row selection for drag-drop
            self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)  # Enable editing
            self.table.clicked.connect(self._on_table_play)
            self.table.delete_key_pressed.connect(self.on_remove_selected)

            # Install custom delegate for play state indicator (now column 1)
            from .play_state_delegate import PlayStateDelegate
            self.play_state_delegate = PlayStateDelegate(self.table)
            self.table.setItemDelegateForColumn(1, self.play_state_delegate)  # Status column

            # Install star rating delegate for Rating column (column 8)
            self.star_rating_delegate = StarRatingDelegate(self.table)
            self.table.setItemDelegateForColumn(8, self.star_rating_delegate)  # Rating column

            # Configure columns with custom header for column management
            custom_header = CustomTableHeader(Qt.Horizontal, self.table)
            self.table.setHorizontalHeader(custom_header)

            header = self.table.horizontalHeader()
            header.setStretchLastSection(False)  # We'll stretch the Title column instead
            # Tooltips for icon-only columns
            header.setSectionResizeMode(0, QHeaderView.Fixed)  # Lookup (globe) - fixed width
            header.setSectionResizeMode(1, QHeaderView.Fixed)  # Status (play indicator) - fixed width
            if self.model is not None:
                self.model.setHeaderData(0, Qt.Horizontal, "Lookup", Qt.ToolTipRole)
                self.model.setHeaderData(1, Qt.Horizontal, "Status", Qt.ToolTipRole)

            # Column resize modes (15 columns total now: Lookup + Status + 13 data columns)
            # Make Title column (2) stretch to consume remaining width
            header.setSectionResizeMode(2, QHeaderView.Stretch)
            for col in range(3, 15):  # All other columns user-resizable
                header.setSectionResizeMode(col, QHeaderView.Interactive)

            # Set initial column widths (optimized for new metadata fields)
            self.table.setColumnWidth(0, 40)   # 🌐 Lookup (globe icon)
            self.table.setColumnWidth(1, 30)   # ● Status (play state indicator)
            self.table.setColumnWidth(2, 250)  # Title
            self.table.setColumnWidth(3, 150)  # Artist
            self.table.setColumnWidth(4, 150)  # Album
            self.table.setColumnWidth(5, 50)   # Year
            self.table.setColumnWidth(6, 120)  # Label
            self.table.setColumnWidth(7, 120)  # Producer
            self.table.setColumnWidth(8, 80)   # Rating (★★★★★)
            self.table.setColumnWidth(9, 70)   # Bitrate
            self.table.setColumnWidth(10, 60)  # Format
            self.table.setColumnWidth(11, 80)  # Sample Rate
            self.table.setColumnWidth(12, 70)  # Bit Depth
            self.table.setColumnWidth(13, 60)  # Duration
            self.table.setColumnWidth(14, 80)  # Play Count

            # Hide less essential columns by default (user can show via right-click menu)
            # Keep: Lookup, Status, Title, Artist, Album, Year, Rating
            # Hide: Label, Producer, Bitrate, Format, Sample Rate, Bit Depth, Duration, Play Count
            self.table.setColumnHidden(6, True)   # Label
            self.table.setColumnHidden(7, True)   # Producer
            self.table.setColumnHidden(9, True)   # Bitrate
            self.table.setColumnHidden(10, True)  # Format
            self.table.setColumnHidden(11, True)  # Sample Rate
            self.table.setColumnHidden(12, True)  # Bit Depth
            self.table.setColumnHidden(13, True)  # Duration
            self.table.setColumnHidden(14, True)  # Play Count

            # Enable word wrap in headers for better text fit
            header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            # Hide vertical header (row numbers) for cleaner look
            self.table.verticalHeader().setVisible(False)
            # Improve at-a-glance readability with alternating rows
            self.table.setAlternatingRowColors(True)

            # Alternating row colors for better readability
            self.table.setAlternatingRowColors(True)

            # Enable sorting by clicking column headers
            self.table.setSortingEnabled(True)

            # Enable drag & drop for reordering rows
            self.table.setDragEnabled(True)
            self.table.setAcceptDrops(True)
            self.table.setDropIndicatorShown(True)
            self.table.setDragDropMode(QAbstractItemView.InternalMove)
            self.table.setDefaultDropAction(Qt.MoveAction)
            self.table.setDragDropOverwriteMode(False)  # Insert instead of overwrite
            # CRITICAL: Show line indicator between rows, not rectangle on row
            # The drop indicator shows as a LINE between items, not a rectangle highlighting the row
            # This is controlled by setDropIndicatorShown(True) and setDragDropOverwriteMode(False)

            # Create container with restructured layout:
            # - Queue table (top, collapsible panel, resizable)
            # - Waveform/EQ (middle, collapsible panel, resizable)
            # - Search bar (bottom, collapsible panel)
            # Simple vertical layout with collapsible panels
            from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QSizePolicy

            # Keep queue panel height synced with content changes
            try:
                self._sync_queue_panel_height()
                if self.model:
                    for signal in (
                        self.model.modelReset,
                        self.model.layoutChanged,
                        self.model.rowsInserted,
                        self.model.rowsRemoved,
                        self.model.dataChanged,
                    ):
                        signal.connect(self._sync_queue_panel_height)
                        signal.connect(self._auto_save_active_playlist)  # Auto-save playlist on changes
            except Exception:
                pass
            central_widget = QWidget()
            central_layout = QVBoxLayout()
            central_layout.setContentsMargins(0, 0, 0, 0)
            # Add breathing room between collapsible panels to avoid cramped headers
            central_layout.setSpacing(12)

            # Panel 1: Song Queue & Metadata (collapsible, accordion style)
            self.queue_panel = CollapsiblePanel("Song Queue & Metadata")
            self.queue_panel.set_content(self.table)
            self.queue_panel.lock_content_height(True)
            self.table.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
            self.table.setMinimumHeight(100)
            central_layout.addWidget(self.queue_panel, stretch=0)  # Dynamic stretch applied later

            # Panel 2: EQ & Waveform (collapsible, accordion style) - will be populated in _build_side_panel
            self.eq_panel = CollapsiblePanel("EQ & Waveform")
            central_layout.addWidget(self.eq_panel, stretch=0)  # Dynamic stretch applied later

            # Panel 3: Now Playing Artist Info (collapsible, accordion style)
            self.search_panel = CollapsiblePanel("Now Playing")

            # Create the artist info display
            self.artist_info_widget = self._create_artist_info_display()
            self.search_panel.set_content(self.artist_info_widget)
            self.search_panel.lock_content_height(False)  # Allow expansion for rich content

            central_layout.addWidget(self.search_panel, stretch=0)  # Dynamic stretch applied later

            # Panel 4: Playlists (collapsible, accordion style)
            self.playlist_panel = CollapsiblePanel("Playlists")
            playlist_widget = self._create_playlist_browser()
            self.playlist_panel.set_content(playlist_widget)
            self.playlist_panel.lock_content_height(False)
            central_layout.addWidget(self.playlist_panel, stretch=0)

            # Store central layout for dynamic stretch updates
            self._central_layout = central_layout

            # Load saved collapse states
            self._load_panel_states()

            central_widget.setLayout(central_layout)
            self.setCentralWidget(central_widget)
            # Keep a handle to the classic central widget so we can swap to Rack Mode
            self._classic_central = central_widget
            self._rack_enabled = False
            self._rack_container = None

            # Load saved queue state
            self._load_queue_state()
            self._sync_queue_panel_height()

            # Auto-refresh metadata for existing queue items (background operation)
            # DISABLED: causing UI responsiveness issues
            # if self.model and hasattr(self.model, '_rows') and len(self.model._rows) > 0:
            #     QTimer.singleShot(500, self._auto_refresh_metadata)
        except Exception as e:
            print(f"[SidecarEQ] Model/table setup failed: {e}")
            import traceback
            traceback.print_exc()
            self.model = None
            self.table = None

        # Player wrapper
        try:
            self.player = Player()
        except Exception:
            self.player = None

        # Build UI sections (safe-call)
        try:
            self._build_menubar()
        except Exception as e:
            print(f"[SidecarEQ] Menubar failed: {e}")
        try:
            self._build_toolbar()
        except Exception as e:
            print(f"[SidecarEQ] Toolbar failed: {e}")
            import traceback
            traceback.print_exc()
        try:
            self._build_side_panel()
        except Exception as e:
            print(f"[SidecarEQ] Side panel failed: {e}")
        try:
            self._build_status_bar()
        except Exception:
            pass

        # Build (but don't show) Rack UI shell so it's ready when toggled
        try:
            self._build_rack_ui()
        except Exception as e:
            print(f"[SidecarEQ] Rack UI build failed: {e}")

        # Wire signals last (player and widgets should exist)
        try:
            self._wire_signals()
        except Exception:
            pass

        self.setWindowTitle('Sidecar EQ')

        # Fixed width, dynamic height calculated by _resize_to_fit_visible_panels
        self.setFixedWidth(1000)

        # Disable window resize (prevents grip/border dragging)
        self.setWindowFlag(Qt.WindowType.MSWindowsFixedSizeDialogHint, True)

        # Apply clean dark theme with modern fonts and compact styling
        if USE_MODERN_UI:
            # Get system font name for the table
            system_font = SystemFonts.get_system_font(size=12).family()

            self.setStyleSheet(f"""
                QMainWindow {{
                    background: {ModernColors.BACKGROUND_PRIMARY};
                }}
                QTableView {{
                    background: {ModernColors.BACKGROUND_SECONDARY};
                    color: {ModernColors.TEXT_PRIMARY};
                    gridline-color: {ModernColors.SEPARATOR};
                    border: 1px solid {ModernColors.SEPARATOR};
                    selection-background-color: {ModernColors.ACCENT};
                    selection-color: white;
                    font-family: '{system_font}';
                    font-size: 11px;
                    /* Make alternating rows slightly more contrasted for better visibility */
                    alternate-background-color: {ModernColors.BACKGROUND_TERTIARY};
                }}
                QTableView::item {{
                    padding: 2px 4px;
                    border: none;
                }}
                QTableView QHeaderView::section {{
                    background: {ModernColors.BACKGROUND_TERTIARY};
                    color: {ModernColors.TEXT_SECONDARY};
                    font-family: '{system_font}';
                    font-size: 10px;
                    font-weight: 600;
                    letter-spacing: 0.3px;
                    text-transform: uppercase;
                    border: none;
                    border-right: 1px solid {ModernColors.SEPARATOR};
                    border-bottom: 1px solid {ModernColors.SEPARATOR};
                    padding: 6px 8px;
                }}
                QToolBar {{
                    background: {ModernColors.BACKGROUND_SECONDARY};
                    border-bottom: 1px solid {ModernColors.SEPARATOR};
                    spacing: 6px;
                    padding: 4px;
                }}
                QStatusBar {{
                    background: {ModernColors.BACKGROUND_SECONDARY};
                    color: {ModernColors.TEXT_SECONDARY};
                    border-top: 1px solid {ModernColors.SEPARATOR};
                    font-family: '{system_font}';
                    font-size: 11px;
                }}
                QDockWidget {{
                    background: {ModernColors.BACKGROUND_PRIMARY};
                    border-left: 1px solid {ModernColors.SEPARATOR};
                }}
                QLabel {{
                    color: {ModernColors.TEXT_SECONDARY};
                    background: transparent;
                    border: none;
                }}
            """)
        else:
            # Fallback styling
            self.setStyleSheet("""
                QMainWindow {
                    background: #1e1e1e;
                }
                QTableView {
                    background: #252525;
                    color: #e0e0e0;
                    gridline-color: #3a3a3a;
                    border: 1px solid #3a3a3a;
                    selection-background-color: #0d4f8f;
                    selection-color: white;
                    font-size: 11px;
                    /* Subtle but visible zebra stripes */
                    alternate-background-color: #2e2e2e;
                }
                QTableView QHeaderView::section {
                    background: #2d2d2d;
                    color: #c0c0c0;
                    font-weight: bold;
                    font-size: 10px;
                    border: 1px solid #3a3a3a;
                    padding: 5px;
                }
                QToolBar {
                    background: #2a2a2a;
                    border-bottom: 1px solid #404040;
                    spacing: 6px;
                    padding: 4px;
                }
                QStatusBar {
                    background: #2a2a2a;
                    color: #c0c0c0;
                    border-top: 1px solid #404040;
                }
                QDockWidget {
                    background: #1e1e1e;
                    border-left: 1px solid #3a3a3a;
                }
                QLabel {
                    color: #c0c0c0;
                    background: transparent;
                    border: none;
                }
            """)

        # Apply user interface preferences (alternating stripes, empty-state stripes, layout default)
        QTimer.singleShot(0, self._apply_ui_prefs_from_store)

    def showEvent(self, event):
        """Called when the window is shown. Auto-select first row if queue has items."""
        super().showEvent(event)

        # Only do this once on first show
        if not hasattr(self, '_initial_selection_done'):
            self._initial_selection_done = True

            # Use a timer to ensure everything is fully initialized
            QTimer.singleShot(100, self._do_initial_selection)

            # Check for missing volumes after initialization
            QTimer.singleShot(1000, self._check_for_missing_volumes)

    def _do_initial_selection(self):
        """Select and display info for the first track in the queue (without playing).
        If queue is empty, load a default track (Children of the Grave by Black Sabbath)."""
        try:
            if self.model.rowCount() > 0:
                # Queue has tracks - select the first one and populate artist info
                first_index = self.model.index(0, 2)  # Column 2 is Title
                self.table.setCurrentIndex(first_index)
                self.table.selectRow(0)

                if len(self.model._rows) > 0:
                    first_path = self.model._rows[0].get('path')
                    if first_path:
                        self._update_artist_info_display(first_path)
            else:
                # Queue is empty - load default track (MLK "I Have a Dream" speech)
                print("[App] Queue is empty, loading default track: MLK 'I Have a Dream' speech")

                # Use bundled MLK speech file
                from pathlib import Path
                default_path = Path(__file__).parent / "MLKDream_64kb.mp3"

                if default_path.exists():
                    # Add the track to queue
                    count = self.model.add_paths([str(default_path)])
                    if count > 0:
                        print(f"[App] Added default track to queue: {default_path}")

                        # Auto-add to library
                        self._auto_add_to_library([str(default_path)])

                        # Select it
                        first_index = self.model.index(0, 2)
                        self.table.setCurrentIndex(first_index)
                        self.table.selectRow(0)

                        self._update_artist_info_display(str(default_path))
                else:
                    print(f"[App] Default track not found at: {default_path}")
                    if hasattr(self, 'artist_info_widget'):
                        self.artist_info_widget.setVisible(False)

        except Exception as e:
            print(f"[App] Failed to do initial selection: {e}")

    def _on_table_play(self, index):
        """
        Handle clicks on the queue table.
        - Column 0 (globe icon): Metadata lookup
        - Column 1 (radio button): Play/pause/resume control
        - Other columns: Select row (no action)
        """
        try:
            # Column 0: Metadata lookup (globe icon)
            if index.column() == 0:
                self._on_metadata_lookup(index.row())
                return

            # Column 1: Play state indicator
            if index.column() != 1:
                return

            clicked_row = index.row()
            from .play_state_delegate import PlayStateDelegate

            # Case 1: Clicking the currently playing row - PAUSE it
            if clicked_row == self.current_row and self._play_state == PlayStateDelegate.PLAY_STATE_PLAYING:
                self.player.pause()
                self.statusBar().showMessage("Paused")
                self.play_btn.setActive(False)
                self.play_state_delegate.set_play_state(clicked_row, PlayStateDelegate.PLAY_STATE_PAUSED)
                self._play_state = PlayStateDelegate.PLAY_STATE_PAUSED
                # Stop LED meters when paused
                self._update_led_meters_playback(False)

            # Case 2: Clicking a paused row - RESUME playback
            elif clicked_row == self.current_row and self._play_state == PlayStateDelegate.PLAY_STATE_PAUSED:
                self.player._player.play()
                self.statusBar().showMessage("Playing (resumed)")
                self.play_btn.setActive(True)
                self.play_state_delegate.set_play_state(clicked_row, PlayStateDelegate.PLAY_STATE_PLAYING)
                self._play_state = PlayStateDelegate.PLAY_STATE_PLAYING
                # Start LED meters when resumed
                self._update_led_meters_playback(True)

            # Case 3: Clicking a different row - PLAY that track from beginning
            else:
                self._play_row(clicked_row)
                self._play_state = PlayStateDelegate.PLAY_STATE_PLAYING

        except Exception as e:
            print(f"[App] Error in _on_table_play: {e}")
            pass
    def _build_status_bar(self):
        """Status bar with repeat button."""
        sb = self.statusBar()
        sb.setSizeGripEnabled(False)  # Disable resize grip (window is fixed size)

        # Repeat button (toggle)
        self._repeat_enabled = False
        self._repeat_btn = QPushButton("🔁 Repeat: Off")
        self._repeat_btn.setCheckable(True)
        self._repeat_btn.setFixedHeight(20)
        self._repeat_btn.clicked.connect(self._toggle_repeat)
        self._repeat_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #808080;
                border: 1px solid #404040;
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 10px;
            }
            QPushButton:hover {
                border: 1px solid #4d88ff;
            }
            QPushButton:checked {
                background: #0d4f8f;
                color: white;
                border: 1px solid #4da6ff;
            }
        """)
        sb.addPermanentWidget(self._repeat_btn)

        sb.showMessage("Ready")


    def _wire_signals(self):
        # play-end → next track (or repeat if enabled)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)
        # wire duration/position to waveform and labels
        def _on_duration(dur):
            try:
                self.waveform.setDuration(int(dur))
            except Exception:
                pass
            self._on_duration(dur)

        def _on_position(pos):
            try:
                self.waveform.setPosition(int(pos))
            except Exception:
                pass
            self._on_position(pos)

        self.player.durationChanged.connect(_on_duration)
        self.player.positionChanged.connect(_on_position)

        # User seeking via waveform click → set player position AND start playback if stopped
        self.waveform.seekRequested.connect(self._on_waveform_seek)

        # Wire collapsible panel signals to save state AND resize window (accordion style)
        if hasattr(self, 'queue_panel'):
            self.queue_panel.collapsed.connect(lambda _: self._on_panel_toggled())
        if hasattr(self, 'eq_panel'):
            self.eq_panel.collapsed.connect(lambda _: self._on_panel_toggled())
        if hasattr(self, 'search_panel'):
            self.search_panel.collapsed.connect(lambda _: self._on_panel_toggled())
        if hasattr(self, 'playlist_panel'):
            self.playlist_panel.collapsed.connect(lambda _: self._on_panel_toggled())

    def _on_waveform_seek(self, ms: int):
        """Handle seeking via waveform click. Start playback if stopped.

        Args:
            ms: Seek position in milliseconds
        """
        from PySide6.QtMultimedia import QMediaPlayer

        # Check if we have any tracks in queue
        if self.model.rowCount() == 0:
            self.statusBar().showMessage("Queue is empty - add tracks first", 3000)
            return

        # If not playing, start playback FIRST, then seek
        if self.player._player.playbackState() != QMediaPlayer.PlayingState:
            # If no track loaded, load first selected/current row
            if self.current_row is None:
                sel = self.table.selectionModel().selectedRows()
                if sel:
                    self._play_row(sel[0].row())
                elif self.model.rowCount() > 0:
                    self._play_row(0)
                else:
                    return
                # Seek after loading new track
                QTimer.singleShot(100, lambda: self.player.set_position(ms))
                return
            else:
                # Resume or start playing current track
                self.player._player.play()
                self.play_btn.setActive(True)
                self.statusBar().showMessage("Playing")
                from .play_state_delegate import PlayStateDelegate
                self.play_state_delegate.set_play_state(self.current_row, PlayStateDelegate.PLAY_STATE_PLAYING)
                self._play_state = PlayStateDelegate.PLAY_STATE_PLAYING
                # Start LED meters
                self._update_led_meters_playback(True)
                # Seek after starting playback (give player time to start)
                QTimer.singleShot(100, lambda: self.player.set_position(ms))
                return

        # Already playing - seek immediately
        self.player.set_position(ms)

    def _build_toolbar(self):
        print("[SidecarEQ] Building toolbar…")
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(QSize(32, 32))
        # Give the toolbar a subtle background so it's clearly visible
        tb.setStyleSheet("QToolBar{background:#202020; border-bottom:1px solid #333; padding:4px;}")
        self.addToolBar(tb)
        self.toolbar = tb  # Store reference for resize calculations

        # Play/Pause button
        self.play_btn = IconButton(
            "icons/play.svg",
            "icons/play_hover.svg",
            "icons/play_active.svg",
            tooltip="Play / Pause (Space)"
        )
        self.play_btn.clicked.connect(self.on_play)
        self.play_btn.setShortcut(QKeySequence(Qt.Key_Space))
        tb.addWidget(self.play_btn)

        # Add Songs button (download icon)
        tb.addSeparator()
        add_btn = IconButton(
            "icons/download.svg",
            "icons/download_hover.svg",
            "icons/download_pressed.svg",
            tooltip="Add Songs"
        )
        add_btn.clicked.connect(self.on_add_based_on_source)
        tb.addWidget(add_btn)

        # Trash button
        tb.addSeparator()
        trash_btn = IconButton(
            "icons/trash.svg",
            "icons/trash_hover.svg",
            "icons/trash_pressed.svg",
            tooltip="Remove Selected"
        )
        trash_btn.clicked.connect(self.on_remove_selected)
        tb.addWidget(trash_btn)

        # Music Directory Selector - Shows current directory, allows selection from recent or browse
        tb.addSeparator()
        from PySide6.QtWidgets import QComboBox
        self.music_dir_combo = QComboBox()
        self.music_dir_combo.setEditable(False)
        self.music_dir_combo.setMinimumWidth(200)
        self.music_dir_combo.setMaximumWidth(400)
        self.music_dir_combo.setStyleSheet("""
            QComboBox {
                color: #b0b0b0;
                background: #1a1a1a;
                border: 1px solid #2a2a2a;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QComboBox:hover {
                border: 1px solid #3a3a3a;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #808080;
                width: 0;
                height: 0;
                margin-right: 6px;
            }
        """)
        self.music_dir_combo.activated.connect(self._on_music_dir_selected)
        tb.addWidget(self.music_dir_combo)

        # Load recent music directories
        self._load_recent_music_dirs()

        # NOW PLAYING / METADATA DISPLAY - Extended to fill available space
        # LCD-style scrolling display inspired by retro alarm clocks and digital displays
        tb.addSeparator()
        self.metadata_label = ScrollingLabel("♪ No track loaded")

        # Style the scrolling label with green LCD-style colors
        self.metadata_label.setStyleSheet("""
            ScrollingLabel {
                color: #00ff00;
                font-family: 'Courier New', 'Courier', 'Lucida Console', monospace;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 16px;
                background: #1e1e1e; /* match main background */
                border: 1px solid #2e2e2e; /* subtle divider instead of heavy border */
                border-radius: 4px;
            }
        """)

        # Make it expand to fill available space
        from PySide6.QtWidgets import QSizePolicy as _SP
        self.metadata_label.setSizePolicy(_SP.Expanding, _SP.Preferred)
        self.metadata_label.setMinimumWidth(200)

        # Configure scroll behavior (slower scroll, longer pause)
        self.metadata_label.setScrollSpeed(1)  # 1 pixel per frame (slow, smooth)
        self.metadata_label.setPauseDuration(2000)  # 2 second pause at start/end

        tb.addWidget(self.metadata_label)

        # Layout preset dropdown and Save button in toolbar
        tb.addSeparator()

        # Layout preset dropdown (Overleaf-style)
        from PySide6.QtWidgets import QComboBox
        self._layout_preset_combo = QComboBox()
        self._layout_preset_combo.addItems([
            "Queue + EQ",
            "Queue + Playlists",
            "EQ Only",
            "Artist Info"
        ])
        self._layout_preset_combo.setCurrentIndex(0)  # Default to Queue + EQ
        self._layout_preset_combo.setToolTip("Select layout preset")
        self._layout_preset_combo.currentIndexChanged.connect(self._on_layout_preset_changed)

        if USE_MODERN_UI:
            system_font = SystemFonts.get_system_font(size=10, weight="Medium").family()
            self._layout_preset_combo.setStyleSheet(f"""
                QComboBox {{
                    background: {ModernColors.BACKGROUND_SECONDARY};
                    color: {ModernColors.TEXT_PRIMARY};
                    border: 1px solid {ModernColors.SEPARATOR};
                    border-radius: 3px;
                    padding: 4px 8px;
                    font-family: '{system_font}';
                    font-size: 10px;
                    min-width: 220px;
                }}
                QComboBox:hover {{
                    border: 1px solid {ModernColors.ACCENT};
                }}
                QComboBox::drop-down {{
                    border: none;
                }}
                QComboBox::down-arrow {{
                    image: none;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 5px solid {ModernColors.TEXT_TERTIARY};
                    margin-right: 8px;
                }}
            """)
        else:
            self._layout_preset_combo.setStyleSheet("""
                QComboBox {
                    background: #2a2a2a;
                    color: #e0e0e0;
                    border: 1px solid #404040;
                    border-radius: 3px;
                    padding: 4px 8px;
                    font-size: 10px;
                    min-width: 220px;
                }
                QComboBox:hover {
                    border: 1px solid #4d88ff;
                }
                QComboBox::drop-down {
                    border: none;
                }
                QComboBox::down-arrow {
                    image: none;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 5px solid #888888;
                    margin-right: 8px;
                }
            """)

        tb.addWidget(self._layout_preset_combo)

    print("[SidecarEQ] Toolbar ready")



    def _create_playlist_browser(self):
        """Create the playlist browser widget."""
        from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout, QListWidgetItem, QMessageBox
        from PySide6.QtCore import Qt
        
        container = QWidget()
        container.setStyleSheet("QWidget { background: #1e1e1e; }")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Playlist list
        self.playlist_list = QListWidget()
        self.playlist_list.setStyleSheet("""
            QListWidget {
                background: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 5px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 3px;
                margin: 2px 0;
            }
            QListWidget::item:hover {
                background: #3a3a3a;
            }
            QListWidget::item:selected {
                background: #4a9eff;
                color: white;
            }
        """)
        self.playlist_list.itemDoubleClicked.connect(self._on_playlist_double_click)
        layout.addWidget(self.playlist_list)
        
        # Button row
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        # Save current queue as playlist button
        save_btn = QPushButton("💾 Save Current Queue")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #4a9eff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background: #5aa9ff; }
            QPushButton:pressed { background: #3a8eef; }
        """)
        save_btn.clicked.connect(self._save_current_queue_as_playlist)
        button_layout.addWidget(save_btn)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 12px;
            }
            QPushButton:hover { background: #3a3a3a; }
            QPushButton:pressed { background: #1a1a1a; }
        """)
        refresh_btn.clicked.connect(self._refresh_playlist_list)
        button_layout.addWidget(refresh_btn)
        
        # Delete button
        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.setStyleSheet("""
            QPushButton {
                background: #ff4444;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 12px;
            }
            QPushButton:hover { background: #ff5555; }
            QPushButton:pressed { background: #dd3333; }
        """)
        delete_btn.clicked.connect(self._delete_selected_playlist)
        button_layout.addWidget(delete_btn)
        
        layout.addLayout(button_layout)
        container.setLayout(layout)
        
        # Initial load of playlists
        self._refresh_playlist_list()
        
        return container

    def _get_playlists_dir(self):
        """Get the playlists directory, creating it if needed."""
        playlists_dir = Path.home() / '.sidecar_eq' / 'playlists'
        playlists_dir.mkdir(parents=True, exist_ok=True)
        return playlists_dir

    def _refresh_playlist_list(self):
        """Refresh the playlist list from disk."""
        try:
            self.playlist_list.clear()
            playlists_dir = self._get_playlists_dir()
            
            # Find all .json playlist files
            playlist_files = sorted(playlists_dir.glob('*.json'))
            
            if not playlist_files:
                item = QListWidgetItem("📁 No playlists yet")
                item.setFlags(Qt.ItemFlag.NoItemFlags)  # Make it non-selectable
                self.playlist_list.addItem(item)
                return
            
            for playlist_file in playlist_files:
                # Load playlist to get track count
                try:
                    data = json.loads(playlist_file.read_text())
                    paths = data.get('paths', [])
                    track_count = len(paths)
                    
                    # Format: playlist name (X tracks)
                    name = playlist_file.stem
                    display_text = f"🎵 {name} ({track_count} track{'s' if track_count != 1 else ''})"
                    
                    item = QListWidgetItem(display_text)
                    item.setData(Qt.ItemDataRole.UserRole, str(playlist_file))  # Store full path
                    self.playlist_list.addItem(item)
                except Exception as e:
                    print(f"[Playlist] Failed to read {playlist_file.name}: {e}")
                    
            print(f"[Playlist] Loaded {len(playlist_files)} playlist(s)")
            
        except Exception as e:
            print(f"[Playlist] Failed to refresh playlist list: {e}")

    def _on_playlist_double_click(self, item):
        """Load playlist when double-clicked."""
        from PySide6.QtWidgets import QMessageBox
        
        playlist_path = item.data(Qt.ItemDataRole.UserRole)
        if not playlist_path:
            return
        
        try:
            # Load the playlist (replaces current queue)
            paths = playlist.load_json(playlist_path)
            if paths:
                # Clear queue first, then add new tracks
                self.model.clear()
                count = self.model.add_paths(paths)
                if self.current_row is None and count > 0:
                    self.table.selectRow(0)
                
                # Set as active playlist for auto-save
                self.active_playlist_path = playlist_path
                
                playlist_name = Path(playlist_path).stem
                self.statusBar().showMessage(f"✅ Loaded playlist '{playlist_name}' ({count} tracks)", 3000)
                print(f"[Playlist] Loaded '{playlist_name}' with {count} tracks - now active for editing")
            else:
                QMessageBox.information(self, "Load Playlist", "No tracks found in playlist.")
        except Exception as e:
            QMessageBox.warning(self, "Load Playlist", f"Failed to load playlist: {e}")

    def _auto_save_active_playlist(self):
        """Auto-save changes to the currently active playlist (if any)."""
        if not self.active_playlist_path:
            return  # No active playlist to save
        
        try:
            # Save current queue to active playlist
            paths = self.model.paths()
            if paths:
                playlist.save_json(paths, str(self.active_playlist_path))
                playlist_name = Path(self.active_playlist_path).stem
                print(f"[Playlist] Auto-saved changes to '{playlist_name}' ({len(paths)} tracks)")
            else:
                # Queue is empty - don't save, just note it
                print(f"[Playlist] Queue empty, skipping auto-save")
        except Exception as e:
            print(f"[Playlist] Auto-save failed: {e}")

    def _save_current_queue_as_playlist(self):
        """Save the current queue as a new playlist."""
        from PySide6.QtWidgets import QInputDialog, QMessageBox
        
        # Get playlist name from user
        name, ok = QInputDialog.getText(
            self,
            "Save Playlist",
            "Enter playlist name:",
            text="My Playlist"
        )
        
        if not ok or not name.strip():
            return
        
        try:
            # Sanitize filename
            safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
            if not safe_name:
                QMessageBox.warning(self, "Save Playlist", "Invalid playlist name.")
                return
            
            # Create playlist file
            playlists_dir = self._get_playlists_dir()
            playlist_path = playlists_dir / f"{safe_name}.json"
            
            # Save current queue
            paths = self.model.paths()
            if not paths:
                QMessageBox.information(self, "Save Playlist", "Queue is empty. Nothing to save.")
                return
            
            playlist.save_json(paths, str(playlist_path))
            
            self.statusBar().showMessage(f"✅ Saved playlist '{safe_name}' ({len(paths)} tracks)", 3000)
            print(f"[Playlist] Saved '{safe_name}' with {len(paths)} tracks to {playlist_path}")
            
            # Refresh the list
            self._refresh_playlist_list()
            
        except Exception as e:
            QMessageBox.warning(self, "Save Playlist", f"Failed to save playlist: {e}")

    def _delete_selected_playlist(self):
        """Delete the selected playlist."""
        from PySide6.QtWidgets import QMessageBox
        
        current_item = self.playlist_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "Delete Playlist", "Please select a playlist to delete.")
            return
        
        playlist_path = current_item.data(Qt.ItemDataRole.UserRole)
        if not playlist_path:
            return
        
        # Confirm deletion
        playlist_name = Path(playlist_path).stem
        reply = QMessageBox.question(
            self,
            "Delete Playlist",
            f"Are you sure you want to delete '{playlist_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                Path(playlist_path).unlink()
                self.statusBar().showMessage(f"🗑️ Deleted playlist '{playlist_name}'", 3000)
                print(f"[Playlist] Deleted '{playlist_name}'")
                self._refresh_playlist_list()
            except Exception as e:
                QMessageBox.warning(self, "Delete Playlist", f"Failed to delete playlist: {e}")

    def _create_artist_info_display(self):
        """Create the Now Playing artist info display widget with rich metadata."""
        try:
            from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget, QHBoxLayout, QPushButton
            from PySide6.QtCore import Qt, QSize
            from PySide6.QtGui import QPixmap

            # Main container widget (no scroll - window will resize to fit)
            from PySide6.QtWidgets import QSizePolicy
            container = QWidget(self)
            container.setStyleSheet("""
                QWidget {
                    background: #1e1e1e;
                }
            """)
            container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

            layout = QVBoxLayout()
            layout.setSpacing(15)
            layout.setContentsMargins(20, 20, 20, 20)

            # --- ALBUM TRACKLIST (TOP, 2 COLUMNS) ---
            header_row = QHBoxLayout()
            header_row.setContentsMargins(0,0,0,0)
            header_row.setSpacing(8)

            tracklist_header = QLabel("Album Tracks")
            tracklist_header.setStyleSheet("""
                QLabel {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    font-size: 15px;
                    font-weight: bold;
                    color: #ffffff;
                    padding-bottom: 8px;
                    background: transparent;
                    border: none;
                }
            """)
            header_row.addWidget(tracklist_header)
            header_row.addStretch()

            # Button: Add Artist to Library
            self.add_artist_btn = QPushButton("Add Artist to Library")
            self.add_artist_btn.setFixedHeight(24)
            self.add_artist_btn.setStyleSheet("""
                QPushButton {
                    background: #2a2a2a;
                    color: #b0d5ff;
                    border: 1px solid #3a3a3a;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                }
                QPushButton:hover { background: #333; border-color: #4a4a4a; }
                QPushButton:disabled { color: #777; }
            """)
            self.add_artist_btn.clicked.connect(self._on_add_artist_to_library)
            header_row.addWidget(self.add_artist_btn)

            layout.addLayout(header_row)

            # Tracklist container with 2-column grid
            self.tracklist_container = QWidget()
            from PySide6.QtWidgets import QGridLayout
            self.tracklist_layout = QGridLayout()
            self.tracklist_layout.setContentsMargins(0, 0, 0, 0)
            self.tracklist_layout.setSpacing(3)
            self.tracklist_layout.setHorizontalSpacing(15)
            self.tracklist_container.setLayout(self.tracklist_layout)
            self.tracklist_container.setVisible(False)  # Hidden until loaded
            layout.addWidget(self.tracklist_container)

            # --- DIVIDER ---
            divider = QFrame()
            divider.setFrameShape(QFrame.HLine)
            divider.setStyleSheet("background: #444; max-height: 1px; margin-top: 5px; margin-bottom: 10px;")
            layout.addWidget(divider)

            # --- MAIN CONTENT: Album art + Bio side-by-side ---
            content_layout = QHBoxLayout()
            content_layout.setSpacing(20)

            # Left side: Album artwork (fixed size, smaller)
            self.album_art_label = QLabel()
            self.album_art_label.setFixedSize(QSize(200, 200))
            self.album_art_label.setScaledContents(True)
            self.album_art_label.setStyleSheet("""
                QLabel {
                    background: #2a2a2a;
                    border: 1px solid #444;
                    border-radius: 6px;
                }
            """)
            # Set placeholder image - use sidecar icon
            from pathlib import Path
            icon_path = Path(__file__).parent.parent / "icons" / "sidecarnote.png"
            if icon_path.exists():
                placeholder_pixmap = QPixmap(str(icon_path))
                placeholder_pixmap = placeholder_pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            else:
                placeholder_pixmap = QPixmap(200, 200)
                placeholder_pixmap.fill(Qt.transparent)
            self.album_art_label.setPixmap(placeholder_pixmap)
            content_layout.addWidget(self.album_art_label, 0, Qt.AlignTop)

            # Right side: Bio text (expanding)
            bio_container = QWidget()
            bio_container.setStyleSheet("QWidget { background: transparent; border: none; }")
            bio_layout = QVBoxLayout()
            bio_layout.setContentsMargins(0, 0, 0, 0)
            bio_layout.setSpacing(10)

            # --- FONT SIZE CONTROLS ---
            font_controls = QWidget()
            font_controls.setStyleSheet("QWidget { background: transparent; border: none; }")
            font_controls_layout = QHBoxLayout()
            font_controls_layout.setContentsMargins(0, 0, 0, 5)
            font_controls_layout.setSpacing(8)

            font_label = QLabel("Text Size:")
            font_label.setStyleSheet("color: #888; font-size: 11px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;")
            font_controls_layout.addWidget(font_label)

            # Font size state (14pt is default/medium)
            self.bio_font_size = 14

            # Small button
            small_btn = QPushButton("S")
            small_btn.setFixedSize(30, 24)
            small_btn.setFlat(True)
            small_btn.setStyleSheet("""
                QPushButton {
                    background: #2a2a2a;
                    color: #888;
                    border: 0px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #3a3a3a;
                    color: #aaa;
                }
                QPushButton:pressed {
                    background: #1a1a1a;
                }
                QPushButton:focus {
                    outline: none;
                    border: 0px;
                }
            """)
            small_btn.clicked.connect(lambda: self._set_bio_font_size(12))
            font_controls_layout.addWidget(small_btn)

            # Medium button
            medium_btn = QPushButton("M")
            medium_btn.setFixedSize(30, 24)
            medium_btn.setFlat(True)
            medium_btn.setStyleSheet("""
                QPushButton {
                    background: #4a9eff;
                    color: #fff;
                    border: 0px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #5aa9ff;
                }
                QPushButton:pressed {
                    background: #3a8eef;
                }
                QPushButton:focus {
                    outline: none;
                    border: 0px;
                }
            """)
            medium_btn.clicked.connect(lambda: self._set_bio_font_size(14))
            font_controls_layout.addWidget(medium_btn)
            self.font_size_medium_btn = medium_btn  # Save reference for highlighting

            # Large button
            large_btn = QPushButton("L")
            large_btn.setFixedSize(30, 24)
            large_btn.setFlat(True)
            large_btn.setStyleSheet("""
                QPushButton {
                    background: #2a2a2a;
                    color: #888;
                    border: 0px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #3a3a3a;
                    color: #aaa;
                }
                QPushButton:pressed {
                    background: #1a1a1a;
                }
                QPushButton:focus {
                    outline: none;
                    border: 0px;
                }
            """)
            large_btn.clicked.connect(lambda: self._set_bio_font_size(16))
            font_controls_layout.addWidget(large_btn)

            # Store button references for highlighting
            self.font_size_buttons = {
                12: small_btn,
                14: medium_btn,
                16: large_btn
            }

            font_controls_layout.addStretch()
            font_controls.setLayout(font_controls_layout)
            bio_layout.addWidget(font_controls)

            # --- ARTIST BIO (scrollable, webpage-like) ---
            self.artist_bio_label = QLabel("")
            self.artist_bio_label.setStyleSheet(f"""
                QLabel {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    font-size: {self.bio_font_size}px;
                    color: #e0e0e0;
                    line-height: 1.7;
                    padding: 0px;
                    background: transparent;
                }}
            """)
            self.artist_bio_label.setWordWrap(True)
            self.artist_bio_label.setTextFormat(Qt.RichText)
            self.artist_bio_label.setOpenExternalLinks(True)
            self.artist_bio_label.setVisible(False)  # Hidden until loaded
            self.artist_bio_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            bio_layout.addWidget(self.artist_bio_label)

            # --- RELATED ARTISTS (2 COLUMNS) ---
            from PySide6.QtWidgets import QGridLayout

            related_header = QLabel("Related Artists")
            related_header.setStyleSheet("""
                QLabel {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    font-size: 13px;
                    font-weight: bold;
                    color: #ffffff;
                    padding: 10px 0px 5px 0px;
                }
            """)
            related_header.setVisible(False)
            bio_layout.addWidget(related_header)

            # Grid for 2-column layout (up to 10 artists = 5 rows × 2 cols)
            self.related_artists_container = QWidget()
            self.related_artists_layout = QGridLayout()
            self.related_artists_layout.setContentsMargins(0, 0, 0, 0)
            self.related_artists_layout.setSpacing(4)
            self.related_artists_container.setLayout(self.related_artists_layout)
            self.related_artists_container.setVisible(False)
            bio_layout.addWidget(self.related_artists_container)

            # Store references for easy updates
            self.related_header = related_header
            self.related_artist_labels = []

            bio_container.setLayout(bio_layout)
            content_layout.addWidget(bio_container, 1)  # Stretch to fill

            layout.addLayout(content_layout)

            # Don't add stretch - let layout size naturally to content
            # layout.addStretch()

            container.setLayout(layout)
            container.setVisible(False)  # Hidden until a track plays
            
            # Store container reference for size calculations
            self._artist_info_container = container

            return container
        except Exception as e:
            print(f"ERROR in _create_artist_info_display: {e}")
            import traceback
            traceback.print_exc()
            # Return a dummy widget so the app doesn't crash
            dummy = QWidget(self)
            return dummy

    def _set_bio_font_size(self, size):
        """Change the font size for the artist bio text.

        Args:
            size: Font size in pixels (12, 14, or 16)
        """
        try:
            self.bio_font_size = size

            # Update bio label style
            self.artist_bio_label.setStyleSheet(f"""
                QLabel {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    font-size: {self.bio_font_size}px;
                    color: #e0e0e0;
                    line-height: 1.7;
                    padding: 10px;
                    background: transparent;
                }}
            """)

            # Update button highlighting
            for btn_size, btn in self.font_size_buttons.items():
                if btn_size == size:
                    # Active button
                    btn.setStyleSheet("""
                        QPushButton {
                            background: #4a9eff;
                            color: #fff;
                            border: 1px solid #4a9eff;
                            border-radius: 4px;
                            font-size: 11px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background: #5aa9ff;
                        }
                        QPushButton:pressed {
                            background: #3a8eef;
                        }
                    """)
                else:
                    # Inactive button
                    btn.setStyleSheet("""
                        QPushButton {
                            background: #2a2a2a;
                            color: #888;
                            border: 1px solid #444;
                            border-radius: 4px;
                            font-size: 11px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background: #3a3a3a;
                            color: #aaa;
                        }
                        QPushButton:pressed {
                            background: #1a1a1a;
                        }
                    """)

            print(f"[App] Bio font size changed to {size}px")

        except Exception as e:
            print(f"[App] Failed to change bio font size: {e}")

    def _update_artist_info_display(self, path):
        """Update the Now Playing artist info display with rich metadata from the currently playing track.

        Args:
            path: Path to the track file or URL
        """
        from PySide6.QtCore import QTimer
        
        if not hasattr(self, 'artist_info_widget') or not self.artist_info_widget:
            return

        try:
            # Get metadata for the track
            track_info = None
            if hasattr(self, 'model') and self.model:
                if self.current_row is not None and self.current_row < len(self.model._rows):
                    track_info = self.model._rows[self.current_row]
                if not track_info:
                    # Fallback: find by path so selection updates even before playback
                    for row in getattr(self.model, '_rows', []):
                        if row.get('path') == path:
                            track_info = row
                            break

            if not track_info:
                # Hide if no track info available
                self.artist_info_widget.setVisible(False)
                return

            # Extract metadata (no need to update labels - info is in LED display)
            artist = track_info.get('artist', 'Unknown Artist')
            album = track_info.get('album', '')

            # Remember current context for actions like Add Artist to Library
            self._current_artist_for_metadata = artist
            self._current_album_for_metadata = album

            # Fetch artist metadata in background
            if hasattr(self, 'metadata_fetcher') and self.metadata_fetcher and artist and artist != 'Unknown Artist':
                # Show loading state
                self.artist_bio_label.setText(f'<span style="color: #999; font-style: italic;">Loading artist info for {artist}...</span>')
                self._clear_related_artists()

                # Fetch in background (method handles threading internally)
                self._fetch_artist_metadata(artist, album)
            else:
                # No metadata fetcher or unknown artist - clear extra fields
                self.artist_bio_label.setText("")
                self._clear_related_artists()
                self._set_placeholder_artwork()
                self.tracklist_container.setVisible(False)

            # Show the display
            self.artist_info_widget.setVisible(True)
            
            # Trigger window resize if in Artist Info layout mode
            if hasattr(self, '_current_layout_preset') and self._current_layout_preset == "artist_info":
                QTimer.singleShot(100, self._resize_to_fit_visible_panels)

        except Exception as e:
            print(f"[App] Failed to update artist info display: {e}")
            import traceback
            traceback.print_exc()
            self.artist_info_widget.setVisible(False)

    def _fetch_artist_metadata(self, artist, album):
        """Fetch artist metadata (bio, genres, artwork) from external sources.

        This runs in a background thread to avoid blocking UI.

        Args:
            artist: Artist name
            album: Album name (optional)
        """
        # Cancel any existing metadata fetch
        if hasattr(self, '_artist_metadata_thread') and self._artist_metadata_thread is not None:
            try:
                if self._artist_metadata_thread.isRunning():
                    self._artist_metadata_thread.quit()
                    self._artist_metadata_thread.wait()
            except RuntimeError:
                # Thread already deleted, that's fine
                pass
            self._artist_metadata_thread = None

        # Create worker and thread
        self._artist_metadata_thread = QThread()
        self._artist_metadata_worker = ArtistMetadataWorker(self.metadata_fetcher, artist, album)
        self._artist_metadata_worker.moveToThread(self._artist_metadata_thread)

        # Connect signals (using QueuedConnection to ensure main thread execution)
        self._artist_metadata_worker.finished.connect(
            self._on_artist_metadata_received,
            Qt.QueuedConnection
        )
        self._artist_metadata_worker.error.connect(self._on_artist_metadata_error, Qt.QueuedConnection)
        self._artist_metadata_thread.started.connect(self._artist_metadata_worker.run)

        # Clean up thread when done
        def cleanup():
            self._artist_metadata_thread = None

        self._artist_metadata_worker.finished.connect(self._artist_metadata_thread.quit)
        self._artist_metadata_worker.error.connect(self._artist_metadata_thread.quit)
        self._artist_metadata_thread.finished.connect(self._artist_metadata_thread.deleteLater)
        self._artist_metadata_thread.finished.connect(cleanup)

        # Start the thread
        self._artist_metadata_thread.start()

    def _on_artist_metadata_received(self, result, artist, album):
        """Handle artist metadata received from background thread.

        This runs on the main thread due to Qt.QueuedConnection.
        """
        try:
            artist_info = result.get('artist_info')
            artwork_url = result.get('artwork_url')
            tracks = result.get('tracks')

            # Update bio
            if artist_info and artist_info.get('bio'):
                bio_text = artist_info['bio']
                bio_text = ' '.join(bio_text.split())

                from html import escape
                bio_html = escape(bio_text)
                print(f"[App] Bio prepared: {len(bio_text)} chars")

                self.artist_bio_label.setText(bio_html)
                self.artist_bio_label.setVisible(True)
                print(f"[App] ✅ Bio label updated")
            else:
                print(f"[App] No bio found for {artist}")
                self.artist_bio_label.setText(f'<span style="color: #999; font-style: italic;">No biography available for {artist}</span>')
                self.artist_bio_label.setVisible(True)

            # Update related artists
            if artist_info and artist_info.get('similar_artists'):
                self._populate_related_artists(artist_info['similar_artists'])
            else:
                self._clear_related_artists()

            # Update artwork
            if artwork_url:
                print(f"[App] Loading artwork: {artwork_url}")
                self._load_album_artwork(artwork_url)
            else:
                self._set_placeholder_artwork()

            # Update tracklist - schedule on main thread's event loop
            if tracks:
                # Create a proper closure and schedule it
                from PySide6.QtCore import QTimer
                def do_populate():
                    self._populate_tracklist(tracks, artist, album)
                QTimer.singleShot(0, do_populate)
            else:
                self.tracklist_container.setVisible(False)

        except Exception as e:
            print(f"[App] Failed to process artist metadata: {e}")
            import traceback
            traceback.print_exc()

    def _on_artist_metadata_error(self, error_msg):
        """Handle artist metadata fetch error."""
        self.artist_bio_label.setText(f'<p style="color: #ff6b6b;">Error loading artist info: {error_msg}</p>')
        self.artist_bio_label.setVisible(True)

    def _populate_tracklist(self, tracks, artist, album):
        """Populate the tracklist with clickable track buttons in a 2-column grid.

        Args:
            tracks: List of track dicts with 'number', 'title', 'length' keys
            artist: Artist name
            album: Album name
        """
        try:
            # Clear existing tracks
            while self.tracklist_layout.count():
                child = self.tracklist_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            # Compute availability from indexed library (if present)
            available_titles = set()
            def _norm_title(s):
                return ''.join(ch for ch in (s or '').lower() if ch.isalnum())
            def _norm_artist(s):
                s = (s or '').strip().lower()
                s = s.replace(', the', '').replace('the ', '')
                return ''.join(ch for ch in s if ch.isalnum())
            def _norm_album(s):
                return ''.join(ch for ch in (s or '').lower() if ch.isalnum())
            try:
                if getattr(self, 'indexer', None) and self.indexer.library and self.indexer.library.artists:
                    target_artist_key = _norm_artist(artist)
                    target_album_key = _norm_album(album)
                    for lib_artist in self.indexer.library.artists.values():
                        if _norm_artist(lib_artist.name) == target_artist_key:
                            # If album specified, restrict to it; else include all
                            for alb in lib_artist.albums.values():
                                if not target_album_key or _norm_album(alb.title) == target_album_key:
                                    for song in alb.songs:
                                        available_titles.add(_norm_title(song.title))
            except Exception as _e:
                pass

            # Add each track as a clickable button in 2 columns
            for idx, track in enumerate(tracks):
                track_btn = QPushButton()
                track_num = track.get('number', '?')
                track_title = track.get('title', 'Unknown')
                track_length = track.get('length')

                # Format length if available (convert ms to mm:ss)
                length_str = ""
                if track_length:
                    total_seconds = track_length // 1000
                    minutes = total_seconds // 60
                    seconds = total_seconds % 60
                    length_str = f" • {minutes}:{seconds:02d}"

                track_btn.setText(f"{track_num}. {track_title}{length_str}")
                track_btn.setStyleSheet("""
                    QPushButton {
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                        font-size: 12px;
                        color: #ccc;
                        background: transparent;
                        border: none;
                        text-align: left;
                        padding: 4px 8px;
                    }
                    QPushButton:hover {
                        background: #2a2a2a;
                        color: #4a9eff;
                        border-radius: 3px;
                    }
                    QPushButton:pressed {
                        background: #1a1a1a;
                    }
                    QPushButton:disabled {
                        color: #777;
                    }
                """)
                track_btn.setCursor(Qt.PointingHandCursor)

                # Mark disabled if not in library
                is_available = _norm_title(track_title) in available_titles if available_titles else True
                track_btn.setEnabled(is_available)
                if not is_available:
                    track_btn.setToolTip("Not in your library yet. Click 'Add Artist to Library' to import.")
                else:
                    track_btn.setToolTip("Click to add to top of queue and play")

                # Connect click handler: add to TOP of queue and PLAY immediately
                track_btn.clicked.connect(
                    lambda checked, t=track_title, a=artist, al=album: self._add_track_and_play(t, a, al)
                )

                # Calculate row and column for 2-column layout
                row = idx // 2
                col = idx % 2
                self.tracklist_layout.addWidget(track_btn, row, col)

            self.tracklist_container.setVisible(True)
            print(f"[App] ✅ Populated tracklist with {len(tracks)} tracks in 2 columns")

        except Exception as e:
            print(f"[App] Failed to populate tracklist: {e}")
            import traceback
            traceback.print_exc()

    def _clear_related_artists(self):
        """Clear the related artists display."""
        # Clear existing labels
        while self.related_artists_layout.count():
            child = self.related_artists_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.related_artist_labels.clear()
        self.related_header.setVisible(False)
        self.related_artists_container.setVisible(False)

    def _populate_related_artists(self, similar_artists):
        """Populate the related artists section with clickable artist names.

        Only shows artists that exist in the user's library.

        Args:
            similar_artists: List of artist name strings (up to 10)
        """
        try:
            self._clear_related_artists()

            if not similar_artists:
                return

            # Filter to only show artists that exist in the library
            artists_in_library = []
            if self.indexer and self.indexer.library:
                for artist_name in similar_artists:
                    # Check if this artist exists in the library (case-insensitive)
                    artist_name_lower = artist_name.lower()
                    for lib_artist_name in self.indexer.library.artists.keys():
                        if lib_artist_name.lower() == artist_name_lower:
                            artists_in_library.append(lib_artist_name)
                            break

            if not artists_in_library:
                # No related artists in library - don't show the section
                return

            # Limit to 10 artists
            artists_to_show = artists_in_library[:10]

            # Populate grid (2 columns, 5 rows max)
            for idx, artist_name in enumerate(artists_to_show):
                row = idx // 2
                col = idx % 2

                # Create clickable label
                artist_label = QLabel(f'• <a href="#" style="color: #4a9eff; text-decoration: none;">{artist_name}</a>')
                artist_label.setStyleSheet("""
                    QLabel {
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                        font-size: 12px;
                        color: #e0e0e0;
                        padding: 2px 0px;
                    }
                    QLabel a:hover {
                        color: #6bb6ff;
                        text-decoration: underline;
                    }
                """)
                artist_label.setTextFormat(Qt.RichText)
                artist_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
                artist_label.linkActivated.connect(lambda _, name=artist_name: self._on_related_artist_clicked(name))

                self.related_artists_layout.addWidget(artist_label, row, col)
                self.related_artist_labels.append(artist_label)

            # Show the section
            self.related_header.setVisible(True)
            self.related_artists_container.setVisible(True)
            print(f"[App] ✅ Related artists displayed: {len(artists_to_show)} artists")

        except Exception as e:
            print(f"[App] Failed to populate related artists: {e}")
            import traceback
            traceback.print_exc()

    def _on_related_artist_clicked(self, artist_name):
        """Handle clicking on a related artist name.

        Args:
            artist_name: Name of the clicked artist
        """
        try:
            print(f"[App] Related artist clicked: {artist_name}")
            # For now, just update the artist info display
            # In the future, could search library or trigger a search
            self._current_artist_for_metadata = artist_name
            self._current_album_for_metadata = ""

            # Show loading state
            self.artist_bio_label.setText(f'<span style="color: #999; font-style: italic;">Loading artist info for {artist_name}...</span>')
            self._clear_related_artists()

            # Fetch metadata
            self._fetch_artist_metadata(artist_name, None)

        except Exception as e:
            print(f"[App] Failed to handle related artist click: {e}")
            import traceback
            traceback.print_exc()

    def _on_add_artist_to_library(self):
        """Index music folders to add this artist's songs to the library, then refresh availability."""
        try:
            artist = getattr(self, '_current_artist_for_metadata', None)
            if not artist or artist == 'Unknown Artist':
                # Try to infer from current row
                if self.model and self.current_row is not None and 0 <= self.current_row < len(self.model._rows):
                    artist = self.model._rows[self.current_row].get('artist')
            if not artist:
                QMessageBox.information(self, "Add to Library", "No artist is selected.")
                return

            # Disable button while indexing
            if hasattr(self, 'add_artist_btn'):
                self.add_artist_btn.setEnabled(False)

            # Try recent music directories first
            recent_dirs = store.get_record("recent_music_dirs") or []
            target_dirs = []
            if isinstance(recent_dirs, list) and recent_dirs:
                # Index the most recently used directory first
                target_dirs = [recent_dirs[0]]
            else:
                # Prompt user to choose a folder
                folder = QFileDialog.getExistingDirectory(self, "Select Music Folder to Index")
                if folder:
                    # Save and index
                    self._add_recent_music_dir(folder)
                    target_dirs = [folder]
                else:
                    if hasattr(self, 'add_artist_btn'):
                        self.add_artist_btn.setEnabled(True)
                    return

            # Start indexing for each target folder (sequentially)
            for folder in target_dirs:
                self.statusBar().showMessage(f"🔍 Indexing {Path(folder).name}… This may take a while.", 0)
                self._start_background_indexing(folder)

        except Exception as e:
            print(f"[App] Failed to start Add Artist to Library: {e}")
            if hasattr(self, 'add_artist_btn'):
                self.add_artist_btn.setEnabled(True)

    def _add_track_and_play(self, track_title, artist, album):
        """Add clicked song to TOP of queue and play it immediately.

        Strategy:
        1) If the song is already in the queue, move that row to index 0.
        2) Else, try to resolve a file path from the indexed library; add it, then move to 0.
        3) Play row 0 via _play_row(0).
        """
        try:
            print(f"[App] ▶️ Track click: '{track_title}' by '{artist}' (album='{album}')")

            if not getattr(self, 'model', None):
                print("[App] No queue model available")
                return

            norm = lambda s: (s or '').strip().lower()
            t_norm, a_norm = norm(track_title), norm(artist)

            # 1) Check if already in queue
            existing_row = None
            existing_path = None
            for i, row in enumerate(self.model._rows):
                if norm(row.get('title')) == t_norm and norm(row.get('artist')) == a_norm:
                    existing_row = i
                    existing_path = row.get('path')
                    break

            if existing_row is None:
                # 2) Resolve from indexed library if available
                resolved_path = None
                try:
                    if getattr(self, 'indexer', None) and self.indexer.library:
                        # Prefer exact match on artist/title, then fallback to search
                        search_query = f"{artist} {track_title}".strip()
                        results = self.indexer.library.search(search_query, limit=50)

                        # Rank: exact artist+title, then title+album, then title, then any
                        best_song = None
                        for song in results.get('songs', []):
                            if norm(song.title) == t_norm and norm(song.artist) == a_norm:
                                best_song = song
                                break
                        if not best_song and album:
                            for song in results.get('songs', []):
                                if norm(song.title) == t_norm and norm(song.album) == norm(album):
                                    best_song = song
                                    break
                        if not best_song:
                            # Try loose title match
                            for song in results.get('songs', []):
                                if norm(song.title) == t_norm:
                                    best_song = song
                                    break
                        if not best_song and results.get('songs'):
                            best_song = results['songs'][0]

                        if best_song:
                            resolved_path = best_song.path
                except Exception as e:
                    print(f"[App] Library search failed: {e}")

                if not resolved_path:
                    # Fallback: scan the current track's folder for a matching file
                    try:
                        base_dir = None
                        # Prefer directory of currently selected/playing track
                        if getattr(self, 'current_row', None) is not None and \
                           0 <= self.current_row < len(self.model._rows):
                            curr_path = self.model._rows[self.current_row].get('path')
                            if curr_path and not curr_path.startswith(('http://', 'https://')):
                                base_dir = os.path.dirname(curr_path)
                        # Otherwise, find any row with same artist/album to infer folder
                        if not base_dir:
                            for r in self.model._rows:
                                if norm(r.get('artist')) == a_norm and norm(r.get('album')) == norm(album or ''):
                                    p = r.get('path')
                                    if p and not p.startswith(('http://', 'https://')):
                                        base_dir = os.path.dirname(p)
                                        break
                        if base_dir and os.path.isdir(base_dir):
                            print(f"[App] 🔎 Scanning folder for match: {base_dir}")
                            try:
                                from mutagen import File as MutagenFile
                            except Exception:
                                MutagenFile = None

                            for fname in os.listdir(base_dir):
                                fpath = os.path.join(base_dir, fname)
                                if not os.path.isfile(fpath):
                                    continue
                                ext = os.path.splitext(fname)[1].lower()
                                if ext not in AUDIO_EXTS:
                                    continue
                                found_match = False
                                # Try tags first if mutagen is available
                                if MutagenFile is not None:
                                    try:
                                        mf = MutagenFile(fpath, easy=True)
                                        if mf:
                                            t = norm((mf.get('title') or [''])[0] if isinstance(mf.get('title'), list) else (mf.get('title') or ''))
                                            a = norm((mf.get('artist') or [''])[0] if isinstance(mf.get('artist'), list) else (mf.get('artist') or ''))
                                            if t == t_norm and (not a_norm or a == a_norm):
                                                found_match = True
                                    except Exception:
                                        pass
                                if not found_match:
                                    # Fallback: filename heuristic
                                    stem = os.path.splitext(fname)[0]
                                    def sanitize(s):
                                        return ''.join(ch for ch in s.lower() if ch.isalnum())
                                    if sanitize(stem) == sanitize(track_title):
                                        found_match = True
                                if found_match:
                                    resolved_path = fpath
                                    print(f"[App] ✅ Found by folder scan: {os.path.basename(fpath)}")
                                    break
                    except Exception as e:
                        print(f"[App] Folder-scan fallback failed: {e}")

                if not resolved_path:
                    self.statusBar().showMessage(f"Track not found in library: {track_title}", 3000)
                    print(f"[App] ⚠️ Track not found in indexed library or folder scan: {track_title} by {artist}")
                    return

                # Append to queue
                before_len = len(self.model._rows)
                added = self.model.add_paths([resolved_path])
                if added <= 0:
                    self.statusBar().showMessage("Failed to add track to queue", 3000)
                    return
                # New row is last index
                existing_row = before_len
                existing_path = resolved_path

            # Move to TOP if not already there
            if existing_row != 0:
                moved = self.model.moveRows(QModelIndex(), existing_row, 1, QModelIndex(), 0)
                print(f"[App] Move row {existing_row} -> 0: {'OK' if moved else 'FAILED'}")

            # Ensure selection on row 0
            try:
                self.table.selectRow(0)
            except Exception:
                pass

            # Play it
            self._play_row(0)
            self.statusBar().showMessage(f"Playing now: {track_title}", 3000)
            print(f"[App] ✅ Added to top and playing: {track_title}")

        except Exception as e:
            print(f"[App] Failed to add-and-play: {e}")
            import traceback
            traceback.print_exc()

    def _load_album_artwork(self, url):
        """Download and display album artwork from URL.

        Args:
            url: URL to the album artwork image
        """
        try:
            import requests
            from io import BytesIO

            # Download image
            response = requests.get(url, timeout=5)
            response.raise_for_status()

            # Load into QPixmap
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)

            if not pixmap.isNull():
                # Scale to fit 200x200 (matching album_art_label size) while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.album_art_label.setPixmap(scaled_pixmap)
            else:
                self._set_placeholder_artwork()

        except Exception as e:
            print(f"[App] Failed to load album artwork: {e}")
            self._set_placeholder_artwork()

    def _set_placeholder_artwork(self):
        """Set the sidecar icon as placeholder artwork."""
        from pathlib import Path
        icon_path = Path(__file__).parent.parent / "icons" / "sidecarnote.png"
        if icon_path.exists():
            placeholder_pixmap = QPixmap(str(icon_path))
            placeholder_pixmap = placeholder_pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.album_art_label.setPixmap(placeholder_pixmap)
        else:
            self.album_art_label.clear()
            self.album_art_label.setText("No artwork")

    def _build_side_panel(self):
        """
        Build the waveform/EQ panel.
        This creates a horizontal layout: Waveform+Volume (left 50%) | Playback+EQ (right 50%)
        The panel is inserted into the central layout between the queue table and search bar.
        """
        from PySide6.QtWidgets import (
            QWidget, QVBoxLayout, QLabel, QHBoxLayout
        )

        # Create horizontal container for waveform+volume | playback+EQ
        container = QWidget()
        container_layout = QHBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(4)  # Small gap between panels

        # === LEFT PANEL: Waveform + Volume Control ===
        waveform_panel = QWidget()
        waveform_layout = QVBoxLayout()
        waveform_layout.setContentsMargins(8, 8, 8, 8)
        waveform_layout.setSpacing(8)

        # Create waveform widget (moved from status bar)
        from .ui import WaveformProgress
        self.waveform = WaveformProgress()
        self.waveform.setMinimumHeight(80)   # Allow it to shrink more (was 150)
        self.waveform.setMaximumHeight(200)  # Still cap maximum
        waveform_layout.addWidget(self.waveform, stretch=1)  # Give it stretch priority

        # Add spacing between waveform and volume controls
        waveform_layout.addSpacing(24)

        # Volume control below waveform (horizontal BeamSlider with red glow)
        volume_container = QWidget()
        volume_container.setStyleSheet("background: transparent; border: none;")
        volume_sub_layout = QVBoxLayout()
        volume_sub_layout.setContentsMargins(0, 0, 0, 0)
        volume_sub_layout.setSpacing(6)  # Proper spacing between volume elements

        # Volume header with label and value display (compact)
        vol_header_layout = QHBoxLayout()
        vol_header_layout.setContentsMargins(0, 0, 0, 0)

        volume_label = QLabel("VOLUME")
        volume_label.setAlignment(Qt.AlignLeft)
        volume_label.setStyleSheet("color: #ff4d4d; font-size: 9px; font-family: 'Helvetica'; font-weight: bold; background: transparent; border: none;")
        vol_header_layout.addWidget(volume_label)

        vol_header_layout.addStretch()

        # Volume value display (0-10 scale)
        self._volume_value_label = QLabel("5.0")  # Default to 5.0 (50%)
        self._volume_value_label.setAlignment(Qt.AlignRight)
        self._volume_value_label.setStyleSheet("color: #ff8888; font-size: 9px; font-family: 'Helvetica Neue', 'Helvetica', 'Arial Narrow', 'Arial', sans-serif; font-weight: normal; background: transparent; border: none;")
        vol_header_layout.addWidget(self._volume_value_label)

        volume_sub_layout.addLayout(vol_header_layout)

        # Volume slider (compact height)
        from .ui import BeamSlider
        self._volume_slider = BeamSlider(vertical=False, core_color=(220, 60, 60), glow_color=(220, 60, 60, 140), handle_color=(255, 200, 200))
        self._volume_slider.setValue(50)  # Default to 50%
        self._volume_slider.setFixedHeight(20)  # Even more compact
        try:
            self._volume_slider.released.connect(self._on_volume_released)
        except Exception:
            pass
        self._volume_slider.valueChanged.connect(self._on_volume_changed_realtime)
        volume_sub_layout.addWidget(self._volume_slider)

        volume_container.setLayout(volume_sub_layout)
        waveform_layout.addWidget(volume_container, stretch=0)  # Volume doesn't stretch

        waveform_layout.addStretch()  # Push everything to top when panel is tall

        waveform_panel.setLayout(waveform_layout)
        waveform_panel.setStyleSheet("""
            QWidget {
                background: #1a1a1a;
                border: 1px solid #2a2a2a;
                border-radius: 4px;
            }
        """)

        # === RIGHT PANEL: EQ Sliders (compact layout) ===
        eq_panel = QWidget()
        eq_panel.setStyleSheet("""
            QWidget {
                background: #1a1a1a;
                border: 1px solid #2a2a2a;
                border-radius: 4px;
            }
        """)
        self._eq_bg_widget = eq_panel  # Store reference for opacity menu

        eq_main_layout = QVBoxLayout()
        eq_main_layout.setContentsMargins(8, 8, 8, 8)
        eq_main_layout.setSpacing(4)

        # === EQ CONTROLS at top (Preset dropdown + Enable/Disable toggle) ===
        from PySide6.QtWidgets import QComboBox, QPushButton
        eq_controls_container = QWidget()
        eq_controls_container.setStyleSheet("background: transparent; border: none;")
        eq_controls_layout = QVBoxLayout()
        eq_controls_layout.setContentsMargins(0, 0, 0, 0)
        eq_controls_layout.setSpacing(6)

        # EQ header with label and enable/disable toggle (matching volume layout)
        eq_header_layout = QHBoxLayout()
        eq_header_layout.setContentsMargins(0, 0, 0, 0)

        eq_label = QLabel("EQUALIZER")
        eq_label.setAlignment(Qt.AlignLeft)
        eq_label.setStyleSheet("color: #6699cc; font-size: 9px; font-family: 'Helvetica'; font-weight: bold; background: transparent; border: none;")
        eq_header_layout.addWidget(eq_label)

        eq_header_layout.addStretch()

        # EQ Enable/Disable toggle button
        self._eq_enabled = True  # Track EQ state
        self._eq_toggle_btn = QPushButton("ON")
        self._eq_toggle_btn.setFixedWidth(40)
        self._eq_toggle_btn.setFixedHeight(18)
        self._eq_toggle_btn.setCheckable(True)
        self._eq_toggle_btn.setChecked(True)
        self._eq_toggle_btn.clicked.connect(self._on_eq_toggle)
        self._eq_toggle_btn.setStyleSheet("""
            QPushButton {
                background: #0d4f8f;
                color: white;
                border: 1px solid #4da6ff;
                border-radius: 2px;
                font-size: 8px;
                font-weight: bold;
                padding: 2px;
            }
            QPushButton:hover {
                background: #1a5fa0;
            }
            QPushButton:checked {
                background: #0d4f8f;
                color: white;
            }
            QPushButton:!checked {
                background: #2a2a2a;
                color: #808080;
                border: 1px solid #404040;
            }
        """)
        eq_header_layout.addWidget(self._eq_toggle_btn)

        eq_controls_layout.addLayout(eq_header_layout)

        # EQ Preset dropdown (matching volume slider width/style)
        self._eq_preset_combo = QComboBox()
        self._eq_preset_combo.addItems([
            "Flat (No EQ)",
            "Bass Boost",
            "Treble Boost",
            "Loudness",
            "Rock",
            "Jazz",
            "Classical",
            "Electronic",
            "Vocal Forward",
            "Custom"
        ])
        self._eq_preset_combo.setCurrentIndex(0)  # Default to Flat
        self._eq_preset_combo.setFixedHeight(20)
        self._eq_preset_combo.currentIndexChanged.connect(self._on_eq_preset_changed)

        if USE_MODERN_UI:
            system_font = SystemFonts.get_system_font(size=9).family()
            self._eq_preset_combo.setStyleSheet(f"""
                QComboBox {{
                    background: #1a1a1a;
                    color: #b0b0b0;
                    border: 1px solid #2a2a2a;
                    border-radius: 2px;
                    padding: 2px 6px;
                    font-family: '{system_font}';
                    font-size: 9px;
                }}
                QComboBox:hover {{
                    border: 1px solid #4da6ff;
                }}
                QComboBox::drop-down {{
                    border: none;
                }}
                QComboBox::down-arrow {{
                    image: none;
                    border-left: 3px solid transparent;
                    border-right: 3px solid transparent;
                    border-top: 4px solid #808080;
                    margin-right: 6px;
                }}
            """)
        else:
            self._eq_preset_combo.setStyleSheet("""
                QComboBox {
                    background: #1a1a1a;
                    color: #b0b0b0;
                    border: 1px solid #2a2a2a;
                    border-radius: 2px;
                    padding: 2px 6px;
                    font-size: 9px;
                }
                QComboBox:hover {
                    border: 1px solid #4da6ff;
                }
                QComboBox::drop-down {
                    border: none;
                }
                QComboBox::down-arrow {
                    image: none;
                    border-left: 3px solid transparent;
                    border-right: 3px solid transparent;
                    border-top: 4px solid #808080;
                    margin-right: 6px;
                }
            """)

        eq_controls_layout.addWidget(self._eq_preset_combo)

        eq_controls_container.setLayout(eq_controls_layout)
        eq_main_layout.addWidget(eq_controls_container)

        # Add spacing to match volume panel layout
        eq_main_layout.addSpacing(24)

        # EQ sliders container (7 sliders only - no volume)
        from PySide6.QtWidgets import QHBoxLayout as HB, QCheckBox
        eq_x_offset = 12

        # Removed save buttons - now in waveform/volume panel

        eq_layout = HB()
        eq_layout.setContentsMargins(eq_x_offset, 14, eq_x_offset, 14)
        eq_layout.setSpacing(16)  # Slightly more compact

        self._eq_sliders = []
        self._led_meters = []  # Store LED meter widgets

        # 70s receiver-style VU meters with blue glow (fallback style for QSlider)
        slider_css_blue_vu = (
            # The groove (VU meter track) - dark recessed
            "QSlider::groove:vertical { "
            "background: #0a0a0a; "
            "width: 14px; border: 1px solid #1a1a1a; "
            "border-radius: 2px; margin: 0px; "
            "}"
            # The filled part (blue VU glow) - classic 70s receiver blue
            "QSlider::add-page:vertical { "
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "stop:0 #66b3ff, stop:0.4 #3399ff, stop:0.7 #0066cc, stop:1 #003d7a); "
            "border: none; "
            "border-radius: 2px; margin: 0px; "
            "}"
            # The handle (fader cap) - subtle dark style
            "QSlider::handle:vertical { "
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 #404040, stop:0.5 #505050, stop:1 #404040); "
            "width: 22px; height: 16px; margin: -4px 0; "
            "border: 1px solid #2a2a2a; "
            "border-radius: 2px; "
            "}"
            # Hover state - blue accent
            "QSlider::handle:vertical:hover { "
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 #4a4a4a, stop:0.5 #5a5a5a, stop:1 #4a4a4a); "
            "border: 1px solid #4da6ff; "
            "}"
            # Pressed state - darker with blue
            "QSlider::handle:vertical:pressed { "
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 #2a2a2a, stop:0.5 #3a3a3a, stop:1 #2a2a2a); "
            "border: 1px solid #0d4f8f; "
            "}"
        )

        # Create 7 EQ sliders with value labels (no volume - that's separate now)
        self._eq_value_labels = []  # Store value labels
        from .ui import BeamSlider
        for i in range(7):
            # Container for slider + value label
            slider_container = QWidget()
            slider_layout = QVBoxLayout()
            slider_layout.setContentsMargins(0, 0, 0, 0)
            slider_layout.setSpacing(2)

            # Value label (shows current dB value)
            value_label = QLabel("+0")
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setStyleSheet("color: #6699cc; font-size: 8px; font-family: 'Helvetica Neue', 'Helvetica', 'Arial Narrow', 'Arial', sans-serif; font-weight: normal; background: transparent; border: none;")
            slider_layout.addWidget(value_label)
            self._eq_value_labels.append(value_label)

            # Create LED meter + slider combo with overlaid layout
            combo_widget = QWidget()
            combo_widget.setStyleSheet("background: transparent; border: none;")
            combo_layout = QVBoxLayout()
            combo_layout.setContentsMargins(0, 0, 0, 0)
            combo_layout.setSpacing(0)

            # LED meter behind slider (will be Z-order below)
            from .ui import LEDMeter
            led_meter = LEDMeter(color_scheme='blue', num_segments=20)
            led_meter.setFixedHeight(120)
            led_meter.setMaximumWidth(18)
            led_meter.enable_simulation(False)  # Start disabled (no audio playing initially)
            self._led_meters.append(led_meter)

            # Use BeamSlider for all EQ bands for consistent look
            try:
                s = BeamSlider()
                # Connect for label updates only (no EQ changes during drag)
                s.valueChanged.connect(lambda v, idx=i: self._on_eq_label_changed(int(round((v/100.0)*24 - 12)), idx))
                # Apply EQ only when slider is released (prevents crackling)
                s.sliderReleased.connect(self._on_eq_released)
                s.setFixedHeight(120)
            except Exception:
                # Fallback to older QSlider style if BeamSlider import fails
                s = QSlider(Qt.Vertical)
                s.setRange(-12, 12)
                s.setValue(0)
                s.setStyleSheet(slider_css_blue_vu)
                s.valueChanged.connect(lambda val, idx=i: self._on_eq_label_changed(val, idx))
                s.sliderReleased.connect(self._on_eq_released)
                s.setFixedHeight(120)

            # Stack LED meter and slider using QStackedLayout for true overlay
            from PySide6.QtWidgets import QStackedLayout
            stack_container = QWidget()
            stack_container.setFixedHeight(120)
            stack_layout = QStackedLayout()
            stack_layout.setStackingMode(QStackedLayout.StackAll)  # All widgets visible
            stack_layout.addWidget(led_meter)  # Background layer
            stack_layout.addWidget(s)  # Foreground layer (slider)
            stack_container.setLayout(stack_layout)

            slider_layout.addWidget(stack_container)
            self._eq_sliders.append(s)

            slider_container.setLayout(slider_layout)
            eq_layout.addWidget(slider_container)

        eq_main_layout.addLayout(eq_layout)

        # Add labels: 7 EQ frequency labels only
        freq_layout = HB()
        freq_layout.setContentsMargins(eq_x_offset, 0, eq_x_offset, 8)
        freq_layout.setSpacing(16)
        for freq in ["60 Hz", "150 Hz", "400 Hz", "1 kHz", "2.4 kHz", "6 kHz", "15 kHz"]:
            label = QLabel(freq)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: #808080; font-size: 8px; font-family: 'Helvetica Neue', 'Helvetica', 'Arial Narrow', 'Arial', sans-serif; font-weight: normal; background: transparent; border: none;")
            freq_layout.addWidget(label)
        eq_main_layout.addLayout(freq_layout)

        eq_panel.setLayout(eq_main_layout)

        # Add panels to horizontal layout (50/50 split)
        container_layout.addWidget(waveform_panel, stretch=1)
        container_layout.addWidget(eq_panel, stretch=1)
        container.setLayout(container_layout)

        # Set container as content of the collapsible EQ panel
        if hasattr(self, 'eq_panel'):
            self.eq_panel.set_content(container)
            self.eq_panel.lock_content_height(True)

        # Apply initial audio defaults (80%) for volume and EQ on first run
        try:
            QTimer.singleShot(0, self._set_initial_audio_settings)
        except Exception:
            pass

    def _on_volume_changed_realtime(self, val):
        """Handle real-time volume changes for immediate audio feedback (no saving)."""
        try:
            # Update volume value display (0-10 scale)
            if hasattr(self, '_volume_value_label'):
                scaled_value = val / 10.0  # 0-100 -> 0.0-10.0
                self._volume_value_label.setText(f"{scaled_value:.1f}")

            # Apply volume: song volume (val) × master volume
            if hasattr(self, 'player') and hasattr(self.player, 'set_volume'):
                final_volume = (val / 100.0) * self._master_volume
                self.player.set_volume(final_volume)
                print(f"[App] Volume: track={val}% × master={self._master_volume*100:.0f}% = {final_volume*100:.0f}%")
        except Exception as e:
            print(f"[App] ERROR setting volume: {e}")
            import traceback
            traceback.print_exc()

    def _on_volume_released(self):
        """Handle volume slider release - NO auto-save, just mark as user-adjusted."""
        val = self._volume_slider.value()
        print(f"[App] Volume released at: {val} (not saved - click Save button)")
        # Mark that user manually changed volume (to prevent analysis from overwriting)
        self._user_adjusted_volume = True

    def _on_volume_changed(self, val):
        """Legacy method - now just for compatibility."""
        pass  # Real-time handled by _on_volume_changed_realtime

    def _sync_queue_panel_height(self, *_, **__):
        """Keep collapsible panels locked to their content height."""

        def _apply():
            try:
                if getattr(self, "table", None):
                    self.table.updateGeometry()
                if getattr(self, "queue_panel", None):
                    self.queue_panel.refresh_geometry()
                if getattr(self, "eq_panel", None):
                    self.eq_panel.refresh_geometry()
                if getattr(self, "search_panel", None):
                    self.search_panel.refresh_geometry()
            except Exception:
                pass

        QTimer.singleShot(0, _apply)

    def _build_menubar(self):
        """Create a macOS-native menubar with File/Playback/View/Help."""
        mb = self.menuBar()

        # File menu
        m_file = mb.addMenu("File")
        act_add_files = QAction("Add Files…", self)
        act_add_files.triggered.connect(self.on_add_files)
        act_add_folder = QAction("Add Folder…", self)
        act_add_folder.triggered.connect(self.on_add_folder)

        # Dynamic Plex submenu - lists all configured servers with their users
        self._plex_menu = m_file.addMenu("Browse Plex")
        self._update_plex_menu()  # Populate with servers

        act_save_pl = QAction("Save Playlist…", self)
        act_save_pl.triggered.connect(self.on_save_playlist)
        act_load_pl = QAction("Load Playlist…", self)
        act_load_pl.triggered.connect(self.on_load_playlist)
        act_refresh_meta = QAction("Refresh Metadata", self)
        act_refresh_meta.triggered.connect(self.on_refresh_metadata)
        act_save_eq = QAction("Save Song EQ", self)
        act_save_eq.triggered.connect(self._safe_save_eq)
        act_index_folder = QAction("Index Music Folder…", self)
        act_index_folder.triggered.connect(self.on_index_folder)
        act_quit = QAction("Quit", self)
        act_quit.setShortcut(QKeySequence.Quit)
        act_quit.triggered.connect(lambda: QApplication.instance().quit())
        # Add all items except Quit, then separator, then Quit at bottom (customary)
        for a in [act_add_files, act_add_folder, act_save_pl, act_load_pl, act_refresh_meta, act_save_eq, act_index_folder]:
            m_file.addAction(a)
        m_file.addSeparator()
        m_file.addAction(act_quit)

        # Settings menu
        m_settings = mb.addMenu("Settings")
        act_prefs = QAction("Preferences…", self)
        act_prefs.setShortcut(QKeySequence.Preferences)
        act_prefs.triggered.connect(self._open_settings_dialog)
        m_settings.addAction(act_prefs)

        act_manage_plex = QAction("Manage Plex Servers…", self)
        act_manage_plex.triggered.connect(self._open_plex_account_manager)
        m_settings.addAction(act_manage_plex)

        # Playback menu
        m_play = mb.addMenu("Playback")
        act_play = QAction("Play / Pause", self)
        act_play.setShortcut(Qt.Key_Space)
        act_play.triggered.connect(self.on_play)
        m_play.addAction(act_play)

        act_stop = QAction("Stop", self)
        act_stop.triggered.connect(self.on_stop)
        m_play.addAction(act_stop)

        act_next = QAction("Next", self)
        act_next.setShortcut(QKeySequence.MoveToNextWord)
        act_next.triggered.connect(self.on_next)
        m_play.addAction(act_next)

        m_play.addSeparator()

        act_repeat = QAction("Repeat Current Track", self)
        act_repeat.setCheckable(True)
        act_repeat.setChecked(False)
        act_repeat.triggered.connect(self.on_repeat_toggle)
        m_play.addAction(act_repeat)
        self._repeat_action = act_repeat

        # View menu (EQ Opacity + Master Volume)
        from PySide6.QtGui import QActionGroup
        m_view = mb.addMenu("View")

    # Layout presets submenu
        m_layout = m_view.addMenu("Layout Presets")
        layout_grp = QActionGroup(self)
        layout_grp.setExclusive(True)

        act_queue_eq = QAction("Queue + EQ", self)
        act_queue_eq.setCheckable(True)
        act_queue_eq.setChecked(True)  # Default
        act_queue_eq.triggered.connect(lambda: self._apply_layout_preset("queue_eq"))
        layout_grp.addAction(act_queue_eq)
        m_layout.addAction(act_queue_eq)

        act_queue_only = QAction("Queue + Playlists", self)
        act_queue_only.setCheckable(True)
        act_queue_only.triggered.connect(lambda: self._apply_layout_preset("queue_only"))
        layout_grp.addAction(act_queue_only)
        m_layout.addAction(act_queue_only)

        act_eq_only = QAction("EQ Only", self)
        act_eq_only.setCheckable(True)
        act_eq_only.triggered.connect(lambda: self._apply_layout_preset("eq_only"))
        layout_grp.addAction(act_eq_only)
        m_layout.addAction(act_eq_only)

        act_artist_info = QAction("Artist Info", self)
        act_artist_info.setCheckable(True)
        act_artist_info.triggered.connect(lambda: self._apply_layout_preset("artist_info"))
        layout_grp.addAction(act_artist_info)
        m_layout.addAction(act_artist_info)

        # Store layout actions for later reference
        self._layout_actions = {
            "queue_eq": act_queue_eq,
            "queue_only": act_queue_only,
            "eq_only": act_eq_only,
            "artist_info": act_artist_info,
        }

        m_view.addSeparator()

        # Rack Mode (experimental)
        self._act_rack_mode = QAction("Rack Mode (experimental)", self)
        self._act_rack_mode.setCheckable(True)
        self._act_rack_mode.setChecked(False)
        self._act_rack_mode.toggled.connect(self._set_rack_mode)
        m_view.addAction(self._act_rack_mode)

        # Master Volume submenu
        m_master_vol = m_view.addMenu("Master Volume")
        vol_grp = QActionGroup(self); vol_grp.setExclusive(True)
        self._master_volume_actions = {}
        def _add_master_vol(name, val):
            act = QAction(name, self); act.setCheckable(True)
            act.triggered.connect(lambda: self._set_master_volume(val))
            vol_grp.addAction(act); m_master_vol.addAction(act); self._master_volume_actions[name] = act
        _add_master_vol("Master Volume • 25%", 0.25)
        _add_master_vol("Master Volume • 50%", 0.50)
        _add_master_vol("Master Volume • 75%", 0.75)
        _add_master_vol("Master Volume • 100% (Default)", 1.00)
        # Default to 100%
        self._master_volume_actions["Master Volume • 100% (Default)"].setChecked(True)

        m_view.addSeparator()

        # EQ Opacity submenu
        grp = QActionGroup(self)
        grp.setExclusive(True)
        self._eq_opacity_actions = {}
        def _add_opc(name, val):
            act = QAction(name, self)
            act.setCheckable(True)
            act.triggered.connect(lambda: self._set_eq_opacity(val))
            grp.addAction(act)
            m_view.addAction(act)
            self._eq_opacity_actions[name] = act
        _add_opc("EQ Plate Opacity • Low (30%)", 0.30)
        _add_opc("EQ Plate Opacity • Medium (60%)", 0.60)
        _add_opc("EQ Plate Opacity • High (90%)", 0.90)
        # Default to Medium
        self._eq_opacity_actions["EQ Plate Opacity • Medium (60%)"].setChecked(True)
        # Apply after side panel builds (safe-call)
        QTimer.singleShot(0, lambda: self._set_eq_opacity(0.60))

        m_view.addSeparator()

        # LED Meters toggle
        self._led_meters_action = QAction("Show LED Meters", self)
        self._led_meters_action.setCheckable(True)
        self._led_meters_action.setChecked(True)  # On by default
        self._led_meters_action.triggered.connect(self._toggle_led_meters_from_menu)
        m_view.addAction(self._led_meters_action)

        # Help menu
        m_help = mb.addMenu("Help")
        act_about = QAction("About Sidecar EQ", self)
        act_about.triggered.connect(self._show_about_dialog)
        m_help.addAction(act_about)

    def _open_settings_dialog(self):
        try:
            dlg = SettingsDialog(self, self)
            dlg.exec()
        except Exception as e:
            print(f"[SidecarEQ] Settings dialog failed: {e}")

    def _apply_ui_prefs_from_store(self):
        """Load UI preferences from the store and apply to the current UI."""
        try:
            prefs = store.get_record("ui:settings") or {}
            # Queue alternating row colors
            alt = bool(prefs.get("queue_alternating_stripes", True))
            if getattr(self, "table", None) is not None:
                self.table.setAlternatingRowColors(alt)
                # Empty-state stripes
                empty_stripes = bool(prefs.get("queue_empty_stripes", True))
                if hasattr(self.table, "setShowEmptyStripes"):
                    self.table.setShowEmptyStripes(empty_stripes)

            # Layout preset behavior
            remember = bool(prefs.get("remember_layout", True))
            default_layout = prefs.get("default_layout_preset", "queue_eq")
            # Map old names to new standardized names
            if default_layout == "full_view":
                default_layout = "queue_eq"
            elif default_layout == "search_only" or default_layout == "search_queue":
                default_layout = "artist_info"
            if not remember and default_layout in ("queue_eq", "queue_only", "eq_only", "artist_info"):
                self._apply_layout_preset(default_layout)
            else:
                # Always apply default layout on startup for consistency
                self._apply_layout_preset("queue_eq")

            # Rack Mode at startup (experimental)
            rack_on = bool(prefs.get("rack_mode_startup", False))
            if rack_on:
                # delay a tick to let widgets finish building
                QTimer.singleShot(0, lambda: self._set_rack_mode(True))
        except Exception as e:
            print(f"[SidecarEQ] Applying UI prefs failed: {e}")

    def _show_about_dialog(self):
        """Display the About dialog with app information."""
        about_text = """<h2>Sidecar EQ</h2>
<p><b>Version 1.1.1</b></p>

<p>A powerful music player with per-track EQ and volume memory.<br/>
Set your perfect sound once per track—the app remembers forever.</p>

<h3>Features</h3>
<ul>
<li><b>Per-Track Memory:</b> Each song remembers your EQ and volume</li>
<li><b>7-Band Real-Time EQ:</b> Professional audio processing (60Hz-15kHz)</li>
<li><b>Multi-Source Playback:</b> Local files, Plex servers, web URLs</li>
<li><b>Background Analysis:</b> Auto-detection of LUFS, tempo, frequency response</li>
<li><b>Smart UI:</b> Four layout presets, LED meters, star ratings</li>
</ul>

<p>Built with ❤️ by Michael Todd Edwards<br/>
Licensed under AGPL v3</p>

<p><a href="https://github.com/OhioMathTeacher/sidecar-eq">GitHub Repository</a></p>
"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("About Sidecar EQ")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(about_text)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    def _set_eq_opacity(self, level: float):
        """Set opacity on the EQ background plate (if present)."""
        try:
            bg = getattr(self, "_eq_bg_widget", None)
            if not bg:
                return
            from PySide6.QtWidgets import QGraphicsOpacityEffect
            eff = getattr(self, "_eq_opacity_effect", None)
            if eff is None:
                eff = QGraphicsOpacityEffect(self)
                self._eq_opacity_effect = eff
                bg.setGraphicsEffect(eff)
            eff.setOpacity(max(0.0, min(1.0, float(level))))
        except Exception as e:
            print(f"[App] Error setting EQ opacity: {e}")

    def _set_master_volume(self, level: float):
        """Set master volume multiplier (affects all tracks)."""
        try:
            self._master_volume = max(0.0, min(1.0, float(level)))
            print(f"[App] Master volume set to {self._master_volume*100:.0f}%")
            # Re-apply current track volume to reflect new master volume
            if hasattr(self, '_volume_slider'):
                current_track_vol = self._volume_slider.value()
                final_volume = (current_track_vol / 100.0) * self._master_volume
                if hasattr(self, 'player') and hasattr(self.player, 'set_volume'):
                    self.player.set_volume(final_volume)
                    print(f"[App] Applied: track={current_track_vol}% × master={self._master_volume*100:.0f}% = {final_volume*100:.0f}%")
        except Exception as e:
            print(f"[App] Error setting master volume: {e}")

    def _on_save_volume_clicked(self):
        """Save only volume for current track."""
        if self.current_row is None:
            self.statusBar().showMessage("No track loaded", 3000)
            return

        try:
            # Get current volume value
            volume = self._volume_slider.value()

            # Save to store
            if hasattr(self, 'model') and self.model and self.current_row < self.model.rowCount():
                path_index = self.model.index(self.current_row, 0)
                file_path = self.model.data(path_index, Qt.ItemDataRole.UserRole)
                if file_path:
                    store.set_record(f"volume:{file_path}", volume)

            # Show confirmation
            self._save_volume_btn.setText("✓ Saved!")
            self._set_button_success_style(self._save_volume_btn)
            self._save_feedback_timer.start(3000)
            self.statusBar().showMessage(f"✓ Volume saved ({volume}%)", 2000)
            print(f"[App] Volume saved: {volume}%")
        except Exception as e:
            self.statusBar().showMessage(f"Save failed: {e}", 3000)
            print(f"[App] Save volume failed: {e}")

    def _on_save_eq_clicked(self):
        """Save only EQ settings for current track."""
        if self.current_row is None:
            self.statusBar().showMessage("No track loaded", 3000)
            return

        try:
            # Save EQ settings
            self.save_eq_for_current_track()

            # Show confirmation
            self._save_eq_btn.setText("✓ Saved!")
            self._set_button_success_style(self._save_eq_btn)
            self._save_feedback_timer.start(3000)
            self.statusBar().showMessage("✓ EQ settings saved", 2000)
            print("[App] EQ settings saved")
        except Exception as e:
            self.statusBar().showMessage(f"Save failed: {e}", 3000)
            print(f"[App] Save EQ failed: {e}")

    def _on_save_both_clicked(self):
        """Save both volume and EQ settings for current track."""
        if self.current_row is None:
            self.statusBar().showMessage("No track loaded", 3000)
            return

        try:
            # Save volume
            volume = self._volume_slider.value()
            if hasattr(self, 'model') and self.model and self.current_row < self.model.rowCount():
                path_index = self.model.index(self.current_row, 0)
                file_path = self.model.data(path_index, Qt.ItemDataRole.UserRole)
                if file_path:
                    store.set_record(f"volume:{file_path}", volume)

            # Save EQ
            self.save_eq_for_current_track()

            # Show confirmation on ALL THREE buttons to indicate both vol and EQ were saved
            self._save_volume_btn.setText("✓ Saved!")
            self._set_button_success_style(self._save_volume_btn)

            self._save_eq_btn.setText("✓ Saved!")
            self._set_button_success_style(self._save_eq_btn)

            self._save_both_btn.setText("✓ Saved!")
            self._set_button_success_style(self._save_both_btn)

            self._save_feedback_timer.start(3000)
            self.statusBar().showMessage("✓ Volume & EQ saved", 2000)
            print("[App] Both volume and EQ saved")
        except Exception as e:
            self.statusBar().showMessage(f"Save failed: {e}", 3000)
            print(f"[App] Save both failed: {e}")

    def _set_button_success_style(self, button):
        """Apply success styling to a button."""
        btn_font_size = 10
        btn_padding = "4px 12px"

        if USE_MODERN_UI:
            system_font = SystemFonts.get_system_font(size=btn_font_size, weight="Semibold").family()
            button.setStyleSheet(f"""
                QPushButton {{
                    background: {ModernColors.with_opacity(ModernColors.SUCCESS, 0.15)};
                    color: {ModernColors.SUCCESS};
                    border: 1px solid {ModernColors.SUCCESS};
                    border-radius: 3px;
                    padding: {btn_padding};
                    font-family: '{system_font}';
                    font-size: {btn_font_size}px;
                    font-weight: 600;
                    min-width: 70px;
                }}
            """)
        else:
            button.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(52, 199, 89, 0.15);
                    color: #34c759;
                    border: 1px solid #34c759;
                    border-radius: 3px;
                    padding: {btn_padding};
                    font-size: {btn_font_size}px;
                    font-weight: 600;
                    min-width: 70px;
                }}
            """)

    def _auto_save_settings_for_current_track(self):
        """Automatically save EQ and volume settings when switching tracks or ending playback."""
        if self.current_row is None:
            return

        try:
            paths = self.model.paths()
            if not paths or self.current_row >= len(paths):
                return

            # Save both volume and EQ silently (no UI feedback)
            # Save volume
            volume = self._volume_slider.value() if hasattr(self, '_volume_slider') else 75
            path = paths[self.current_row]
            if path:
                store.set_record(f"volume:{path}", volume)

            # Save EQ
            self.save_eq_for_current_track()

            print(f"[App] Auto-saved EQ and volume for: {Path(path).stem} (Vol: {volume}%)")
        except Exception as e:
            print(f"[App] Auto-save failed: {e}")

    def _reset_save_buttons_text(self):
        """Reset save button back to normal state after confirmation."""
        self._save_both_btn.setText("Save EQ and Vol")

        # Reset to normal styling
        btn_font_size = 10
        btn_padding = "4px 12px"

        if USE_MODERN_UI:
            system_font = SystemFonts.get_system_font(size=btn_font_size, weight="Semibold").family()
            self._save_both_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {ModernColors.ACCENT};
                    border: 1px solid {ModernColors.ACCENT};
                    border-radius: 3px;
                    padding: {btn_padding};
                    font-family: '{system_font}';
                    font-size: {btn_font_size}px;
                    font-weight: 600;
                    min-width: 100px;
                }}
                QPushButton:hover {{
                    background: {ModernColors.with_opacity(ModernColors.ACCENT, 0.1)};
                    border: 1px solid {ModernColors.ACCENT_HOVER};
                }}
                QPushButton:pressed {{
                    background: {ModernColors.with_opacity(ModernColors.ACCENT, 0.2)};
                }}
                QPushButton:disabled {{
                    color: {ModernColors.TEXT_QUATERNARY};
                    border: 1px solid {ModernColors.SEPARATOR};
                }}
            """)
        else:
            self._save_both_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: #4d88ff;
                    border: 1px solid #4d88ff;
                    border-radius: 3px;
                    padding: {btn_padding};
                    font-size: {btn_font_size}px;
                    font-weight: 600;
                    min-width: 100px;
                }}
                QPushButton:hover {{
                    background: rgba(77, 136, 255, 0.1);
                    border: 1px solid #6699ff;
                }}
                QPushButton:pressed {{
                    background: rgba(77, 136, 255, 0.2);
                }}
                QPushButton:disabled {{
                    color: #666666;
                    border: 1px solid #3a3a3a;
                }}
            """)

    def _on_save_settings_clicked(self):
        """Legacy handler - redirect to save both."""
        self._on_save_both_clicked()

    def _reset_save_button_text(self):
        """Legacy reset - redirect to new method."""
        self._reset_save_buttons_text()

    # --- Toolbar handlers ---
    def on_play(self):
        """Toggle between play and pause. Play button shows current state."""
        from .play_state_delegate import PlayStateDelegate

        # If currently playing, pause it
        if self.player.is_playing():
            self.player.pause()
            self.statusBar().showMessage("Paused")
            self.play_btn.setActive(False)  # Show as not active (paused state)
            # Update play state indicator to show paused (blinking)
            if self.current_row is not None:
                self.play_state_delegate.set_play_state(self.current_row, PlayStateDelegate.PLAY_STATE_PAUSED)
            # Stop LED meters when paused
            self._update_led_meters_playback(False)
        else:
            # Check if we're in paused state (track loaded but not playing)
            # Use the Player's is_playing() method which works for both AudioEngine and QMediaPlayer
            if self.current_row is not None and hasattr(self.player, '_engine') and self.player._use_audio_engine:
                # AudioEngine: check if paused
                if self.player._engine.is_paused:
                    # Resume from paused position
                    self.player._engine.play()  # This will resume
                    self.statusBar().showMessage("Playing (resumed)")
                    self.play_btn.setActive(True)
                    self.play_state_delegate.set_play_state(self.current_row, PlayStateDelegate.PLAY_STATE_PLAYING)
                    self._update_led_meters_playback(True)
                elif self.current_row is None:
                    # No track loaded - start from selected or first row
                    sel = self.table.selectionModel().selectedRows()
                    self._play_row(sel[0].row() if sel else 0)
                else:
                    # Track was stopped, restart from beginning
                    self._play_row(self.current_row)
            elif self.current_row is not None and self.player._player.playbackState() == QMediaPlayer.PausedState:
                # QMediaPlayer: Resume from paused position
                self.player._player.play()
                self.statusBar().showMessage("Playing (resumed)")
                self.play_btn.setActive(True)
                self.play_state_delegate.set_play_state(self.current_row, PlayStateDelegate.PLAY_STATE_PLAYING)
                self._update_led_meters_playback(True)
            elif self.current_row is None:
                # No track loaded - start from selected or first row
                sel = self.table.selectionModel().selectedRows()
                self._play_row(sel[0].row() if sel else 0)
            else:
                # Track was stopped, restart from beginning
                self._play_row(self.current_row)

    def on_stop(self):
        """Stop playback and save current position for resume."""
        from .play_state_delegate import PlayStateDelegate

        if self.current_row is not None and self.player:
            # Save current position for potential resume
            try:
                current_pos = self.player._player.position()
                paths = self.model.paths()
                if self.current_row < len(paths):
                    path = paths[self.current_row]
                    # Store position in per-track settings
                    store_data = store.get_record(path) or {}
                    store_data['last_position_ms'] = current_pos
                    store.put_record(path, store_data)
                    print(f"[App] Saved position {current_pos}ms for resume")
            except Exception as e:
                print(f"[App] Failed to save position: {e}")

            # Update play state indicator to show stopped (before clearing current_row)
            self.play_state_delegate.set_play_state(self.current_row, PlayStateDelegate.PLAY_STATE_STOPPED)
            self._play_state = PlayStateDelegate.PLAY_STATE_STOPPED

        self.player.stop()
        self.statusBar().showMessage("Stopped")
        self.play_btn.setActive(False)

        # Stop LED meters when stopped
        self._update_led_meters_playback(False)

    def on_next(self):
        # Auto-save settings before moving to next track
        if self.current_row is not None:
            self._auto_save_settings_for_current_track()

        if self.current_row is None:
            self._play_row(0)
            return
        self._play_row(self.current_row + 1)

    def on_repeat_toggle(self):
        """Toggle repeat mode on/off."""
        self._repeat_mode = not self._repeat_mode
        status = "ON" if self._repeat_mode else "OFF"
        print(f"[App] Repeat mode: {status}")
        self._status_label.setText(f"🔁 Repeat: {status}")

        # Update repeat button visual state
        if hasattr(self, '_repeat_btn'):
            self._repeat_btn.setActive(self._repeat_mode)

        # Update menu action checked state
        if hasattr(self, '_repeat_action'):
            self._repeat_action.setChecked(self._repeat_mode)

    def on_add_based_on_source(self):
        # v1.0.0: Local files only (Plex/Web deferred to v2.0.0)
        return self.on_add_files()

    def on_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add Audio/Video Files", "", "Media Files (*.wav *.flac *.mp3 *.ogg *.m4a *.mp4 *.mov *.avi *.mkv *.flv *.m4v *.webm)"
        )
        if files:
            count = self.model.add_paths(files)
            if self.current_row is None and count > 0:
                self.table.selectRow(0)
            self.statusBar().showMessage(f"Added {count} files")

            # Auto-add to library (only local audio files, not videos or URLs)
            self._auto_add_to_library(files)

    def on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Add Folder")
        if not folder:
            return
        paths = []
        for root, _, files in os.walk(folder):
            for name in files:
                if name.startswith("._"):
                    continue
                if Path(name).suffix.lower() in MEDIA_EXTS:
                    paths.append(os.path.join(root, name))
        count = self.model.add_paths(paths)
        if self.current_row is None and count > 0:
            self.table.selectRow(0)
        self.statusBar().showMessage(f"Added {count} files from folder")

        # Auto-add to library (only local audio files, not videos or URLs)
        self._auto_add_to_library(paths)

    def on_browse_plex(self):
        """Open Plex browser to add tracks from Plex server."""
        from .plex_browser import PlexBrowserDialog

        # Load Plex server config from store
        plex_servers = store.get_record("plex_servers") or []
        if not plex_servers:
            QMessageBox.warning(
                self,
                "No Plex Server",
                "No Plex server configured. Please add a Plex server first via Plex → Manage Servers."
            )
            return

        # Use first configured server (TODO: support multiple servers)
        server_config = plex_servers[0]

        # Get username from server config (first user)
        users = server_config.get("users", [])
        username = users[0].get("username") if users else None

        dialog = PlexBrowserDialog(self, server_config=server_config, username=username)
        if dialog.exec() == QDialog.Accepted:
            selected_tracks = dialog.get_selected_tracks()
            if selected_tracks:
                # Add Plex tracks to queue with metadata
                count = self.model.add_plex_tracks(selected_tracks)

                if self.current_row is None and count > 0:
                    self.table.selectRow(0)

                self.statusBar().showMessage(f"Added {count} tracks from Plex")

    def on_remove_selected(self):
        sel = self.table.selectionModel().selectedRows()
        rows = [ix.row() for ix in sel]
        self.model.remove_rows(rows)
        self.statusBar().showMessage(f"Removed {len(rows)} rows")

    def _on_search_result_selected(self, data, play_immediately: bool):
        """Handle selection of a search result.

        Args:
            data: Either a file path string (legacy) or dict with 'type' and 'paths'
            play_immediately: If True, add and play; if False, just add to queue
        """
        # Handle both legacy (string path) and new (dict) formats
        if isinstance(data, str):
            # Legacy format - single file path
            file_paths = [data]
            result_type = 'song'
        elif isinstance(data, dict):
            # New format - dict with type and paths
            file_paths = data.get('paths', [])
            result_type = data.get('type', 'song')
        else:
            self.statusBar().showMessage("❌ Invalid search result data!", 3000)
            print(f"[App] Error: Unexpected data type: {type(data)}")
            return

        if not file_paths:
            self.statusBar().showMessage("❌ No file paths provided!", 3000)
            print(f"[App] Error: file_paths is empty")
            return

        # Debug: Log what we received
        print(f"[App] Search result selected: {result_type} with {len(file_paths)} file(s)")
        print(f"[App] Play immediately: {play_immediately}")

        # Filter out files that don't exist and collect missing ones
        existing_paths = []
        missing_paths = []

        for file_path in file_paths:
            file_path_obj = Path(file_path)
            if file_path_obj.exists():
                existing_paths.append(file_path)
            else:
                missing_paths.append(file_path)
                print(f"[App] Warning: File does not exist at: {file_path}")

        # If some files are missing, show error dialog
        if missing_paths:
            # Show error for first missing file
            self._show_missing_file_dialog(missing_paths[0])

            # If ALL files are missing, don't add anything
            if not existing_paths:
                self.statusBar().showMessage(f"❌ All files not found!", 4000)
                return
            else:
                # Some files exist - show warning and continue with existing ones
                self.statusBar().showMessage(
                    f"⚠️  {len(missing_paths)} file(s) not found, adding {len(existing_paths)} available",
                    4000
                )

        # Add existing files to queue
        count = self.model.add_paths(existing_paths)

        if count > 0:
            new_row = len(self.model._rows) - 1  # Last row added

            if play_immediately:
                # Play the first new track immediately
                first_new_row = new_row - count + 1
                self._play_row(first_new_row)

                # Show appropriate message based on type
                if result_type == 'album':
                    album_title = data.get('title', 'Unknown Album')
                    self.statusBar().showMessage(f"▶️  Playing Album: {album_title} ({count} tracks)", 4000)
                elif result_type == 'artist':
                    artist_name = data.get('name', 'Unknown Artist')
                    self.statusBar().showMessage(f"▶️  Playing Artist: {artist_name} ({count} tracks)", 4000)
                else:
                    filename = Path(existing_paths[0]).name
                    self.statusBar().showMessage(f"▶️  Now Playing: {filename}", 4000)

                self.statusBar().setStyleSheet("QStatusBar { background: #2a4a2a; color: #4eff4e; }")
                # Reset style after message
                QTimer.singleShot(4000, lambda: self.statusBar().setStyleSheet(""))
            else:
                # Just added to queue - show clear feedback
                if result_type == 'album':
                    album_title = data.get('title', 'Unknown Album')
                    self.statusBar().showMessage(f"✅ Added Album to Queue: {album_title} ({count} tracks)", 3000)
                elif result_type == 'artist':
                    artist_name = data.get('name', 'Unknown Artist')
                    self.statusBar().showMessage(f"✅ Added Artist to Queue: {artist_name} ({count} tracks)", 3000)
                else:
                    filename = Path(existing_paths[0]).name
                    self.statusBar().showMessage(f"✅ Added to Queue: {filename}", 3000)

                self.statusBar().setStyleSheet("QStatusBar { background: #2a3a4a; color: #4a9eff; }")
                # Reset style after message
                QTimer.singleShot(3000, lambda: self.statusBar().setStyleSheet(""))
        else:
            self.statusBar().showMessage(f"⚠️  Could not add file(s) to queue", 3000)
            print(f"[App] Error: model.add_paths returned 0 for {len(existing_paths)} path(s)")

    def _show_missing_file_dialog(self, file_path: str):
        """Show dialog when file is not found, with helpful suggestions.

        Args:
            file_path: The missing file path
        """
        from PySide6.QtWidgets import QMessageBox, QPushButton

        file_path_obj = Path(file_path)

        # Detect if it's on an external volume
        is_volume = file_path.startswith('/Volumes/')
        volume_name = None
        if is_volume:
            parts = file_path.split('/')
            if len(parts) > 2:
                volume_name = parts[2]

        # Create message box
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("File Not Found")

        if is_volume and volume_name:
            msg.setText(f"Cannot access file on unmounted volume")
            msg.setInformativeText(
                f"<b>Volume:</b> {volume_name}<br>"
                f"<b>File:</b> {file_path_obj.name}<br><br>"
                f"This file is on an external drive or network share that is not currently connected.<br><br>"
                f"<b>Solutions:</b><br>"
                f"• Connect/mount the <b>{volume_name}</b> volume<br>"
                f"• Re-index your music library from a new location<br>"
                f"• Check if the file has been moved or deleted"
            )
        else:
            msg.setText(f"File not found")
            msg.setInformativeText(
                f"<b>Path:</b> {file_path}<br><br>"
                f"The file may have been moved, renamed, or deleted.<br><br>"
                f"<b>Suggestions:</b><br>"
                f"• Check if the file still exists at this location<br>"
                f"• Re-index your music library (File → Index Folder...)<br>"
                f"• Verify the file hasn't been moved to a different folder"
            )

        # Add buttons
        msg.setStandardButtons(QMessageBox.Ok)

        # Add "Re-index Library" button if it's a volume issue
        if is_volume:
            reindex_btn = msg.addButton("Re-index Library...", QMessageBox.ActionRole)
            reindex_btn.clicked.connect(lambda: self._handle_reindex_request())

        msg.exec()

    def _handle_reindex_request(self):
        """Handle request to re-index library after missing file error."""
        # Trigger the index folder action
        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "Re-index Music Library",
            "This will scan a new folder and update your music library.\n\n"
            "Note: This will replace your current library index.\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Call the existing index folder method
            self._index_music_folder()

    def _check_for_missing_volumes(self):
        """Check if any files in the library are on unmounted volumes and show notification."""
        if not self.indexer:
            return

        library = self.indexer.get_library()
        if not library:
            return

        # Collect missing volume information
        missing_volumes = set()
        missing_count = 0

        for artist in library.artists.values():
            for album in artist.albums.values():
                for song in album.songs:
                    if not Path(song.path).exists():
                        # Check if it's on a volume
                        if song.path.startswith('/Volumes/'):
                            parts = song.path.split('/')
                            if len(parts) > 2:
                                missing_volumes.add(parts[2])
                        missing_count += 1

        # Show notification if missing files found
        if missing_volumes:
            from PySide6.QtWidgets import QMessageBox

            volumes_str = ", ".join(sorted(missing_volumes))

            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Unmounted Volumes Detected")
            msg.setText(f"Some music files are on unmounted volumes")
            msg.setInformativeText(
                f"<b>{missing_count}</b> files are unavailable on these volumes:<br>"
                f"<b>{volumes_str}</b><br><br>"
                f"To access these files:<br>"
                f"• Connect/mount the external drive(s)<br>"
                f"• Or re-index your library from a new location<br><br>"
                f"You can still use files that are currently available."
            )
            msg.setStandardButtons(QMessageBox.Ok)

            # Don't block - use a timer to show after the window is visible
            QTimer.singleShot(500, msg.exec)

    def _on_command_entered(self, command: str):
        """Handle command entered in search bar.

        Args:
            command: Command string (e.g., "HELP", "PLAYLIST local")
        """
        parts = command.strip().split()
        if not parts:
            return

        cmd = parts[0].upper()
        args = parts[1:] if len(parts) > 1 else []

        if cmd == "HELP":
            self._show_help_dialog()
        elif cmd == "PLAYLIST":
            self._handle_playlist_command(args)
        elif cmd == "EQ":
            self._handle_eq_command(args)
        else:
            self.statusBar().showMessage(f"Unknown command: {cmd}. Try HELP", 3000)

    def _show_help_dialog(self):
        """Show help dialog with available commands."""
        help_text = """<h2>Sidecar EQ Commands</h2>

        <p><b>Search:</b> Just type song names, artists, or albums!</p>

        <p><b>Available Commands:</b></p>
        <ul>
            <li><b>HELP</b> - Show this help dialog</li>
            <li><b>PLAYLIST local</b> - Load local .m3u playlist</li>
            <li><b>EQ export</b> - Export current EQ settings</li>
        </ul>

        <p><b>Tips:</b></p>
        <ul>
            <li>Press <b>Enter</b> to play the first result immediately</li>
            <li>Click a result to add it to the queue</li>
            <li>Tracks with ⭐ have saved EQ settings</li>
            <li>▶ shows play count</li>
        </ul>
        """
        QMessageBox.information(self, "Sidecar EQ Help", help_text)

    def _handle_playlist_command(self, args: list):
        """Handle PLAYLIST command.

        Args:
            args: Command arguments
        """
        if not args or args[0] != "local":
            self.statusBar().showMessage("Usage: PLAYLIST local", 3000)
            return

        # Open file dialog for .m3u playlist
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Playlist", "", "Playlist Files (*.m3u *.m3u8)"
        )
        if file_path:
            self.on_load_playlist(file_path)

    def _handle_eq_command(self, args: list):
        """Handle EQ command.

        Args:
            args: Command arguments
        """
        if not args or args[0] != "export":
            self.statusBar().showMessage("Usage: EQ export", 3000)
            return

        # Export current EQ settings
        if self.current_row is not None and self.current_row < len(self.model._rows):
            track_info = self.model._rows[self.current_row]
            path = track_info.get("path", "")

            if path:
                settings = store.get_record(path)
                if settings and "eq" in settings:
                    # Show EQ values
                    eq_vals = settings["eq"]
                    msg = f"Current EQ:\n{eq_vals}"
                    QMessageBox.information(self, "EQ Settings", msg)
                else:
                    self.statusBar().showMessage("No EQ saved for this track", 3000)
            else:
                self.statusBar().showMessage("No track playing", 3000)
        else:
            self.statusBar().showMessage("No track playing", 3000)

    def on_index_folder(self):
        """Index a music folder for search functionality (runs in background)."""
        if not self.indexer:
            QMessageBox.warning(self, "Indexer Error", "Library indexer not available!")
            return

        folder = QFileDialog.getExistingDirectory(self, "Select Music Folder to Index")
        if not folder:
            return

        # Add to recent directories
        self._add_recent_music_dir(folder)

        # Start background indexing thread
        self._start_background_indexing(folder)

    def _load_recent_music_dirs(self):
        """Load recent music directories from settings and populate combo box."""
        try:
            recent_dirs = store.get_record("recent_music_dirs") or []

            self.music_dir_combo.clear()

            # If we have recent dirs, show the most recent one as the default/current selection
            # Prefer the last used directory if available, otherwise default to the user's home folder
            current_dir = None
            if recent_dirs:
                cand = recent_dirs[-1]
                if Path(cand).exists():
                    current_dir = cand
            if current_dir is None:
                current_dir = str(Path.home())

            display_name = self._shorten_path(current_dir)
            # Show current folder at top (will be selected by default)
            self.music_dir_combo.addItem(f"♪ {display_name}", current_dir)
            # Add "Choose different folder..." option
            self.music_dir_combo.addItem("📁 Choose Different Folder...")

            # Add Plex servers if available
            plex_servers = self._discover_plex_servers()
            if plex_servers:
                for server_info in plex_servers:
                    self.music_dir_combo.addItem(
                        f"🎵 Plex: {server_info['name']}",
                        f"plex://{server_info['name']}"
                    )

            # Add other recent directories (excluding the current one)
            for dir_path in reversed(recent_dirs[-10:]):  # Last 10 directories, newest first
                if dir_path != current_dir and Path(dir_path).exists():
                    display_name = self._shorten_path(dir_path)
                    self.music_dir_combo.addItem(f"  {display_name}", dir_path)

            # Keep index 0 selected (current folder)
            self.music_dir_combo.setCurrentIndex(0)

        except Exception as e:
            print(f"[App] Failed to load recent music dirs: {e}")

    def _shorten_path(self, path: str, max_length: int = 50) -> str:
        """Shorten a path for display purposes."""
        if len(path) <= max_length:
            return path

        # Show ~/... for home directory
        home = str(Path.home())
        if path.startswith(home):
            path = "~" + path[len(home):]

        # If still too long, show start and end
        if len(path) > max_length:
            keep_start = max_length // 2 - 3
            keep_end = max_length // 2 - 3
            path = path[:keep_start] + "..." + path[-keep_end:]

        return path

    def _add_recent_music_dir(self, dir_path: str):
        """Add a directory to recent music directories list."""
        try:
            recent_dirs = store.get_record("recent_music_dirs") or []

            # Remove if already exists (we'll add to end)
            if dir_path in recent_dirs:
                recent_dirs.remove(dir_path)

            # Add to end
            recent_dirs.append(dir_path)

            # Keep only last 20
            recent_dirs = recent_dirs[-20:]

            # Save
            store.put_record("recent_music_dirs", recent_dirs)

            # Reload combo box
            self._load_recent_music_dirs()

        except Exception as e:
            print(f"[App] Failed to add recent music dir: {e}")

    def _on_music_dir_selected(self, index: int):
        """Handle selection from music directory combo box."""
        # Get the current data (directory path)
        dir_path = self.music_dir_combo.itemData(index)

        if index == 0 and dir_path:
            # Current folder selected - no action needed (just showing current state)
            return
        elif self.music_dir_combo.itemText(index).startswith("📁"):
            # "Choose Folder..." or "Choose Different Folder..." selected - open file dialog
            folder = QFileDialog.getExistingDirectory(self, "Select Music Folder")
            if folder:
                self._add_recent_music_dir(folder)
                # Optionally trigger indexing
                reply = QMessageBox.question(
                    self,
                    "Index Folder?",
                    f"Would you like to index this folder for searching?\n\n{folder}",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    self._start_background_indexing(folder)
        elif dir_path and dir_path.startswith("plex://"):
            # Plex server selected - show account picker
            server_name = dir_path.replace("plex://", "")
            self._connect_to_plex_server(server_name)
            # Reset to current folder after connection attempt
            self.music_dir_combo.setCurrentIndex(0)
        else:
            # Existing directory selected
            dir_path = self.music_dir_combo.itemData(index)
            if dir_path and Path(dir_path).exists():
                self.statusBar().showMessage(f"Music folder: {dir_path}", 5000)

                # Optionally ask to re-index
                reply = QMessageBox.question(
                    self,
                    "Re-index Folder?",
                    f"Would you like to re-index this folder?\n\n{dir_path}",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self._start_background_indexing(dir_path)
            else:
                QMessageBox.warning(self, "Folder Not Found", f"The selected folder no longer exists:\n{dir_path}")
                # Remove from recent list
                recent_dirs = store.get_record("recent_music_dirs") or []
                if dir_path in recent_dirs:
                    recent_dirs.remove(dir_path)
                    store.put_record("recent_music_dirs", recent_dirs)
                self._load_recent_music_dirs()

    def _start_background_indexing(self, folder: str):
        """Start indexing in a background thread.

        Args:
            folder: Path to folder to index
        """
        from PySide6.QtCore import QRunnable, QThreadPool, QObject, Signal

        class ProgressSignals(QObject):
            """Signals for progress updates (must be QObject for thread safety)."""
            progress = Signal(int, int)  # scanned, added
            finished = Signal(int, int, str)  # added, total, error

        class IndexingTask(QRunnable):
            """Background task for indexing music library."""
            def __init__(self, indexer, folder, signals):
                super().__init__()
                self.indexer = indexer
                self.folder = folder
                self.signals = signals

            def run(self):
                """Run the indexing scan."""
                try:
                    def progress_callback(scanned, added):
                        self.signals.progress.emit(scanned, added)

                    added = self.indexer.scan_folder(
                        self.folder,
                        recursive=True,
                        progress_callback=progress_callback
                    )
                    library = self.indexer.get_library()
                    total = library.total_songs
                    self.signals.finished.emit(added, total, "")
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    self.signals.finished.emit(0, 0, str(e))

        # Create signals
        signals = ProgressSignals()
        signals.progress.connect(self._on_indexing_progress)
        signals.finished.connect(self._on_indexing_complete)

        # Show initial status
        self.statusBar().showMessage(f"🔍 Indexing {Path(folder).name}... You can keep using the app!", 0)

        # Create and start background task
        task = IndexingTask(self.indexer, folder, signals)
        QThreadPool.globalInstance().start(task)

    def _on_indexing_progress(self, scanned: int, added: int):
        """Handle progress updates from background indexer.

        Args:
            scanned: Number of audio files scanned so far
            added: Number of new tracks added so far
        """
        self.statusBar().showMessage(
            f"🔍 Indexing... Scanned {scanned} files, added {added} new tracks",
            0
        )

    def _on_indexing_complete(self, added: int, total: int, error: Optional[str]):
        """Handle indexing completion (called from background thread).

        Args:
            added: Number of tracks added
            total: Total tracks in index
            error: Error message if failed, None if successful
        """
        if error:
            self.statusBar().showMessage(f"Indexing failed: {error}", 5000)
            QMessageBox.warning(self, "Indexing Error", f"Failed to index folder:\n{error}")
            if hasattr(self, 'add_artist_btn'):
                self.add_artist_btn.setEnabled(True)
            return

        # Show completion message
        self.statusBar().showMessage(
            f"✅ Indexing complete! Added {added} new tracks. Total: {total} indexed tracks.",
            5000
        )

        # Refresh availability in the Now Playing tracklist
        try:
            if self.model and self.current_row is not None and 0 <= self.current_row < len(self.model._rows):
                current_path = self.model._rows[self.current_row].get('path')
                if current_path:
                    self._update_artist_info_display(current_path)
        except Exception:
            pass

        # Re-enable button if present
        if hasattr(self, 'add_artist_btn'):
            self.add_artist_btn.setEnabled(True)

        # Show dialog with results
        QMessageBox.information(
            self,
            "Indexing Complete! 🎵",
            f"Successfully indexed your music library!\n\n"
            f"• Added: {added} new tracks\n"
            f"• Total indexed: {total} tracks\n\n"
            f"The Now Playing panel now reflects available tracks for this artist."
        )

    def _discover_plex_servers(self):
        """Get configured Plex servers from store.

        Returns:
            List of dicts with server info, or empty list if none configured.
        """
        try:
            servers = store.get_record("plex_servers") or []

            if servers:
                print(f"[App] Found {len(servers)} configured Plex server(s)")
            return servers

        except Exception as e:
            print(f"[App] Failed to load Plex servers: {e}")
            return []

    def _connect_to_plex_server(self, server_name: str):
        """Connect to a Plex server after user selects a Home User.

        Args:
            server_name: Name of the Plex server to connect to
        """
        # Get server configuration
        servers = store.get_record("plex_servers") or []
        server = next((s for s in servers if s.get('name') == server_name), None)

        if not server:
            QMessageBox.warning(
                self,
                "Server Not Found",
                f"Server '{server_name}' not found.\n\n"
                "Please configure it in Settings → Manage Plex Servers."
            )
            return

        users = server.get('users', [])
        if not users:
            QMessageBox.warning(
                self,
                "No Users Configured",
                f"No Home Users configured for {server_name}.\n\n"
                "Please configure users in Settings → Manage Plex Servers."
            )
            return

        # If only one user, use it directly
        if len(users) == 1:
            user = users[0]
        else:
            # Multiple users - let user choose
            from .plex_account_manager import PlexAccountSelectorDialog
            dialog = PlexAccountSelectorDialog(server_name, users, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            user = dialog.get_selected_user()

        if user:
            username = user.get('username', 'Unknown')
            self._update_plex_server_users(server_name, users)
            self._open_plex_browser_as_user(server, username)

    def _open_plex_browser_as_user(self, server: dict, username: str):
        """Open Plex browser dialog for a specific Home User.

        Args:
            server: Server configuration dict with host, port, users
            username: Name of the Home User to connect as
        """
        try:
            from .plex_browser import PlexBrowserDialog

            # Note: For now, we'll use a simple approach
            # In the future, this should authenticate as the specific Home User
            # For guest users (no PIN), we can connect directly
            # For users with PINs, we need to get a session token

            dialog = PlexBrowserDialog(self, server_config=server, username=username)
            result = dialog.exec()

            if result == QDialog.DialogCode.Accepted:
                selected_tracks = dialog.get_selected_tracks()
                if selected_tracks:
                    # Add Plex tracks to queue with metadata
                    count = self.model.add_plex_tracks(selected_tracks)

                    if self.current_row is None and count > 0:
                        self.table.selectRow(0)

                    server_name = server.get('name', 'Plex')
                    self.statusBar().showMessage(f"✅ Added {count} tracks from {server_name} ({username})", 5000)
        except Exception as e:
            print(f"[App] Failed to connect to Plex: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(
                self,
                "Plex Connection Failed",
                f"Could not connect to {server.get('name', 'Plex')} as {username}:\n\n{str(e)}"
            )

    def _open_plex_account_manager(self):
        """Open the Plex Server Manager dialog to configure Plex servers and Home Users."""
        from .plex_account_manager import PlexServerManagerDialog

        dialog = PlexServerManagerDialog(store, self)
        dialog.exec()

        # Reload music directory dropdown to show newly added servers
        self._load_recent_music_dirs()

        # Update Plex menu to reflect changes
        self._update_plex_menu()

    def _update_plex_server_users(self, server_name: str, users: list) -> None:
        """Persist updated Plex user metadata back to the store."""
        try:
            servers = store.get_record("plex_servers") or []
            changed = False
            for server in servers:
                if server.get('name') == server_name:
                    if server.get('users') != users:
                        server['users'] = users
                        changed = True
                    break
            if changed:
                store.put_record("plex_servers", servers)
        except Exception as exc:
            print(f"[App] Failed to persist Plex user changes: {exc}")

    def _update_plex_menu(self):
        """Update the Browse Plex submenu with configured servers and users."""
        if not hasattr(self, '_plex_menu'):
            return

        # Clear existing menu items
        self._plex_menu.clear()

        # Get configured servers
        servers = self._discover_plex_servers()

        if not servers:
            # No servers configured - show placeholder
            act_no_servers = QAction("No Plex Servers Configured", self)
            act_no_servers.setEnabled(False)
            self._plex_menu.addAction(act_no_servers)
            self._plex_menu.addSeparator()
            act_manage = QAction("Configure Plex Servers…", self)
            act_manage.triggered.connect(self._open_plex_account_manager)
            self._plex_menu.addAction(act_manage)
            return

        # Add menu items for each server
        for server in servers:
            server_name = server.get('name', 'Unknown Server')
            users = server.get('users', [])

            if not users:
                # Server has no users configured - show disabled entry
                act_server = QAction(f"{server_name} (no users configured)", self)
                act_server.setEnabled(False)
                self._plex_menu.addAction(act_server)
                continue

            if len(users) == 1:
                # Single user - direct action (no submenu)
                user = users[0]
                username = user.get('username', 'Unknown')
                act_user = QAction(f"{server_name}: {username}", self)
                act_user.triggered.connect(
                    lambda checked=False, s=server, u=username: self._open_plex_browser_as_user(s, u)
                )
                self._plex_menu.addAction(act_user)
            else:
                # Multiple users - create submenu
                server_submenu = self._plex_menu.addMenu(f"{server_name}")
                for user in users:
                    username = user.get('username', 'Unknown')
                    has_pin = user.get('pin') is not None
                    label = f"{username} {'🔒' if has_pin else ''}"
                    act_user = QAction(label, self)
                    act_user.triggered.connect(
                        lambda checked=False, s=server, u=username: self._open_plex_browser_as_user(s, u)
                    )
                    server_submenu.addAction(act_user)

        # Add separator and management option at bottom
        self._plex_menu.addSeparator()
        act_manage = QAction("Manage Plex Servers…", self)
        act_manage.triggered.connect(self._open_plex_account_manager)
        self._plex_menu.addAction(act_manage)

    def _set_initial_audio_settings(self):
        """Initialize volume and EQ sliders to sensible defaults.

        This is called on app startup to set global defaults (80% volume, neutral EQ).
        These defaults will be overridden when:
        - A track is loaded that has saved analysis data
        - Real-time analysis completes for a track
        """
        try:
            # Set global default volume to 50% (0..100 scale) - was 80%, too loud!
            if hasattr(self, '_volume_slider') and self._volume_slider:
                try:
                    self._volume_slider.blockSignals(True)  # Don't trigger save
                    self._volume_slider.setValue(50)  # Reduced from 80
                    self._volume_slider.blockSignals(False)
                except Exception:
                    pass
                try:
                    self._volume_value_label.setText(f"{(50/10):.1f}")  # Display 5.0
                except Exception:
                    pass

            # Set global default EQ to 50 (BeamSlider 0..100, maps to 0dB = flat)
            # Flat EQ is a better default than boosted
            for s in getattr(self, '_eq_sliders', []):
                try:
                    s.blockSignals(True)  # Don't trigger save
                    s.setValue(50)  # 50 = 0dB (flat response)
                    s.blockSignals(False)
                except Exception:
                    pass

            # Update value labels (map 0..100 to -12..12 dB)
            for idx, lbl in enumerate(getattr(self, '_eq_value_labels', [])):
                try:
                    slider = self._eq_sliders[idx]
                    v = slider.value()
                    db = int(round((v/100.0)*24 - 12))
                    lbl.setText(f"{db:+d}")
                except Exception:
                    pass

            # Apply to audio backend if present
            try:
                if hasattr(self.player, 'set_volume'):
                    self.player.set_volume(0.5)  # 50% volume
            except Exception:
                pass

            print("[App] 🎚️  Set global defaults: 80% volume, +4.8dB EQ (will be overridden by track analysis)")
        except Exception as e:
            print(f"[App] Failed to set initial audio settings: {e}")

    def _auto_refresh_metadata(self):
        """Start background metadata loading for rows that need it."""
        if not self.model or not hasattr(self.model, '_rows'):
            return

        # Find all rows that need metadata extraction
        rows_needing_metadata = []
        for i, row in enumerate(self.model._rows):
            if row.get("_needs_metadata"):
                rows_needing_metadata.append(i)

        if not rows_needing_metadata:
            return

        print(f"[App] Starting background metadata extraction for {len(rows_needing_metadata)} tracks...")

        # Create worker and thread
        self._metadata_thread = QThread()
        self._metadata_worker = MetadataLoaderWorker(self.model, rows_needing_metadata)
        self._metadata_worker.moveToThread(self._metadata_thread)

        # Connect signals
        self._metadata_worker.metadata_loaded.connect(self._on_metadata_loaded)
        self._metadata_worker.finished.connect(self._on_metadata_loading_finished)
        self._metadata_thread.started.connect(self._metadata_worker.run)

        # Start the thread
        self._metadata_thread.start()

    def _on_metadata_loaded(self, row_index, metadata):
        """Handle metadata loaded for a single row (called from main thread)."""
        if self.model:
            self.model.update_row_metadata(row_index, metadata)

    def _on_metadata_loading_finished(self):
        """Clean up after background metadata loading completes."""
        print("[App] Background metadata extraction complete")

        # Clean up thread
        if hasattr(self, '_metadata_thread'):
            self._metadata_thread.quit()
            self._metadata_thread.wait()
            self._metadata_thread.deleteLater()
            delattr(self, '_metadata_thread')

        if hasattr(self, '_metadata_worker'):
            self._metadata_worker.deleteLater()
            delattr(self, '_metadata_worker')


    def _auto_add_to_library(self, paths: list):
        """Automatically add local audio files to the library when added to queue.

        This keeps the on-disk library in sync with the queue so Now Playing
        stats (top tracks, play counts) remain accurate.

        Args:
            paths: List of file paths to add to library
        """
        if not self.indexer:
            return

        # Filter to only local audio files (skip videos, URLs, etc.)
        from .video_extractor import is_video_file
        audio_paths = []
        for path in paths:
            # Skip URLs
            if isinstance(path, str) and path.startswith(('http://', 'https://')):
                continue

            # Skip videos
            try:
                if is_video_file(path):
                    continue
            except Exception:
                pass

            # Check if it's an audio file
            file_ext = Path(path).suffix.lower()
            if file_ext in AUDIO_EXTS:
                audio_paths.append(path)

        if not audio_paths:
            return

        # Add to library in background
        added = 0
        for path in audio_paths:
            try:
                song = self.indexer._create_song(Path(path))
                if song:
                    self.indexer.library.add_song(song)
                    added += 1
            except Exception as e:
                print(f"[App] Failed to add {path} to library: {e}")

        if added > 0:
            self.indexer.save_library()
            print(f"[App] 📚 Auto-added {added} track(s) to library")

    def _on_metadata_lookup(self, row: int):
        """Lookup and update metadata for a specific track from online sources.

        Args:
            row: Row index in the queue table
        """
        try:
            if not self.model or row < 0 or row >= len(self.model._rows):
                return

            row_data = self.model._rows[row]
            path = row_data.get('path', '')

            # Skip URLs (can't lookup metadata for streams)
            if path.startswith(('http://', 'https://')):
                self.statusBar().showMessage("Metadata lookup not available for URLs/streams")
                return

            # Get current metadata for search
            title = row_data.get('title') or Path(path).stem
            artist = row_data.get('artist', '')
            album = row_data.get('album', '')

            # Show status
            self.statusBar().showMessage(f"Looking up metadata for: {title}...")
            print(f"[App] 🌐 Metadata lookup: {title} - {artist}")

            # For now, use simple online search approach
            # Fetch online metadata using Wikipedia, MusicBrainz, and Last.fm
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox, QPushButton
            from .online_metadata import get_metadata_fetcher

            # Create a dialog to show the results
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Online Metadata: {artist}")
            dialog.resize(600, 500)

            layout = QVBoxLayout(dialog)

            # Text browser for rich HTML content
            browser = QTextBrowser()
            browser.setOpenExternalLinks(True)  # Allow clicking links
            browser.setStyleSheet("""
                QTextBrowser {
                    background-color: #1e1e1e;
                    color: #e0e0e0;
                    border: 1px solid #404040;
                    border-radius: 4px;
                }
            """)

            # Show loading message first
            browser.setHtml("""
                <html>
                <body style="font-family: Arial; color: #e0e0e0; padding: 20px;">
                    <h2 style="color: #4a9eff;">🔍 Fetching metadata...</h2>
                    <p>Querying Wikipedia, MusicBrainz, and Last.fm for artist information...</p>
                </body>
                </html>
            """)

            layout.addWidget(browser)

            # Button box
            button_box = QDialogButtonBox(QDialogButtonBox.Close)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)

            # Show dialog (non-blocking)
            dialog.show()

            # Fetch metadata in background (we'll use a simple approach for now)
            # In a production app, you'd use QThread or async to avoid blocking the UI
            self.statusBar().showMessage(f"Fetching online metadata for '{artist}'...")

            try:
                fetcher = get_metadata_fetcher()
                info = fetcher.fetch_artist_info(artist, title)

                # Build local metadata dict for context
                local_meta = {
                    'title': title,
                    'artist': artist,
                    'album': album,
                    'path': path
                }

                # Format as HTML and display
                html = fetcher.format_artist_info_html(info, local_meta)
                browser.setHtml(html)

                if info:
                    source = info.get('source', 'online')
                    self.statusBar().showMessage(f"Metadata fetched from {source}", 3000)
                else:
                    self.statusBar().showMessage("No online metadata found", 3000)

            except Exception as e:
                browser.setHtml(f"""
                    <html>
                    <body style="font-family: Arial; color: #e0e0e0; padding: 20px;">
                        <h2 style="color: #ff6b6b;">❌ Error fetching metadata</h2>
                        <p>{str(e)}</p>
                        <p style="color: #999;">Make sure you have an internet connection.</p>
                    </body>
                    </html>
                """)
                self.statusBar().showMessage(f"Metadata fetch failed: {e}", 3000)
                print(f"[App] Metadata fetch error: {e}")

        except Exception as e:
            print(f"[App] Error in metadata lookup: {e}")
            self.statusBar().showMessage(f"Metadata lookup failed: {e}")

    def on_refresh_metadata(self):
        """Re-scan all tracks in the queue and update their metadata."""
        self._refresh_metadata_internal(show_message=True)

    def _refresh_metadata_internal(self, show_message=True):
        """Internal method to refresh metadata."""
        if not self.model or not hasattr(self.model, '_rows'):
            return

        try:
            from mutagen import File as MutagenFile
        except:
            QMessageBox.warning(self, "Mutagen Not Installed",
                              "Mutagen library is required for metadata reading.\nInstall with: pip install mutagen")
            return

        updated_count = 0
        for row in self.model._rows:
            path = row.get('path', '')
            if not path or path.startswith(('http://', 'https://')):
                continue  # Skip URLs

            try:
                # Re-read metadata using the improved logic
                mf = MutagenFile(path)
                if mf and hasattr(mf, 'tags') and mf.tags:
                    tags = mf.tags

                    title = None
                    artist = None
                    album = None

                    # Title
                    for key in ['TIT2', 'title', '©nam', 'TITLE']:
                        if key in tags:
                            val = tags[key]
                            title = str(val[0]) if isinstance(val, list) else str(val)
                            break

                    # Artist
                    for key in ['TPE1', 'artist', '©ART', 'ARTIST']:
                        if key in tags:
                            val = tags[key]
                            artist = str(val[0]) if isinstance(val, list) else str(val)
                            break

                    # Album
                    for key in ['TALB', 'album', '©alb', 'ALBUM']:
                        if key in tags:
                            val = tags[key]
                            album = str(val[0]) if isinstance(val, list) else str(val)
                            break

                    # Update the row if we found any metadata
                    if any([title, artist, album]):
                        if title:
                            row['title'] = title
                        if artist:
                            row['artist'] = artist
                        if album:
                            row['album'] = album
                        updated_count += 1
            except Exception as e:
                print(f"[App] Failed to refresh metadata for {Path(path).name}: {e}")
                continue

        # Force table refresh
        self.model.layoutChanged.emit()
        if show_message:
            self.statusBar().showMessage(f"Refreshed metadata for {updated_count} tracks")
        print(f"[App] Refreshed metadata for {updated_count}/{len(self.model._rows)} tracks")

    def on_save_playlist(self):
        playlists_dir = str(self._get_playlists_dir())
        out, _ = QFileDialog.getSaveFileName(self, "Save Playlist (JSON)", playlists_dir, "JSON (*.json)")
        if not out:
            return
        playlist.save_json(self.model.paths(), out)
        self.statusBar().showMessage(f"Saved playlist to {out}")

    def on_load_playlist(self):
        playlists_dir = str(self._get_playlists_dir())
        inp, _ = QFileDialog.getOpenFileName(self, "Load Playlist (JSON or M3U)", playlists_dir, "Playlists (*.json *.m3u *.m3u8)")
        if not inp:
            return
        suffix = Path(inp).suffix.lower()
        if suffix == ".json":
            paths = playlist.load_json(inp)
        else:
            lines = Path(inp).read_text(errors="ignore").splitlines()
            paths = [ln for ln in lines if ln and not ln.startswith("#")]
        if paths:
            count = self.model.add_paths(paths)
            if self.current_row is None and count > 0:
                self.table.selectRow(0)
            self.statusBar().showMessage(f"Loaded {count} items")
        else:
            QMessageBox.information(self, "Load Playlist", "No paths found in playlist.")

    def _safe_save_eq(self):
        try:
            self.save_eq_for_current_track()
            self.statusBar().showMessage('EQ saved')
        except Exception as e:
            QMessageBox.warning(self, 'Save EQ', str(e))

    def import_plex_playlist(self):
        playlists = get_playlist_titles()  # list of (title, id)
        if not playlists:
            QMessageBox.information(self, "Plex", "No Plex playlists found.")
            return
        titles = [t for t, _ in playlists]
        title, ok = QInputDialog.getItem(self, "Import Plex Playlist", "Choose a playlist:", titles, 0, False)
        if not ok or not title:
            return
        # Find id for chosen title
        pl_id = None
        for t, pid in playlists:
            if t == title:
                pl_id = pid
                break
        if not pl_id:
            QMessageBox.warning(self, "Plex", "Selected playlist not found.")
            return
        tracks = get_tracks_for_playlist(pl_id)
        if not tracks:
            QMessageBox.information(self, "Plex", "No tracks in the selected playlist.")
            return

        # Add tracks using the model's add_track method for Plex items
        count = 0
        for track in tracks:
            try:
                # The track already has the right format from plex_helpers.py
                added = self.model.add_track(track)
                count += added
            except Exception as e:
                print(f"[App] Failed to add Plex track: {e}")
                continue

        if not count:
            QMessageBox.information(self, "Plex", "No tracks could be imported from playlist.")
            return

        if self.current_row is None and count > 0:
            self.table.selectRow(0)
        self.statusBar().showMessage(f"Imported {count} tracks from Plex playlist: {title}")

    # --- Playback helpers ---
    def _play_row(self, row: int):
        paths = self.model.paths()
        if not paths or row is None or row < 0 or row >= len(paths):
            return

        # Auto-save settings for previous track before switching
        if self.current_row is not None and self.current_row != row:
            self._auto_save_settings_for_current_track()

        # Cancel any running background analysis since we're switching tracks
        if self._analysis_worker and self._analysis_worker.isRunning():
            self._analysis_worker.stop_analysis()
            self._pending_analysis_path = None

        # Reset user volume adjustment flag for new track
        self._user_adjusted_volume = False

        self.current_row = row

        # Enable Save button since we have a loaded track
        if hasattr(self, '_save_both_btn'):
            self._save_both_btn.setEnabled(True)

        # Get the track info to handle both local files, URLs, and Plex streams
        track_info = self.model._rows[row] if row < len(self.model._rows) else {}
        path = paths[row]

        # Update metadata display for the loaded track
        self._update_metadata_display(path)

        # Update Now Playing artist info display
        self._update_artist_info_display(path)

        # Determine source type and playback URL
        # Robust source detection with validation
        stream_url = track_info.get('stream_url')

        if stream_url and stream_url.strip() and stream_url.startswith(('http://', 'https://')):
            # Plex track - has valid stream URL
            playback_url = stream_url
            identifier = stream_url
            source_type = 'plex'
        elif path and path.startswith(('http://', 'https://')):
            # Website URL - path is HTTP/HTTPS URL
            playback_url = path
            identifier = path
            source_type = 'url'
        elif path and path.strip():
            # Local file - could be audio or video
            from .video_extractor import is_video_file, extract_audio_from_video

            if is_video_file(path):
                # Video file - extract audio for playback
                print(f"[App] Video file detected: {Path(path).name}")
                extracted_audio = extract_audio_from_video(path)
                if extracted_audio:
                    playback_url = str(extracted_audio)
                    identifier = path  # Use original video path as identifier
                    source_type = 'video'
                    print(f"[App] Using extracted audio: {Path(extracted_audio).name}")
                else:
                    print(f"[App] Failed to extract audio from: {Path(path).name}")
                    raise ValueError(f"Could not extract audio from video file: '{Path(path).name}'")
            else:
                # Regular audio file
                playback_url = path
                identifier = path
                source_type = 'local'
        else:
            # Invalid/empty path - this shouldn't happen
            print(f"[Error] Invalid path/URL for row {row}: path='{path}', track_info={track_info}")
            raise ValueError(f"Invalid path for playback: '{path}'")

        try:
            self.player.play(playback_url)
            self.play_btn.setActive(True)
            self.table.selectRow(row)

            # Update play state indicator to show playing
            from .play_state_delegate import PlayStateDelegate
            self.play_state_delegate.set_play_state(row, PlayStateDelegate.PLAY_STATE_PLAYING)
            self._play_state = PlayStateDelegate.PLAY_STATE_PLAYING

            # Enable Save button since we have a loaded track
            if hasattr(self, '_save_both_btn'):
                self._save_both_btn.setEnabled(True)

            # Start LED meters if they're visible and enabled
            self._update_led_meters_playback(True)

            title = self.model.data(self.model.index(row, 2))  # Title is now column 2
            artist = self.model.data(self.model.index(row, 3)) or ""  # Artist is column 3
            album = self.model.data(self.model.index(row, 4)) or ""  # Album is column 4

            # Show source type in status
            source_labels = {'local': '', 'url': 'from URL', 'plex': 'from Plex', 'video': 'from video'}
            source_label = source_labels.get(source_type, '')
            status_msg = f"Playing: {title}" + (f" ({source_label})" if source_label else "")
            self.statusBar().showMessage(status_msg)

            # Track play count using the identifier
            self._increment_play_count(identifier)

            # Handle EQ and analysis based on source type
            # ALWAYS load saved settings first (prioritize manual saves)
            saved_data = self.load_eq_for_track(identifier)
            saved_volume = saved_data.get('suggested_volume') if saved_data else None
            has_manual_save = saved_data.get('manual_save', False) if saved_data else False

            # If user manually saved settings, ALWAYS use those (skip analysis)
            if has_manual_save and saved_data:
                print(f"[App] ✓ Loading manually saved settings for: {Path(identifier).stem}")
                preset_name = saved_data.get('eq_preset')
                self._apply_eq_settings(saved_data.get('gains_db', saved_data.get('eq_settings', [0]*7)), preset_name)
            elif source_type in ('plex', 'url'):
                # Streaming sources: just load saved settings (no analysis possible)
                if saved_data:
                    preset_name = saved_data.get('eq_preset')
                    self._apply_eq_settings(saved_data.get('gains_db', saved_data.get('eq_settings', [0]*7)), preset_name)
                    print(f"[App] Loaded saved EQ settings for streaming source: {Path(identifier).stem}")
                else:
                    # Reset to flat EQ for new streaming sources
                    self._apply_eq_settings([0]*7, "Flat (No EQ)")
                    print(f"[App] No saved settings for streaming source: {Path(identifier).stem} - using flat EQ")
            elif source_type == 'video':
                # Video files: analyze extracted audio but use original video path as identifier
                print(f"[App] Analyzing extracted audio from video: {Path(identifier).name}")
                eq_data = self._get_or_analyze_eq(playback_url)  # Analyze the extracted audio file
                if eq_data:
                    # Save settings using video file path as key for consistency
                    preset_name = eq_data.get('eq_preset')
                    self._apply_eq_settings(eq_data.get('gains_db', [0]*7), preset_name)
                    # Store analysis under video file identifier
                    self._store_analysis_for_video(identifier, eq_data)
                else:
                    # Reset to flat EQ if no analysis available
                    self._apply_eq_settings([0]*7, "Flat (No EQ)")
            else:
                # Regular local audio files: Load saved settings or analyze
                if saved_data:
                    # Use saved settings (from previous analysis or manual save)
                    preset_name = saved_data.get('eq_preset')
                    self._apply_eq_settings(saved_data.get('gains_db', saved_data.get('eq_settings', [0]*7)), preset_name)
                    print(f"[App] ✓ Loaded saved EQ for: {Path(identifier).stem}")
                else:
                    # No saved settings - start background analysis
                    print(f"[App] No saved settings - starting analysis for: {Path(identifier).stem}")
                    self._apply_eq_settings([0]*7, "Flat (No EQ)")  # Flat EQ while analyzing
                    self._start_background_analysis(identifier)

            # Apply saved volume for ALL source types (not just local files)
            if saved_volume is not None:
                print(f"[App] ✓ Loading saved volume: {saved_volume}%")
                self._apply_volume_setting(saved_volume)
            else:
                # No saved volume - use default 75% for new tracks
                print("[App] ⚠️  No saved volume found, defaulting to 75%")
                self._apply_volume_setting(75)

        except Exception as e:
            QMessageBox.warning(self, "Play error", str(e))

    def _get_or_analyze_eq(self, path: str) -> dict:
        """Get saved EQ data or start background analysis if first time playing."""
        # First check if we have saved EQ settings
        try:
            saved_data = self.load_eq_for_track(path)
            if saved_data:
                # Also apply saved volume if available
                if 'suggested_volume' in saved_data:
                    self._apply_volume_setting(saved_data['suggested_volume'])
                return saved_data
        except Exception:
            pass

        # No saved EQ found, start background analysis
        self._start_background_analysis(path)
        return None

    def _start_background_analysis(self, path: str):
        """Start background analysis for the given track."""
        try:
            # Stop any existing analysis
            if self._analysis_worker and self._analysis_worker.isRunning():
                self._analysis_worker.stop_analysis()
                self._analysis_worker.wait(1000)  # Wait up to 1 second

            # Start new background analysis
            self._analysis_worker = BackgroundAnalysisWorker(path, self)
            self._analysis_worker.analysis_complete.connect(self._on_analysis_complete)
            self._analysis_worker.analysis_failed.connect(self._on_analysis_failed)
            self._pending_analysis_path = path

            self._analysis_worker.start()
            self.statusBar().showMessage(f"Playing: {Path(path).stem} (analyzing in background...)")

        except Exception as e:
            print(f"[App] Failed to start background analysis: {e}")
            self.statusBar().showMessage(f"Playing: {Path(path).stem}")

    def _on_analysis_complete(self, path: str, analysis_result: dict):
        """Handle completed background analysis."""
        try:
            # Check if this analysis is still relevant (user might have switched tracks)
            if path != self._pending_analysis_path:
                print(f"[App] Ignoring stale analysis for: {Path(path).stem}")
                return

            # Save the analysis results
            self._save_analysis_data(path, analysis_result)

            # Apply EQ and volume suggestions in real-time
            if analysis_result:
                # Apply EQ settings
                eq_data = analysis_result.get('eq_data', {})
                if eq_data:
                    gains_db = eq_data.get('gains_db', [0]*7)
                    # Analysis doesn't set a preset - it's custom based on audio content
                    self._apply_eq_settings(gains_db, "Custom")

                # Apply volume suggestion ONLY if user hasn't manually adjusted it
                if not self._user_adjusted_volume:
                    analysis_data = analysis_result.get('analysis_data', {})
                    if 'suggested_volume' in analysis_data:
                        self._apply_volume_setting(analysis_data['suggested_volume'])
                else:
                    print("[App] Skipping volume from analysis (user adjusted manually)")

                lufs = analysis_result.get('analysis_data', {}).get('loudness_lufs', -23)
                self.statusBar().showMessage(f"Playing: {Path(path).stem} (analyzed: {lufs:.1f} LUFS - settings applied)")
                print(f"[App] Applied real-time analysis for: {Path(path).stem}")

        except Exception as e:
            print(f"[App] Error applying analysis results: {e}")
        finally:
            self._pending_analysis_path = None

    def _on_analysis_failed(self, path: str, error_message: str):
        """Handle failed background analysis."""
        print(f"[App] Background analysis failed for {Path(path).stem}: {error_message}")
        if path == self._pending_analysis_path:
            self.statusBar().showMessage(f"Playing: {Path(path).stem} (analysis failed)")
            self._pending_analysis_path = None

    def _apply_volume_setting(self, suggested_volume: int):
        """Apply suggested volume to the volume slider without triggering save."""
        try:
            if hasattr(self, '_volume_slider'):
                # Handle None or invalid values - default to 75% (mid-range)
                if suggested_volume is None:
                    volume = 75
                    print("[App] ⚠️  Volume is None, defaulting to 75%")
                else:
                    # Clamp to valid range (0-100)
                    volume = max(0, min(100, suggested_volume))

                # Block signals to prevent saving this loaded value back to the track
                self._volume_slider.blockSignals(True)
                self._volume_slider.setValue(volume)
                self._volume_slider.blockSignals(False)

                # UPDATE LABEL to match slider (signals are blocked so realtime handler won't fire)
                if hasattr(self, '_volume_value_label'):
                    scaled_value = volume / 10.0  # 0-100 -> 0.0-10.0
                    self._volume_value_label.setText(f"{scaled_value:.1f}")

                # Apply to player immediately
                if hasattr(self.player, 'set_volume'):
                    self.player.set_volume(volume / 100.0)

                print(f"[App] 📻 LOADED volume {volume}% (display: {volume/10.0:.1f})")
        except Exception as e:
            print(f"[App] Failed to apply volume: {e}")

    def _save_volume_for_current_track(self, volume_value: int):
        """Save volume setting for the currently playing track."""
        try:
            if self.current_row is None or not self.model:
                return

            # Get current track path
            track_path = self.model.data(self.model.index(self.current_row, 0), Qt.UserRole)
            if not track_path:
                return

            # Load existing EQ data or create new
            existing_data = self.load_eq_for_track(track_path) or {}

            # Update volume setting
            existing_data['suggested_volume'] = volume_value

            # Save back to file
            self._save_analysis_data(track_path, existing_data)
            print(f"[App] 💾 SAVED volume {volume_value}% for: {track_path}")

        except Exception as e:
            print(f"[App] Error saving volume: {e}")

    def _apply_eq_settings(self, gains_db: list, preset_name: str = None):
        """Apply EQ settings to the sliders and update value labels.

        Args:
            gains_db: List of EQ gains in dB (-12 to +12 range)
            preset_name: Optional preset name to restore in the dropdown
        """
        try:
            if hasattr(self, '_eq_sliders') and len(gains_db) >= len(self._eq_sliders):
                for i, slider in enumerate(self._eq_sliders):
                    if i < len(gains_db):
                        # Clamp to dB range (-12 to +12)
                        db_value = max(-12, min(12, int(gains_db[i])))

                        # Convert dB to BeamSlider 0..100 scale
                        # -12dB -> 0, 0dB -> 50, +12dB -> 100
                        slider_value = int(round(((db_value + 12) / 24.0) * 100))

                        # Block signals to prevent saving during load
                        slider.blockSignals(True)
                        slider.setValue(slider_value)
                        slider.blockSignals(False)

                        # Update the value label too
                        if hasattr(self, '_eq_value_labels') and i < len(self._eq_value_labels):
                            if db_value >= 0:
                                self._eq_value_labels[i].setText(f"+{db_value}")
                            else:
                                self._eq_value_labels[i].setText(f"{db_value}")

            # Restore preset dropdown if preset_name provided
            if preset_name and hasattr(self, '_eq_preset_combo'):
                # Find the preset in the combo box
                index = self._eq_preset_combo.findText(preset_name)
                if index >= 0:
                    self._eq_preset_combo.blockSignals(True)
                    self._eq_preset_combo.setCurrentIndex(index)
                    self._eq_preset_combo.blockSignals(False)
                    print(f"[App] ✓ Restored EQ preset: {preset_name}")
                else:
                    # Preset not found - set to "Custom"
                    custom_index = self._eq_preset_combo.findText("Custom")
                    if custom_index >= 0:
                        self._eq_preset_combo.blockSignals(True)
                        self._eq_preset_combo.setCurrentIndex(custom_index)
                        self._eq_preset_combo.blockSignals(False)
        except Exception as e:
            print(f"[App] Failed to apply EQ: {e}")

    def _update_led_meters_playback(self, is_playing: bool):
        """Enable/disable LED meter simulation based on playback state.

        Args:
            is_playing: True if audio is playing, False otherwise
        """
        try:
            if not hasattr(self, '_led_meters') or not hasattr(self, '_led_meters_action'):
                return

            # Only animate if menu action is checked AND audio is playing
            meters_visible = self._led_meters_action.isChecked()

            if is_playing and meters_visible:
                # Start simulation for all meters
                for meter in self._led_meters:
                    meter.enable_simulation(True)
                print("[App] LED meters started (playback active)")
            else:
                # Stop simulation
                for meter in self._led_meters:
                    meter.enable_simulation(False)
                if not is_playing:
                    print("[App] LED meters stopped (no playback)")
        except Exception as e:
            print(f"[App] Error updating LED meter playback state: {e}")

    def _toggle_led_meters_from_menu(self):
        """Toggle LED meters from the View menu."""
        # Get state from the menu action
        visible = self._led_meters_action.isChecked()
        self._toggle_led_meters_impl(visible)

    def _toggle_led_meters(self, state):
        """Toggle LED meters from checkbox (legacy, if checkbox still exists)."""
        visible = (state == Qt.Checked)
        self._toggle_led_meters_impl(visible)

    def _toggle_led_meters_impl(self, visible: bool):
        """Implementation of LED meters toggle."""
        try:
            if hasattr(self, '_led_meters'):
                # Check if audio is currently playing
                is_playing = False
                if hasattr(self, 'player') and self.player:
                    from PySide6.QtMultimedia import QMediaPlayer
                    is_playing = (self.player._player.playbackState() == QMediaPlayer.PlayingState)

                for meter in self._led_meters:
                    if visible:
                        # Show meters and enable simulation if playing
                        meter.setVisible(True)
                        meter.show()
                        meter.raise_()
                        if is_playing:
                            meter.enable_simulation(True)
                        meter.update()
                    else:
                        # Hide meters and disable simulation
                        meter.enable_simulation(False)
                        meter.setVisible(False)
                        meter.hide()

                # Force layout update
                if hasattr(self, 'eq_panel'):
                    self.eq_panel.updateGeometry()
                    self.eq_panel.update()

                status = 'visible' if visible else 'hidden'
                print(f"[App] LED meters: {status} (playing={is_playing})")
        except Exception as e:
            print(f"[App] Failed to toggle LED meters: {e}")

    def _toggle_repeat(self):
        """Toggle repeat mode for the current track."""
        self._repeat_enabled = self._repeat_btn.isChecked()
        if self._repeat_enabled:
            self._repeat_btn.setText("🔁 Repeat: On")
            print("[App] Repeat mode enabled")
        else:
            self._repeat_btn.setText("🔁 Repeat: Off")
            print("[App] Repeat mode disabled")

    def _on_eq_label_changed(self, val, idx):
        """Update the value label only - does not apply EQ (prevents crackling during drag)."""
        # Update the value label for this slider
        if hasattr(self, '_eq_value_labels') and idx < len(self._eq_value_labels):
            # Format: +12, +0, -12
            if val >= 0:
                self._eq_value_labels[idx].setText(f"+{val}")
            else:
                self._eq_value_labels[idx].setText(f"{val}")

    def _on_eq_released(self):
        """Apply EQ after a short delay when slider is released - prevents crackling.

        Uses a timer to debounce rapid EQ changes (e.g., when adjusting multiple sliders).
        """
        try:
            # Get current EQ values and convert BeamSlider 0-100 to dB (-12 to +12)
            eq_values = []
            for slider in self._eq_sliders:
                raw_val = slider.value()
                # Check if it's a BeamSlider (0-100 range) or QSlider (-12 to 12 range)
                if hasattr(slider, '__class__') and 'BeamSlider' in slider.__class__.__name__:
                    # BeamSlider: 0-100 → -12 to +12
                    db_val = int(round((raw_val / 100.0) * 24 - 12))
                else:
                    # QSlider: already in -12 to +12 range
                    db_val = raw_val
                eq_values.append(db_val)

            self._pending_eq_values = eq_values

            # Switch to "Custom" preset when user manually adjusts sliders
            if hasattr(self, '_eq_preset_combo'):
                # Block signals to prevent triggering preset change
                self._eq_preset_combo.blockSignals(True)
                self._eq_preset_combo.setCurrentIndex(9)  # "Custom" is last item
                self._eq_preset_combo.blockSignals(False)

            # Restart timer (debounces multiple slider releases)
            self._eq_update_timer.stop()
            self._eq_update_timer.start(300)  # 300ms delay to allow multiple slider adjustments

        except Exception as e:
            print(f"[App] Failed to queue EQ update: {e}")

    def _apply_pending_eq_update(self):
        """Apply the pending EQ update (called by timer)."""
        try:
            if self._pending_eq_values is not None:
                self._apply_eq_to_player(self._pending_eq_values)
                print(f"[App] EQ applied: {self._pending_eq_values} (not saved - click Save button)")
                self._pending_eq_values = None
        except Exception as e:
            print(f"[App] Failed to apply pending EQ: {e}")

    def _on_eq_changed(self):
        """Handle EQ slider changes and apply audio effects.

        NOTE: All 7 sliders are EQ (volume is now a separate horizontal slider).
        Settings are NOT auto-saved - user must click Save button.
        """
        try:
            # Get EQ values from all 7 sliders
            eq_values = [slider.value() for slider in self._eq_sliders]

            # Apply EQ settings to the player
            self._apply_eq_to_player(eq_values)

            # NO AUTO-SAVE - user must click Save button
            print(f"[App] EQ changed: {eq_values} (not saved - click Save button)")
        except Exception as e:
            print(f"[App] Failed to handle EQ change: {e}")

    def _apply_eq_to_player(self, eq_values: list):
        """Apply EQ settings to audio playback.

        Args:
            eq_values: List of dB values from -12 to +12
        """
        try:
            if not hasattr(self, 'player') or not self.player:
                return

            # If EQ is disabled, send flat EQ (all zeros)
            if not self._eq_enabled:
                eq_values = [0] * 7

            # Convert dB values (-12 to +12) to slider values (0 to 200)
            # where 100 = 0dB (flat)
            # Formula: slider_value = (dB_value + 12) * 200 / 24
            # Or simpler: slider_value = 100 + (dB_value * 100 / 12)
            slider_values = []
            for db_val in eq_values:
                # Clamp to -12 to +12 range
                db_val = max(-12, min(12, db_val))
                # Convert to 0-200 range (100 = 0dB)
                slider_val = 100 + (db_val * 100 / 12)
                slider_values.append(int(slider_val))

            # Send EQ values to player
            if hasattr(self.player, 'set_eq_values'):
                self.player.set_eq_values(slider_values)
                if self._eq_enabled:
                    print(f"[App] EQ applied to player: {eq_values} dB → {slider_values} slider")
                else:
                    print(f"[App] EQ disabled - sending flat EQ")

        except Exception as e:
            print(f"[App] Failed to apply EQ to player: {e}")
            import traceback
            traceback.print_exc()

    def _on_eq_toggle(self, checked: bool):
        """Handle EQ enable/disable toggle."""
        try:
            self._eq_enabled = checked
            self._eq_toggle_btn.setText("ON" if checked else "OFF")

            # Apply current EQ settings (will be flat if disabled)
            if hasattr(self, '_eq_sliders'):
                eq_values = []
                for slider in self._eq_sliders:
                    raw_val = slider.value()
                    if hasattr(slider, '__class__') and 'BeamSlider' in slider.__class__.__name__:
                        db_val = int(round((raw_val / 100.0) * 24 - 12))
                    else:
                        db_val = raw_val
                    eq_values.append(db_val)
                self._apply_eq_to_player(eq_values)

            print(f"[App] EQ {'enabled' if checked else 'disabled'}")

        except Exception as e:
            print(f"[App] Failed to toggle EQ: {e}")

    def _on_eq_preset_changed(self, index: int):
        """Handle EQ preset selection."""
        try:
            preset_name = self._eq_preset_combo.currentText()

            # Define EQ presets (dB values for 60Hz, 150Hz, 400Hz, 1kHz, 2.4kHz, 6kHz, 15kHz)
            presets = {
                "Flat (No EQ)": [0, 0, 0, 0, 0, 0, 0],
                "Bass Boost": [6, 4, 2, 0, 0, 0, 0],
                "Treble Boost": [0, 0, 0, 0, 2, 4, 6],
                "Loudness": [4, 2, 0, 0, 0, 2, 3],  # Boost bass and treble for low volume
                "Rock": [4, 2, -1, 0, 1, 3, 4],
                "Jazz": [2, 1, 0, 1, 2, 2, 1],
                "Classical": [0, 0, 0, 0, 0, 2, 3],
                "Electronic": [5, 3, 0, 0, 2, 3, 4],
                "Vocal Forward": [-2, -1, 2, 3, 2, 0, -1],
                "Custom": None  # Don't change sliders for Custom
            }

            eq_values = presets.get(preset_name)

            if eq_values is not None:
                # Update sliders to match preset
                for i, db_val in enumerate(eq_values):
                    if i < len(self._eq_sliders):
                        slider = self._eq_sliders[i]
                        # Convert dB to slider value
                        if hasattr(slider, '__class__') and 'BeamSlider' in slider.__class__.__name__:
                            # BeamSlider: -12 to +12 → 0 to 100
                            slider_val = int(round((db_val + 12) * 100 / 24))
                        else:
                            # QSlider: direct dB value
                            slider_val = db_val
                        slider.setValue(slider_val)

                        # Update label
                        if i < len(self._eq_value_labels):
                            if db_val >= 0:
                                self._eq_value_labels[i].setText(f"+{db_val}")
                            else:
                                self._eq_value_labels[i].setText(f"{db_val}")

                # Apply preset immediately
                self._apply_eq_to_player(eq_values)
                print(f"[App] Applied EQ preset: {preset_name} → {eq_values}")
            else:
                print(f"[App] Selected Custom preset - sliders unchanged")

        except Exception as e:
            print(f"[App] Failed to apply EQ preset: {e}")
            import traceback
            traceback.print_exc()

    def _increment_play_count(self, path: str):
        """Increment play count for a track using the store module."""
        try:
            from . import store
            store.increment_play_count(path)

            # Update the model to refresh the play count display
            self._refresh_play_count_display(path)

            print(f"[App] Incremented play count for: {Path(path).stem}")
        except Exception as e:
            print(f"[App] Failed to increment play count: {e}")

    def _refresh_play_count_display(self, path: str):
        """Refresh the play count display for a specific track."""
        try:
            paths = self.model.paths()
            for row, model_path in enumerate(paths):
                if model_path == path:
                    # Update the play count in the model's internal data
                    from . import store
                    record = store.get_record(path) or {}
                    play_count = record.get('play_count', 0)

                    if row < len(self.model._rows):
                        self.model._rows[row]['play_count'] = play_count
                        # Emit data changed signal to update the display
                        index = self.model.index(row, 3)  # Play Count column
                        self.model.dataChanged.emit(index, index)
                    break
        except Exception as e:
            print(f"[App] Failed to refresh play count display: {e}")

    def _save_analysis_data(self, path: str, analysis_data: dict):
        """Save analysis data to our EQ store with enhanced metadata."""
        try:
            p = self._eq_store_path()
            data = {}
            if p.exists():
                try:
                    data = json.loads(p.read_text())
                except Exception:
                    data = {}

            # Helper function to convert numpy types to native Python types for JSON serialization
            def convert_to_native(obj):
                """Recursively convert numpy types to native Python types."""
                import numpy as np
                if isinstance(obj, (np.integer, np.floating)):
                    return obj.item()
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif isinstance(obj, dict):
                    return {k: convert_to_native(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [convert_to_native(item) for item in obj]
                return obj

            # Store both EQ settings and analysis metadata
            existing_track_data = data.get(path, {})
            data[path] = {
                'eq_settings': convert_to_native(analysis_data.get('gains_db', [0]*7)),
                'suggested_volume': convert_to_native(analysis_data.get('analysis_data', {}).get('suggested_volume')),
                'analysis_data': convert_to_native(analysis_data.get('analysis_data', {})),
                'analyzed_at': str(QDateTime.currentDateTime().toString()),
                'play_count': existing_track_data.get('play_count', 0),  # Don't increment here
                'manual_save': existing_track_data.get('manual_save', False)  # Preserve manual save flag
            }

            p.write_text(json.dumps(data, indent=2))

        except Exception as e:
            print(f"[App] Failed to save analysis data: {e}")

    def _on_position(self, pos_ms: int):
        """Update waveform position display."""
        self._current_position_ms = pos_ms
        mins, secs = divmod(pos_ms // 1000, 60)
        self._current_position = f"{mins:02d}:{secs:02d}"
        # Update waveform with time info
        if hasattr(self, 'waveform'):
            self.waveform.setPosition(pos_ms)

    def _on_duration(self, dur_ms: int):
        """Update waveform duration display."""
        self._current_duration_ms = dur_ms
        mins, secs = divmod(dur_ms // 1000, 60)
        self._current_duration = f"{mins:02d}:{secs:02d}"
        # Update waveform with time info
        if hasattr(self, 'waveform'):
            self.waveform.setDuration(dur_ms)

    def _on_media_status_changed(self, status):
        """Handle media status changes, including repeat mode."""
        from PySide6.QtMultimedia import QMediaPlayer

        if status == QMediaPlayer.EndOfMedia:
            if self._repeat_enabled:
                # Repeat current track
                print(f"[App] Repeat mode: replaying track {self.current_row}")
                self._play_row(self.current_row)
            else:
                # Play next track
                self.on_next()

    # --- EQ persistence helpers ---
    def _eq_store_path(self):
        return Path.home() / '.sidecar_eq_eqs.json'

    def save_eq_for_current_track(self):
        """Save current EQ, volume, and any existing analysis data for the current track."""
        if self.current_row is None:
            raise RuntimeError('No current track to save EQ for')
        paths = self.model.paths()
        if not paths or self.current_row >= len(paths):
            raise RuntimeError('Invalid current row')

        path = paths[self.current_row]

        # Get current EQ slider values and convert from BeamSlider (0-100) to dB (-12 to +12)
        eq_sliders = getattr(self, '_eq_sliders', [])
        eq_values = []
        for slider in eq_sliders:
            slider_val = slider.value()  # 0-100
            # Convert: 0 -> -12, 50 -> 0, 100 -> +12
            db_val = int(round((slider_val / 100.0) * 24 - 12))
            eq_values.append(db_val)

        # Get current volume
        current_volume = self._volume_slider.value() if hasattr(self, '_volume_slider') else 75

        # Get current preset name
        current_preset = self._eq_preset_combo.currentText() if hasattr(self, '_eq_preset_combo') else "Custom"

        # Load existing data (to preserve analysis results)
        p = self._eq_store_path()
        data = {}
        if p.exists():
            try:
                data = json.loads(p.read_text())
            except Exception:
                data = {}

        # Get existing track data or create new
        existing_track_data = data.get(path, {})

        # Update with current manual settings
        track_data = {
            'eq_settings': eq_values,
            'gains_db': eq_values,  # Also store as gains_db for compatibility
            'suggested_volume': current_volume,
            'eq_preset': current_preset,  # Save the preset name
            'analysis_data': existing_track_data.get('analysis_data', {}),  # Preserve existing analysis
            'analyzed_at': existing_track_data.get('analyzed_at', str(QDateTime.currentDateTime().toString())),
            'play_count': existing_track_data.get('play_count', 0),
            'manual_save': True,  # Flag to indicate user manually saved settings
            'saved_at': str(QDateTime.currentDateTime().toString())
        }

        # Update the data and save
        data[path] = track_data
        p.write_text(json.dumps(data, indent=2))

        print(f"[App] ✓ Saved EQ and volume for: {Path(path).stem} (EQ dB: {eq_values}, Vol: {current_volume}%)")
        print(f"[App]   File: {p}")

    def _update_metadata_display(self, path: str):
        """Extract and display track + audio file metadata in the toolbar."""
        try:
            # For streaming URLs (Plex, web), get metadata from queue model instead of file
            if path.startswith(('http://', 'https://')):
                # Get metadata from the current row in the queue
                if self.current_row is not None and self.current_row < len(self.model._rows):
                    track_info = self.model._rows[self.current_row]
                    title = track_info.get('title', 'Unknown')
                    artist = track_info.get('artist', '')
                    album = track_info.get('album', '')
                    source = track_info.get('source', 'streaming')

                    # Build display: "Title - Artist • Album" or "Title • Album" or just "Title"
                    parts = []
                    if artist:
                        parts.append(f"♪ {title} - {artist}")
                    else:
                        parts.append(f"♪ {title}")

                    if album:
                        parts.append(album)

                    # Add source indicator
                    if source == 'plex':
                        parts.append("Plex")
                    else:
                        parts.append("Streaming")

                    self.metadata_label.setText(" • ".join(parts))
                else:
                    self.metadata_label.setText("🌐 Streaming • No metadata available")
                return

            file_path = Path(path)
            if not file_path.exists():
                self.metadata_label.setText("⚠️ File not found")
                return

            # Get file size
            file_size_bytes = file_path.stat().st_size
            if file_size_bytes < 1024:
                size_str = f"{file_size_bytes}B"
            elif file_size_bytes < 1024 * 1024:
                size_str = f"{file_size_bytes / 1024:.1f}KB"
            else:
                size_str = f"{file_size_bytes / (1024 * 1024):.1f}MB"

            # Try to extract audio metadata with mutagen
            try:
                from mutagen import File as MutagenFile
                audio = MutagenFile(path)

                if audio is None:
                    # Fallback - just show filename
                    self.metadata_label.setText(f"♪ {file_path.stem} • {file_path.suffix.upper()[1:]} • {size_str}")
                    return

                # Extract track info (title, artist, album)
                title = None
                artist = None
                album = None

                if hasattr(audio, 'tags') and audio.tags:
                    tags = audio.tags
                    # Try common tag names
                    for key in ['TIT2', 'title', '©nam', 'TITLE']:
                        if key in tags:
                            val = tags[key]
                            title = str(val[0]) if isinstance(val, list) else str(val)
                            break
                    for key in ['TPE1', 'artist', '©ART', 'ARTIST', 'TPE2', 'albumartist']:
                        if key in tags:
                            val = tags[key]
                            artist = str(val[0]) if isinstance(val, list) else str(val)
                            break
                    for key in ['TALB', 'album', '©alb', 'ALBUM']:
                        if key in tags:
                            val = tags[key]
                            album = str(val[0]) if isinstance(val, list) else str(val)
                            break

                # Fallback to filename for title
                if not title:
                    title = file_path.stem

                # Build the NOW PLAYING display: "Title - Artist • Album • FORMAT • details"
                parts = []

                # Song info first (most important)
                if artist:
                    parts.append(f"♪ {title} - {artist}")
                else:
                    parts.append(f"♪ {title}")

                if album:
                    parts.append(album)

                # Technical details
                format_name = file_path.suffix.upper()[1:]  # .flac -> FLAC
                sample_rate = getattr(audio.info, 'sample_rate', None)
                bits_per_sample = getattr(audio.info, 'bits_per_sample', None)
                bitrate = getattr(audio.info, 'bitrate', None)
                channels = getattr(audio.info, 'channels', None)

                # Format string
                tech_parts = [format_name]

                if bits_per_sample:
                    # Lossless format
                    tech_parts.append(f"{sample_rate / 1000:.1f}kHz/{bits_per_sample}bit")
                elif bitrate:
                    # Lossy format
                    tech_parts.append(f"{bitrate // 1000}kbps")

                if channels == 2:
                    tech_parts.append("Stereo")
                elif channels == 1:
                    tech_parts.append("Mono")

                tech_parts.append(size_str)

                parts.append(" ".join(tech_parts))

                # Final display text
                display_text = " • ".join(parts)
                self.metadata_label.setText(display_text)
                self.metadata_label.setToolTip(display_text)  # Full text on hover

            except Exception as e:
                # Fallback if mutagen fails
                self.metadata_label.setText(f"♪ {file_path.stem} • {file_path.suffix.upper()[1:]} • {size_str}")
                print(f"[Metadata] Could not extract audio info: {e}")

        except Exception as e:
            self.metadata_label.setText("⚠️ Error reading metadata")
            print(f"[Metadata] Error: {e}")

    def load_eq_for_track(self, path):
        """Load EQ and volume data for a track. Returns dict with eq_settings/gains_db and volume or None."""
        p = self._eq_store_path()
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text())
        except Exception:
            return None

        track_data = data.get(path)
        if not track_data:
            return None

        # Handle both old format (just values) and new format (dict with metadata)
        if isinstance(track_data, list):
            # Old format - just EQ values (assume they're in dB)
            return {
                'gains_db': track_data,
                'eq_settings': track_data,
                'suggested_volume': None
            }
        elif isinstance(track_data, dict):
            # New format - with metadata
            # Return the dict so caller can use the data
            return track_data
        else:
            return None

    def _store_analysis_for_video(self, video_path: str, analysis_data: dict):
        """Store analysis data for a video file using the original video path as key."""
        try:
            p = self._eq_store_path()
            data = {}
            if p.exists():
                try:
                    data = json.loads(p.read_text())
                except Exception:
                    data = {}

            # Store under video file path with analysis from extracted audio
            track_data = {
                'eq_settings': analysis_data.get('gains_db', [0]*7),
                'suggested_volume': analysis_data.get('suggested_volume', 75),
                'analysis_data': analysis_data,
                'analyzed_at': str(QDateTime.currentDateTime().toString()),
                'play_count': data.get(video_path, {}).get('play_count', 0),
                'source_type': 'video'
            }

            data[video_path] = track_data
            p.write_text(json.dumps(data, indent=2))

            print(f"[App] Stored video analysis for: {Path(video_path).stem}")

        except Exception as e:
            print(f"[App] Failed to store video analysis: {e}")

    def closeEvent(self, event):
        """Clean up background analysis and save queue state when closing the application."""
        try:
            # Save queue state before closing
            self._save_queue_state()

            # Clean up background analysis
            if self._analysis_worker and self._analysis_worker.isRunning():
                print("[App] Stopping background analysis...")
                self._analysis_worker.stop_analysis()
                self._analysis_worker.wait(2000)  # Wait up to 2 seconds
        except Exception as e:
            print(f"[App] Error during cleanup: {e}")

        event.accept()

    def _get_queue_state_file(self):
        """Get the path to current.json (the active queue/playlist)."""
        playlists_dir = self._get_playlists_dir()
        return playlists_dir / "current.json"

    def _load_panel_states(self):
        """Load saved collapse states for all panels.

        Default behavior: All panels open (expanded) on startup.
        This prevents weird UI issues from launching with everything collapsed.
        """
        try:
            # Always start with all panels expanded for best UX
            # (Saved states can cause issues if everything is collapsed)
            if hasattr(self, 'queue_panel'):
                self.queue_panel.set_collapsed(False)
            if hasattr(self, 'eq_panel'):
                self.eq_panel.set_collapsed(False)
            if hasattr(self, 'search_panel'):
                self.search_panel.set_collapsed(False)
            if hasattr(self, 'playlist_panel'):
                self.playlist_panel.set_collapsed(False)

            # Set initial stretch factors so last visible panel fills space
            self._update_panel_stretch_factors()

            print("[App] Initialized panels: all expanded (default)")
        except Exception as e:
            print(f"[App] Failed to load panel states: {e}")

    def _update_panel_stretch_factors(self):
        """Update stretch factors so the last visible panel fills remaining space.

        The last expanded (visible) panel should have stretch=1 to fill all available space.
        All collapsed panels should have stretch=0 and be completely minimized.
        """
        try:
            from PySide6.QtWidgets import QSizePolicy
            from .collapsible_panel import CollapsiblePanel

            if not hasattr(self, '_central_layout'):
                return

            # Get all panels in order
            panels = []
            if hasattr(self, 'queue_panel'):
                panels.append(self.queue_panel)
            if hasattr(self, 'eq_panel'):
                panels.append(self.eq_panel)
            if hasattr(self, 'search_panel'):
                panels.append(self.search_panel)
            if hasattr(self, 'playlist_panel'):
                panels.append(self.playlist_panel)

            # Find the last visible (non-collapsed) panel
            last_visible = None
            for panel in reversed(panels):
                if panel.isVisible() and not panel.is_collapsed:
                    last_visible = panel
                    break

            # Update stretch factors for all panels
            layout = self._central_layout
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and item.widget() in panels:
                    panel = item.widget()

                    # Collapsed panels: stretch=0, Fixed size policy, minimal height
                    if not panel.isVisible() or panel.is_collapsed:
                        layout.setStretch(i, 0)
                        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                        panel.updateGeometry()
                    # Last visible panel: stretch based on preset
                    elif panel is last_visible:
                        preset = getattr(self, "_current_layout_preset", None)
                        if preset == "eq_only" and panel is getattr(self, 'eq_panel', None):
                            # In EQ-only mode, keep EQ sized-to-content; do NOT stretch
                            layout.setStretch(i, 0)
                            if not getattr(panel, "_lock_content_height", False):
                                panel.lock_content_height(True)
                            panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
                            if isinstance(panel, CollapsiblePanel):
                                panel.set_content_stretch(False)
                            panel.updateGeometry()
                        else:
                            # Default behavior: last visible fills space
                            layout.setStretch(i, 1)
                            # Allow this panel to expand fully
                            if getattr(panel, "_lock_content_height", False):
                                panel.lock_content_height(False)
                            panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                            # Ensure internal content area also stretches
                            if isinstance(panel, CollapsiblePanel):
                                panel.set_content_stretch(True)
                            # If this is the queue panel, allow the table to expand vertically
                            try:
                                if panel is getattr(self, 'queue_panel', None) and getattr(self, 'table', None) is not None:
                                    self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                            except Exception:
                                pass
                            panel.updateGeometry()
                    # Other visible panels: stretch=0, size to content
                    else:
                        layout.setStretch(i, 0)
                        # Make these panels size-to-content and not steal space
                        if not getattr(panel, "_lock_content_height", False):
                            panel.lock_content_height(True)
                        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
                        # If queue panel is not the last visible, keep the table sizing to content
                        try:
                            if panel is getattr(self, 'queue_panel', None) and getattr(self, 'table', None) is not None:
                                self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
                        except Exception:
                            pass
                        panel.updateGeometry()

            print(f"[App] Updated panel stretch factors, last visible: {last_visible.title if last_visible else 'none'}")
        except Exception as e:
            print(f"[App] Failed to update panel stretch factors: {e}")

    def _save_panel_states(self):
        """Save current collapse states for all panels."""
        try:
            states = {}
            if hasattr(self, 'queue_panel'):
                states['queue'] = self.queue_panel.is_collapsed
            if hasattr(self, 'eq_panel'):
                states['eq'] = self.eq_panel.is_collapsed
            if hasattr(self, 'search_panel'):
                states['search'] = self.search_panel.is_collapsed
            if hasattr(self, 'playlist_panel'):
                states['playlist'] = self.playlist_panel.is_collapsed
            store.set_record("panel_states", states)
            print(f"[App] Saved panel states: {states}")
        except Exception as e:
            print(f"[App] Failed to save panel states: {e}")

    def _apply_layout_preset(self, preset: str):
        """Apply a layout preset (workflow mode).

        Args:
            preset: One of "queue_eq", "queue_only", "eq_only", "artist_info"
                - queue_eq: Queue and EQ panels only (default, no artist info, no playlists)
                - queue_only: Just the queue panel
                - eq_only: EQ and Playlists panels
                - artist_info: Artist info panel only (full height)
        """
        try:
            # Remember current preset for stretch logic nuances
            self._current_layout_preset = preset

            if preset == "queue_only":
                # Queue + Playlists
                self.queue_panel.set_collapsed(False)
                self.eq_panel.set_collapsed(True)
                self.search_panel.set_collapsed(True)
                if hasattr(self, 'playlist_panel'):
                    self.playlist_panel.set_collapsed(False)
                # Hide other panel headers entirely in this preset
                self.queue_panel.setVisible(True)
                self.eq_panel.setVisible(False)
                self.search_panel.setVisible(False)
                if hasattr(self, 'playlist_panel'):
                    self.playlist_panel.setVisible(True)
                # Queue should be allowed to expand fully
                try:
                    self.queue_panel.lock_content_height(False)
                    self.queue_panel.set_content_stretch(True)
                    if getattr(self, 'table', None) is not None:
                        from PySide6.QtWidgets import QSizePolicy
                        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                except Exception:
                    pass
                print("[App] Applied Queue + Playlists layout")

            elif preset == "eq_only":
                # EQ Only
                self.queue_panel.set_collapsed(True)
                self.eq_panel.set_collapsed(False)
                self.search_panel.set_collapsed(True)
                if hasattr(self, 'playlist_panel'):
                    self.playlist_panel.set_collapsed(True)
                self.queue_panel.setVisible(False)
                self.eq_panel.setVisible(True)
                self.search_panel.setVisible(False)
                if hasattr(self, 'playlist_panel'):
                    self.playlist_panel.setVisible(False)
                # Keep EQ sized-to-content to avoid overly tall sliders
                try:
                    self.eq_panel.lock_content_height(True)
                    self.eq_panel.set_content_stretch(False)
                    # Reset alignment to default
                    if hasattr(self, '_central_layout'):
                        self._central_layout.setAlignment(Qt.AlignmentFlag(0))
                except Exception:
                    pass
                print("[App] Applied EQ Only layout")

            elif preset == "artist_info":
                # Artist Info View - Just the artist info panel at full height
                self.queue_panel.set_collapsed(True)
                self.eq_panel.set_collapsed(True)
                self.search_panel.set_collapsed(False)
                if hasattr(self, 'playlist_panel'):
                    self.playlist_panel.set_collapsed(True)
                self.queue_panel.setVisible(False)
                self.eq_panel.setVisible(False)
                self.search_panel.setVisible(True)
                if hasattr(self, 'playlist_panel'):
                    self.playlist_panel.setVisible(False)

                # Make artist info panel size to content (like EQ panel)
                try:
                    self.search_panel.lock_content_height(True)
                    self.search_panel.set_content_stretch(False)
                    # Reset alignment to default (like queue_eq layout) instead of AlignTop
                    if hasattr(self, '_central_layout'):
                        self._central_layout.setAlignment(Qt.AlignmentFlag(0))
                except Exception as e:
                    print(f"[App] Error configuring Artist Info layout: {e}")

                print("[App] Applied Artist Info layout (artist info only)")

            elif preset == "queue_eq":
                # Queue + EQ View - Queue and EQ panels only (no search, no playlists)
                self.queue_panel.set_collapsed(False)
                self.eq_panel.set_collapsed(False)
                self.search_panel.set_collapsed(True)
                if hasattr(self, 'playlist_panel'):
                    self.playlist_panel.set_collapsed(True)
                self.queue_panel.setVisible(True)
                self.eq_panel.setVisible(True)
                self.search_panel.setVisible(False)
                if hasattr(self, 'playlist_panel'):
                    self.playlist_panel.setVisible(False)
                try:
                    # Panels size to content
                    self.queue_panel.lock_content_height(True)
                    self.queue_panel.set_content_stretch(False)
                    self.eq_panel.lock_content_height(True)
                    self.eq_panel.set_content_stretch(False)
                    # Reset alignment to default
                    if hasattr(self, '_central_layout'):
                        self._central_layout.setAlignment(Qt.AlignmentFlag(0))
                except Exception:
                    pass
                print("[App] Applied Queue + EQ layout (no artist info)")

            else:
                # Unknown preset - default to queue_eq
                print(f"[App] Warning: Unknown layout preset '{preset}', using queue_eq")
                self._apply_layout_preset("queue_eq")
                return

            # Update stretch factors so last visible panel fills space
            self._update_panel_stretch_factors()
            # Snap window height to visible content so there's no extra padding
            QTimer.singleShot(0, self._resize_to_fit_visible_panels)

            # Save the panel states
            self._save_panel_states()

        except Exception as e:
            print(f"[App] Failed to apply layout preset: {e}")

    def _show_artist_info_panel(self):
        """Convenience action to reveal the Now Playing panel."""
        try:
            self._apply_layout_preset("artist_info")
            if hasattr(self, 'search_panel'):
                self.search_panel.setVisible(True)
                if getattr(self.search_panel, 'is_collapsed', False):
                    self.search_panel.set_collapsed(False)
        except Exception as e:
            print(f"[App] Failed to show Now Playing panel: {e}")

    def _resize_to_fit_visible_panels(self):
        """Resize the fixed-height window to fit the toolbar + visible panels + status bar.

        Keeps the non-resizable behavior but avoids large empty space when fewer panels are visible
        (e.g., EQ Only or Search & Queue). Width remains unchanged.
        """
        try:
            # Activate layouts to get accurate size hints
            try:
                if self.centralWidget() and self.centralWidget().layout():
                    self.centralWidget().layout().activate()
            except Exception:
                pass

            central = self.centralWidget()
            ch = central.sizeHint().height() if central is not None else 0
            mbh = self.menuBar().height() if self.menuBar() else 0
            tb = getattr(self, 'toolbar', None)
            tbh = tb.height() if tb is not None else 0
            sb = self.statusBar() if hasattr(self, 'statusBar') else None
            sbh = sb.height() if sb is not None else 0

            # Base gaps: minor padding between sections
            extra = 8
            new_h = mbh + tbh + ch + sbh + extra

            # Clamp to sensible range - restore 480px min for Queue Only
            new_h = max(480, min(new_h, 1000))

            # Preserve current width (we keep window non-resizable)
            new_w = self.width()
            self.setFixedSize(new_w, new_h)
        except Exception as e:
            print(f"[App] Failed to resize-to-fit: {e}")

    # =========================
    # Rack Mode (experimental)
    # =========================
    def _build_rack_ui(self):
        """Prepare the Rack Mode container and pages. Not shown until enabled."""
        if getattr(self, "_rack_container", None) is not None:
            return
        from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QFrame

        self._rack_container = QWidget()
        root = QHBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._rack_view = RackView()
        root.addWidget(self._rack_view)

        self._rack_content_frame = QFrame()
        self._rack_content_frame.setObjectName("RackContentFrame")
        self._rack_content_frame.setStyleSheet(
            """
            QFrame#RackContentFrame {
                background: #141414;
            }
            """
        )
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        self._rack_content_frame.setLayout(content_layout)
        root.addWidget(self._rack_content_frame, 1)

        # Map rack modules to layout presets so buttons behave like the old dropdown
        self._rack_module_presets = {
            "mix": "queue_eq",
            "queue": "queue_only",
            "eq": "eq_only",
            "search": "artist_info",
        }
        for module_id, title in [
            ("mix", "Queue + EQ"),
            ("queue", "Queue + Playlists"),
            ("eq", "EQ Only"),
            ("search", "Artist Info"),
        ]:
            self._rack_view.add_module(module_id, title)
        self._preset_to_rack_module = {preset: module for module, preset in self._rack_module_presets.items()}
        self._rack_view.module_selected.connect(self._on_rack_module_selected)

        self._rack_container.setLayout(root)

    def _on_rack_module_selected(self, page_id: str):
        try:
            preset = getattr(self, "_rack_module_presets", {}).get(page_id)
            if preset:
                self._apply_layout_preset(preset)
        except Exception:
            pass

    def _set_rack_mode(self, enabled: bool):
        """Toggle Rack Mode and swap central widget accordingly."""
        if enabled == getattr(self, "_rack_enabled", False):
            return
        self._rack_enabled = enabled
        if enabled:
            self._enter_rack_mode()
        else:
            self._exit_rack_mode()
        # keep menu state in sync
        if hasattr(self, "_act_rack_mode") and self._act_rack_mode.isChecked() != enabled:
            self._act_rack_mode.setChecked(enabled)

    def _enter_rack_mode(self):
        """Reparent key widgets into Rack pages and show rack container."""
        try:
            if getattr(self, "_rack_container", None) is None:
                self._build_rack_ui()

            if not getattr(self, "_rack_content_frame", None):
                return

            # Take whatever central widget is active (classic layout) and move it into the rack content area
            current_central = self.takeCentralWidget()
            if current_central is None:
                current_central = getattr(self, "_classic_central", None)
            if current_central is None:
                return

            self._classic_central = current_central

            content_layout = self._rack_content_frame.layout()
            while content_layout.count():
                item = content_layout.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.setParent(None)

            current_central.setParent(self._rack_content_frame)
            content_layout.addWidget(current_central)

            self.setCentralWidget(self._rack_container)

            # Highlight the rack button that matches the current preset
            current_preset = getattr(self, "_current_layout_preset", "queue_eq")
            module = getattr(self, "_preset_to_rack_module", {}).get(current_preset)
            if module:
                self._rack_view.set_active(module)
        except Exception as e:
            print(f"[SidecarEQ] Enter Rack Mode failed: {e}")

    def _exit_rack_mode(self):
        """Restore classic central layout and reparent widgets back."""
        try:
            if getattr(self, "_classic_central", None) is None:
                return

            if self.centralWidget() is self._rack_container:
                self.takeCentralWidget()

            if getattr(self, "_rack_content_frame", None):
                layout = self._rack_content_frame.layout()
                if layout is not None:
                    layout.removeWidget(self._classic_central)

            self._classic_central.setParent(None)
            self.setCentralWidget(self._classic_central)
        except Exception as e:
            print(f"[SidecarEQ] Exit Rack Mode failed: {e}")

    def _on_layout_preset_changed(self, index: int):
        """Handle layout preset dropdown selection.

        Args:
            index: 0=Queue + EQ, 1=Queue + Playlists, 2=EQ Only, 3=Artist Info
        """
        # Map dropdown indices to preset names
        presets = ["queue_eq", "queue_only", "eq_only", "artist_info"]
        if 0 <= index < len(presets):
            self._apply_layout_preset(presets[index])

    def _on_panel_toggled(self):
        """Handle panel collapse/expand - save state and update last visible panel stretch."""
        # Save the state
        self._save_panel_states()

        # Update stretch factors so last visible panel fills space
        self._update_panel_stretch_factors()

        # Refresh panel geometry
        QTimer.singleShot(0, self._resize_to_fit_visible_panels)
        QTimer.singleShot(300, lambda: self._sync_queue_panel_height())

    def _save_queue_state(self):
        """Save the current queue state to disk."""
        try:
            if self.model:
                queue_file = self._get_queue_state_file()
                self.model.save_queue_state(queue_file)
        except Exception as e:
            print(f"[App] Failed to save queue state: {e}")

    def _load_queue_state(self):
        """Load the saved queue state from current.json and set as active playlist."""
        try:
            if self.model:
                queue_file = self._get_queue_state_file()
                self.model.load_queue_state(queue_file)
                # Set current.json as the active playlist for auto-save
                self.active_playlist_path = str(queue_file)
                print(f"[App] Loaded current.json as active playlist")
        except Exception as e:
            print(f"[App] Failed to load queue state: {e}")

def main():
    """App entry point: configure environment, create QApplication, show MainWindow."""
    try:
        load_dotenv()
    except Exception:
        pass

    # High DPI support is automatic in Qt6, no need to set attributes
    # (AA_EnableHighDpiScaling and AA_UseHighDpiPixmaps are deprecated in Qt 6.10)

    app = QApplication.instance() or QApplication(sys.argv)

    # Fusion dark palette
    try:
        app.setStyle("Fusion")
        from PySide6.QtGui import QPalette, QColor
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(45, 45, 45))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Highlight, QColor(64, 128, 255))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        app.setPalette(palette)
    except Exception:
        pass

    w = MainWindow()

    # Map hardware volume keys and +/- to control the app volume by 1 unit
    def _vol_key_filter(obj, event):
        try:
            from PySide6.QtCore import QEvent
            if event.type() == QEvent.KeyPress:
                if event.key() in (Qt.Key_VolumeUp, Qt.Key_Plus, Qt.Key_Equal):
                    # Find volume spinner and bump +1
                    try:
                        # We stored it on window during side panel build
                        if hasattr(w, '_volume_slider'):
                            w._volume_slider.setValue(w._volume_slider.value() + 1)
                            return True
                    except Exception:
                        pass
                if event.key() in (Qt.Key_VolumeDown, Qt.Key_Minus, Qt.Key_Underscore):
                    try:
                        if hasattr(w, '_volume_slider'):
                            w._volume_slider.setValue(w._volume_slider.value() - 1)
                            return True
                    except Exception:
                        pass
        except Exception:
            pass
        return False

    # Proper QObject-based event filter so installEventFilter receives a QObject
    class VolFilter(QObject):
        def __init__(self, handler, parent=None):
            super().__init__(parent)
            self._handler = handler
        def eventFilter(self, obj, event):
            try:
                return bool(self._handler(obj, event))
            except Exception:
                return False

    _vf = VolFilter(_vol_key_filter, app)
    app.installEventFilter(_vf)
    # Keep a Python-side ref so it isn't GC'd while the app runs
    # Store reference on the app instance to avoid GC in a type-safe way
    # Use object.__setattr__ to avoid type checker complaints and keep styling tools happy
    try:
        object.__setattr__(app, "_vol_filter", _vf)  # type: ignore[attr-defined]
    except Exception:
        app.__dict__["_vol_filter"] = _vf  # type: ignore[attr-defined]
    w.show()

    # Calculate correct window height based on visible panels
    QTimer.singleShot(0, w._resize_to_fit_visible_panels)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
