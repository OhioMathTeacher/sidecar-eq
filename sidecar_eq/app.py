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
from dotenv import load_dotenv
from plexapi.server import PlexServer
from PySide6.QtCore import QDateTime, QModelIndex, QObject, QSize, Qt, QThread, QTimer, Signal, QPoint
from PySide6.QtGui import QAction, QIcon, QKeyEvent, QKeySequence, QPainter, QPixmap
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
    QWidget,
)

# Local imports
from . import playlist, store
from .collapsible_panel import CollapsiblePanel
from .indexer import LibraryIndexer
from .player import Player
from .queue_model import QueueModel
from .plex_helpers import get_playlist_titles, get_tracks_for_playlist
from .search import SearchBar
from .ui import IconButton, KnobWidget, QueueTableView, SnapKnobWidget, WaveformProgress
from .workers import BackgroundAnalysisWorker

# Media file extensions
AUDIO_EXTS = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".flv", ".m4v", ".webm", ".wmv", ".3gp"}
MEDIA_EXTS = AUDIO_EXTS | VIDEO_EXTS


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

        # Library indexer
        try:
            self.indexer = LibraryIndexer()
        except Exception as e:
            print(f"[SidecarEQ] Indexer failed: {e}")
            self.indexer = None

        # Search bar
        try:
            self.search_bar = SearchBar()
            self.search_bar.result_selected.connect(self._on_search_result_selected)
            self.search_bar.command_entered.connect(self._on_command_entered)
            # Connect to indexer
            if self.indexer:
                self.search_bar.set_index(self.indexer.get_index())
        except Exception as e:
            print(f"[SidecarEQ] Search bar failed: {e}")
            self.search_bar = None

        # Model / table
        try:
            self.model = QueueModel()
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
            
            # Configure columns with custom header for column management
            custom_header = CustomTableHeader(Qt.Horizontal, self.table)
            self.table.setHorizontalHeader(custom_header)
            
            header = self.table.horizontalHeader()
            header.setStretchLastSection(True)  # Stretch last column to fill space
            
            # Column resize modes (15 columns total now: Lookup + Status + 13 data columns)
            header.setSectionResizeMode(0, QHeaderView.Fixed)  # Lookup (globe) - fixed width
            header.setSectionResizeMode(1, QHeaderView.Fixed)  # Status (play indicator) - fixed width
            for col in range(2, 15):  # All other columns user-resizable
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
            
            # Enable word wrap in headers for better text fit
            header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            
            # Hide vertical header (row numbers) for cleaner look
            self.table.verticalHeader().setVisible(False)
            
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
            # - Queue table (top, collapsible panel)
            # - Waveform/EQ (middle, collapsible panel)
            # - Search bar (bottom, collapsible panel)
            # ACCORDION STYLE: Window height changes when panels collapse/expand
            from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QSplitter
            central_widget = QWidget()
            central_layout = QVBoxLayout()
            central_layout.setContentsMargins(0, 0, 0, 0)
            central_layout.setSpacing(0)
            
            # Panel 1: Song Queue & Metadata (collapsible, accordion style)
            self.queue_panel = CollapsiblePanel("Song Queue & Metadata")
            self.queue_panel.set_content(self.table)
            
            # Make table expand to fill available space
            from PySide6.QtWidgets import QSizePolicy
            self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.table.setMinimumHeight(200)  # Minimum height when expanded
            
            central_layout.addWidget(self.queue_panel, stretch=1)  # Add stretch for vertical resizing
            
            # Panel 2: EQ & Waveform (collapsible, accordion style) - will be populated in _build_side_panel
            self.eq_panel = CollapsiblePanel("EQ & Waveform")
            self._waveform_eq_splitter = None  # Will be created in _build_side_panel
            central_layout.addWidget(self.eq_panel)  # NO stretch - natural size
            
            # Panel 3: Search (collapsible, accordion style)
            self.search_panel = CollapsiblePanel("Artist Information & Search")
            if self.search_bar:
                self.search_bar.setMinimumHeight(250)  # Minimum height for split search view
                self.search_panel.set_content(self.search_bar)
            central_layout.addWidget(self.search_panel)  # NO stretch - natural size
            
            # Load saved collapse states
            self._load_panel_states()
            
            central_widget.setLayout(central_layout)
            self.setCentralWidget(central_widget)
            
            # Load saved queue state
            self._load_queue_state()
            
            # Auto-refresh metadata for existing queue items (background operation)
            if self.model and hasattr(self.model, '_rows') and len(self.model._rows) > 0:
                QTimer.singleShot(500, self._auto_refresh_metadata)
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

        # Wire signals last (player and widgets should exist)
        try:
            self._wire_signals()
        except Exception:
            pass

        self.setWindowTitle('Sidecar EQ')
        self.resize(1000, 640)
        
        # Apply clean dark theme with subtle accents
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
            }
            QTableView QHeaderView::section {
                background: #2d2d2d;
                color: #c0c0c0;
                font-weight: bold;
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
    
    def showEvent(self, event):
        """Called when the window is shown. Auto-select first row if queue has items."""
        super().showEvent(event)
        
        # Only do this once on first show
        if not hasattr(self, '_initial_selection_done'):
            self._initial_selection_done = True
            
            # Use a timer to ensure everything is fully initialized
            QTimer.singleShot(100, self._do_initial_selection)
    
    def _do_initial_selection(self):
        """Select and display info for the first track in the queue (without playing)."""
        try:
            if self.model.rowCount() > 0:
                # Select the first row in the table
                first_index = self.model.index(0, 2)  # Column 2 is Title
                self.table.setCurrentIndex(first_index)
                self.table.selectRow(0)
                
                # Trigger auto-search to show info in the search panel
                paths = self.model.paths()
                if paths and self.search_bar:
                    path = paths[0]
                    row_data = self.model.get_row_data(0)
                    if row_data:
                        title = row_data.get('title', '')
                        artist = row_data.get('artist', '')
                        if title and artist:
                            self.search_bar.search_for_track(artist, title)
                            print(f"[App] Auto-selected first track: {artist} - {title}")
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
        """Status bar for messages only (waveform now in split panel)."""
        sb = self.statusBar()
        sb.showMessage("Ready")


    def _wire_signals(self):
        # play-end → next track
        self.player.mediaStatusChanged.connect(
            lambda st: st == QMediaPlayer.EndOfMedia and self.on_next()
        )
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

        # Play/Pause button - HIDDEN (use radio buttons in queue instead)
        # Keep reference for internal play state tracking
        self.play_btn = IconButton(
            "icons/play.svg",
            "icons/play_hover.svg",
            "icons/play_active.svg",
            tooltip="Play / Pause (Space)"
        )
        self.play_btn.clicked.connect(self.on_play)
        self.play_btn.setShortcut(QKeySequence(Qt.Key_Space))
        self.play_btn.hide()  # Hidden - click radio buttons to play
        # tb.addWidget(self.play_btn)  # Commented out - not in toolbar

        # Stop button - HIDDEN (use radio buttons in queue instead)
        # stop_btn = IconButton(
        #     "icons/stop.svg",
        #     "icons/stop_hover.svg",
        #     "icons/stop_pressed.svg",
        #     tooltip="Stop (resets position)"
        # )
        # stop_btn.clicked.connect(self.on_stop)
        # tb.addWidget(stop_btn)

        # Add Songs button (download icon)
        # tb.addSeparator()  # No separator needed if play/stop hidden
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
        # LCD-style display inspired by retro alarm clocks and digital displays
        tb.addSeparator()
        self.metadata_label = QLabel("♪ No track loaded")
        # Use a flatter background that matches the main window to remove
        # the heavy shaded bounding box and make the display look cleaner.
        self.metadata_label.setStyleSheet("""
            QLabel {
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
        # Make it expand to fill available space (but allow text truncation with ...)
        from PySide6.QtWidgets import QSizePolicy as _SP
        self.metadata_label.setSizePolicy(_SP.Expanding, _SP.Preferred)
        self.metadata_label.setMinimumWidth(200)
        # Enable text elision (show ... for long text)
        from PySide6.QtCore import Qt as _Qt
        self.metadata_label.setTextFormat(_Qt.PlainText)
        tb.addWidget(self.metadata_label)
        
        # NOTE: Removed Save EQ button - EQ auto-saves on change now
    print("[SidecarEQ] Toolbar ready")

    def _build_side_panel(self):
        """
        Build the waveform/EQ split panel.
        This creates a horizontal split: Waveform+Volume (left 50%) | Playback+EQ (right 50%)
        The panel is inserted into the central layout between the queue table and search bar.
        """
        from PySide6.QtWidgets import (
            QWidget, QVBoxLayout, QLabel, QHBoxLayout, QSplitter
        )

        # Create horizontal splitter for waveform+volume | playback+EQ
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)  # Prevent collapsing panels
        
        # === LEFT PANEL: Waveform + Volume Control ===
        waveform_panel = QWidget()
        waveform_layout = QVBoxLayout()
        waveform_layout.setContentsMargins(8, 8, 8, 8)
        waveform_layout.setSpacing(8)
        
        # Create waveform widget (moved from status bar)
        from .ui import WaveformProgress
        self.waveform = WaveformProgress()
        self.waveform.setMinimumHeight(150)  # Taller than before (was 70px)
        self.waveform.setMaximumHeight(200)
        waveform_layout.addWidget(self.waveform)

        # Volume control below waveform (horizontal BeamSlider with red glow)
        volume_container = QWidget()
        volume_container.setStyleSheet("background: transparent; border: none;")
        volume_sub_layout = QVBoxLayout()
        volume_sub_layout.setContentsMargins(0, 0, 0, 0)
        volume_sub_layout.setSpacing(0)  # Minimal spacing
        
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
        waveform_layout.addWidget(volume_container)

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
        
        # === PLAYBACK CONTROLS at top (Rate, Treble Boost, etc.) ===
        playback_container = QWidget()
        playback_container.setStyleSheet("background: transparent; border: none;")
        playback_layout = QVBoxLayout()
        playback_layout.setContentsMargins(0, 0, 0, 0)
        playback_layout.setSpacing(2)
        
        # TODO: Add playback rate control, treble boost, loudness, etc.
        # Placeholder container for future controls - no labels yet to save vertical space
        
        playback_container.setLayout(playback_layout)
        eq_main_layout.addWidget(playback_container)
        
        # EQ sliders container (7 sliders only - no volume)
        from PySide6.QtWidgets import QHBoxLayout as HB, QCheckBox
        eq_x_offset = 12
        
        # LED meter toggle checkbox with Save button on the right
        led_checkbox_layout = QHBoxLayout()
        led_checkbox_layout.setContentsMargins(eq_x_offset, 0, eq_x_offset, 8)
        self._led_meter_checkbox = QCheckBox("Show LED Meters")
        self._led_meter_checkbox.setChecked(True)  # On by default
        self._led_meter_checkbox.setStyleSheet("""
            QCheckBox {
                color: #808080;
                font-size: 9px;
                font-family: 'Helvetica Neue', 'Helvetica', 'Arial Narrow', 'Arial', sans-serif;
                background: transparent;
                border: none;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                background: #1a1a1a;
                border: 1px solid #3a3a3a;
                border-radius: 2px;
            }
            QCheckBox::indicator:checked {
                background: #4d88ff;
                border: 1px solid #6699ff;
            }
        """)
        self._led_meter_checkbox.stateChanged.connect(self._toggle_led_meters)
        led_checkbox_layout.addWidget(self._led_meter_checkbox)
        led_checkbox_layout.addStretch()
        
        # Save Settings button (pushbutton.svg icon) - compact, inline
        self._save_settings_btn = QPushButton()
        self._save_settings_btn.setToolTip("Save EQ Settings")
        
        # Load the pushbutton.svg icon
        from pathlib import Path
        icon_path = Path(__file__).parent.parent / "icons" / "pushbutton.svg"
        if icon_path.exists():
            from PySide6.QtGui import QIcon
            from PySide6.QtCore import QSize
            self._save_settings_btn.setIcon(QIcon(str(icon_path)))
            self._save_settings_btn.setIconSize(QSize(32, 32))
        
        self._save_settings_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                padding: 0px;
                min-width: 32px;
                max-width: 32px;
                min-height: 32px;
                max-height: 32px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 10);
                border-radius: 16px;
            }
            QPushButton:pressed {
                background: rgba(0, 0, 0, 20);
                border-radius: 16px;
            }
            QPushButton:disabled {
                opacity: 0.3;
            }
        """)
        self._save_settings_btn.setEnabled(False)
        self._save_settings_btn.clicked.connect(self._on_save_settings_clicked)
        led_checkbox_layout.addWidget(self._save_settings_btn)
        
        eq_main_layout.addLayout(led_checkbox_layout)
        
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
                # Connect BeamSlider 0..100 -> -12..12 for label updates
                s.valueChanged.connect(lambda v, idx=i: self._on_eq_changed_with_label(int(round((v/100.0)*24 - 12)), idx))
                s.setFixedHeight(120)
            except Exception:
                # Fallback to older QSlider style if BeamSlider import fails
                s = QSlider(Qt.Vertical)
                s.setRange(-12, 12)
                s.setValue(0)
                s.setStyleSheet(slider_css_blue_vu)
                s.valueChanged.connect(lambda val, idx=i: self._on_eq_changed_with_label(val, idx))
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
        
        # Add panels to splitter (50/50 split)
        splitter.addWidget(waveform_panel)
        splitter.addWidget(eq_panel)
        splitter.setSizes([500, 500])  # Equal widths initially
        
        # Set splitter as content of the collapsible EQ panel
        self._waveform_eq_splitter = splitter
        if hasattr(self, 'eq_panel'):
            self.eq_panel.set_content(splitter)

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

    def _build_menubar(self):
        """Create a macOS-native menubar with File/Playback/View/Help."""
        mb = self.menuBar()

        # File menu
        m_file = mb.addMenu("File")
        act_add_files = QAction("Add Files…", self); act_add_files.triggered.connect(self.on_add_files)
        act_add_folder = QAction("Add Folder…", self); act_add_folder.triggered.connect(self.on_add_folder)
        act_save_pl = QAction("Save Playlist…", self); act_save_pl.triggered.connect(self.on_save_playlist)
        act_load_pl = QAction("Load Playlist…", self); act_load_pl.triggered.connect(self.on_load_playlist)
        act_refresh_meta = QAction("Refresh Metadata", self); act_refresh_meta.triggered.connect(self.on_refresh_metadata)
        act_save_eq = QAction("Save Song EQ", self); act_save_eq.triggered.connect(self._safe_save_eq)
        act_index_folder = QAction("Index Music Folder for Search…", self); act_index_folder.triggered.connect(self.on_index_folder)
        act_quit = QAction("Quit", self); act_quit.setShortcut(QKeySequence.Quit); act_quit.triggered.connect(lambda: QApplication.instance().quit())
        # Add all items except Quit, then separator, then Quit at bottom (customary)
        for a in [act_add_files, act_add_folder, act_save_pl, act_load_pl, act_refresh_meta, act_save_eq, act_index_folder]:
            m_file.addAction(a)
        m_file.addSeparator()
        m_file.addAction(act_quit)

        # Playback menu
        m_play = mb.addMenu("Playback")
        act_play = QAction("Play / Pause", self); act_play.setShortcut(Qt.Key_Space); act_play.triggered.connect(self.on_play)
        act_stop = QAction("Stop", self); act_stop.triggered.connect(self.on_stop)
        act_next = QAction("Next", self); act_next.setShortcut(QKeySequence.MoveToNextWord); act_next.triggered.connect(self.on_next)
        for a in [act_play, act_stop, act_next]: m_play.addAction(a)

        # View menu (EQ Opacity + Master Volume)
        m_view = mb.addMenu("View")
        
        # Master Volume submenu
        m_master_vol = m_view.addMenu("Master Volume")
        from PySide6.QtGui import QActionGroup
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
        grp = QActionGroup(self); grp.setExclusive(True)
        self._eq_opacity_actions = {}
        def _add_opc(name, val):
            act = QAction(name, self); act.setCheckable(True)
            act.triggered.connect(lambda: self._set_eq_opacity(val))
            grp.addAction(act); m_view.addAction(act); self._eq_opacity_actions[name] = act
        _add_opc("EQ Plate Opacity • Low (30%)", 0.30)
        _add_opc("EQ Plate Opacity • Medium (60%)", 0.60)
        _add_opc("EQ Plate Opacity • High (90%)", 0.90)
        # Default to Medium
        self._eq_opacity_actions["EQ Plate Opacity • Medium (60%)"].setChecked(True)
        # Apply after side panel builds (safe-call)
        QTimer.singleShot(0, lambda: self._set_eq_opacity(0.60))

        # Search shortcut (Cmd+F / Ctrl+F)
        act_search = QAction("Search", self)
        act_search.setShortcut(QKeySequence.Find)
        act_search.triggered.connect(lambda: self.search_bar.focus_search() if self.search_bar else None)
        m_file.addAction(act_search)

        # Help menu
        m_help = mb.addMenu("Help")
        act_about = QAction("About Sidecar EQ", self)
        act_about.triggered.connect(lambda: QMessageBox.information(self, "About", "Sidecar EQ\nSimple local player with per-track EQ."))
        m_help.addAction(act_about)

    def _set_eq_opacity(self, level: float):
        """Set opacity on the EQ background plate (if present)."""
        try:
            bg = getattr(self, "_eq_bg_widget", None)
            if not bg: return
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
    
    def _on_save_settings_clicked(self):
        """Handle Save Settings button click - save EQ and volume for current track."""
        if self.current_row is None:
            self.statusBar().showMessage("No track loaded - nothing to save", 3000)
            return
        
        try:
            # Save both EQ and volume
            self.save_eq_for_current_track()
            self.statusBar().showMessage("✓ Settings saved for this track!", 3000)
            print(f"[App] User clicked Save - settings saved for track at row {self.current_row}")
        except Exception as e:
            self.statusBar().showMessage(f"Failed to save settings: {e}", 5000)
            print(f"[App] Save settings failed: {e}")

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
            if self.current_row is not None and self.player._player.playbackState() == QMediaPlayer.PausedState:
                # Resume from paused position
                self.player._player.play()
                self.statusBar().showMessage("Playing (resumed)")
                self.play_btn.setActive(True)
                # Update play state indicator back to playing
                self.play_state_delegate.set_play_state(self.current_row, PlayStateDelegate.PLAY_STATE_PLAYING)
                # Start LED meters when resumed
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
        if self.current_row is None:
            self._play_row(0); return
        self._play_row(self.current_row + 1)

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

    def on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Add Folder")
        if not folder: return
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

    def on_remove_selected(self):
        sel = self.table.selectionModel().selectedRows()
        rows = [ix.row() for ix in sel]
        self.model.remove_rows(rows)
        self.statusBar().showMessage(f"Removed {len(rows)} rows")

    def _on_search_result_selected(self, file_path: str, play_immediately: bool):
        """Handle selection of a search result.
        
        Args:
            file_path: Path to the selected audio file
            play_immediately: If True, add and play; if False, just add to queue
        """
        if not file_path or not Path(file_path).exists():
            self.statusBar().showMessage("File not found!", 3000)
            return
            
        # Add to queue
        count = self.model.add_paths([file_path])
        
        if count > 0:
            new_row = len(self.model._rows) - 1  # Last row added
            
            if play_immediately:
                # Play the new track immediately
                self._play_row(new_row)
                self.statusBar().showMessage(f"Playing: {Path(file_path).name}", 3000)
            else:
                # Just added to queue
                self.statusBar().showMessage(f"Added: {Path(file_path).name}", 2000)
                
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
                    total = len(self.indexer.get_index())
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
            return
            
        # Update search bar with new index (on main thread)
        if self.search_bar:
            self.search_bar.set_index(self.indexer.get_index())
            
        # Show completion message
        self.statusBar().showMessage(
            f"✅ Indexing complete! Added {added} new tracks. Total: {total} searchable tracks.", 
            5000
        )
        
        # Show dialog with results
        QMessageBox.information(
            self, 
            "Indexing Complete! 🎵", 
            f"Successfully indexed your music library!\n\n"
            f"• Added: {added} new tracks\n"
            f"• Total searchable: {total} tracks\n\n"
            f"You can now search for songs using the search bar at the top!\n"
            f"Try typing an artist or song name. 🔍"
        )

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
        """Silently refresh metadata on startup without status message."""
        self._refresh_metadata_internal(show_message=False)
    
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
        out, _ = QFileDialog.getSaveFileName(self, "Save Playlist (JSON)", "", "JSON (*.json)")
        if not out: return
        playlist.save_json(self.model.paths(), out)
        self.statusBar().showMessage(f"Saved playlist to {out}")

    def on_load_playlist(self):
        inp, _ = QFileDialog.getOpenFileName(self, "Load Playlist (JSON or M3U)", "", "Playlists (*.json *.m3u *.m3u8)")
        if not inp: return
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
                pl_id = pid; break
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
        
        # Cancel any running background analysis since we're switching tracks
        if self._analysis_worker and self._analysis_worker.isRunning():
            self._analysis_worker.stop_analysis()
            self._pending_analysis_path = None
        
        # Reset user volume adjustment flag for new track
        self._user_adjusted_volume = False
        
        self.current_row = row
        
        # Get the track info to handle both local files, URLs, and Plex streams
        track_info = self.model._rows[row] if row < len(self.model._rows) else {}
        path = paths[row]
        
        # Update metadata display for the loaded track
        self._update_metadata_display(path)
        
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
            if hasattr(self, '_save_settings_btn'):
                self._save_settings_btn.setEnabled(True)
            
            # Start LED meters if they're visible and enabled
            self._update_led_meters_playback(True)
            
            title = self.model.data(self.model.index(row, 2))  # Title is now column 2
            artist = self.model.data(self.model.index(row, 3)) or ""  # Artist is column 3
            album = self.model.data(self.model.index(row, 4)) or ""  # Album is column 4
            
            # Auto-search for the currently playing track to show related songs
            if hasattr(self, 'search_bar') and self.search_bar:
                try:
                    self.search_bar.search_for_track(title or "Unknown", artist, album)
                except Exception as e:
                    print(f"[App] Failed to auto-search: {e}")
            
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
                self._apply_eq_settings(saved_data.get('gains_db', saved_data.get('eq_settings', [0]*7)))
            elif source_type in ('plex', 'url'):
                # Streaming sources: just load saved settings (no analysis possible)
                if saved_data:
                    self._apply_eq_settings(saved_data.get('gains_db', saved_data.get('eq_settings', [0]*7)))
                    print(f"[App] Loaded saved EQ settings for streaming source: {Path(identifier).stem}")
                else:
                    # Reset to flat EQ for new streaming sources
                    self._apply_eq_settings([0]*7)
                    print(f"[App] No saved settings for streaming source: {Path(identifier).stem} - using flat EQ")
            elif source_type == 'video':
                # Video files: analyze extracted audio but use original video path as identifier
                print(f"[App] Analyzing extracted audio from video: {Path(identifier).name}")
                eq_data = self._get_or_analyze_eq(playback_url)  # Analyze the extracted audio file
                if eq_data:
                    # Save settings using video file path as key for consistency
                    self._apply_eq_settings(eq_data.get('gains_db', [0]*7))
                    # Store analysis under video file identifier
                    self._store_analysis_for_video(identifier, eq_data)
                else:
                    # Reset to flat EQ if no analysis available
                    self._apply_eq_settings([0]*7)
            else:
                # Regular local audio files: Load saved settings or analyze
                if saved_data:
                    # Use saved settings (from previous analysis or manual save)
                    self._apply_eq_settings(saved_data.get('gains_db', saved_data.get('eq_settings', [0]*7)))
                    print(f"[App] ✓ Loaded saved EQ for: {Path(identifier).stem}")
                else:
                    # No saved settings - start background analysis
                    print(f"[App] No saved settings - starting analysis for: {Path(identifier).stem}")
                    self._apply_eq_settings([0]*7)  # Flat EQ while analyzing
                    self._start_background_analysis(identifier)
            
            # Apply saved volume for ALL source types (not just local files)
            if saved_volume is not None:
                print(f"[App] ✓ Loading saved volume: {saved_volume}%")
                self._apply_volume_setting(saved_volume)
            else:
                # No saved volume - use default 75% for new tracks
                print(f"[App] ⚠️  No saved volume found, defaulting to 75%")
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
                    self._apply_eq_settings(eq_data)
                
                # Apply volume suggestion ONLY if user hasn't manually adjusted it
                if not self._user_adjusted_volume:
                    analysis_data = analysis_result.get('analysis_data', {})
                    if 'suggested_volume' in analysis_data:
                        self._apply_volume_setting(analysis_data['suggested_volume'])
                else:
                    print(f"[App] Skipping volume from analysis (user adjusted manually)")
                
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
                    print(f"[App] ⚠️  Volume is None, defaulting to 75%")
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
    
    def _apply_eq_settings(self, gains_db: list):
        """Apply EQ settings to the sliders and update value labels.
        
        Args:
            gains_db: List of EQ gains in dB (-12 to +12 range)
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
        except Exception as e:
            print(f"[App] Failed to apply EQ: {e}")
    
    def _update_led_meters_playback(self, is_playing: bool):
        """Enable/disable LED meter simulation based on playback state.
        
        Args:
            is_playing: True if audio is playing, False otherwise
        """
        try:
            if not hasattr(self, '_led_meters') or not hasattr(self, '_led_meter_checkbox'):
                return
            
            # Only animate if checkbox is checked AND audio is playing
            meters_visible = self._led_meter_checkbox.isChecked()
            
            if is_playing and meters_visible:
                # Start simulation for all meters
                for meter in self._led_meters:
                    meter.enable_simulation(True)
                print(f"[App] LED meters started (playback active)")
            else:
                # Stop simulation
                for meter in self._led_meters:
                    meter.enable_simulation(False)
                if not is_playing:
                    print(f"[App] LED meters stopped (no playback)")
        except Exception as e:
            print(f"[App] Error updating LED meter playback state: {e}")
    
    def _toggle_led_meters(self, state):
        """Toggle visibility of LED meters behind EQ sliders."""
        try:
            visible = (state == Qt.Checked)
            if hasattr(self, '_led_meters'):
                # Check if audio is currently playing
                is_playing = False
                if hasattr(self, 'player') and self.player:
                    from PySide6.QtMultimedia import QMediaPlayer
                    is_playing = (self.player._player.playbackState() == QMediaPlayer.PlayingState)
                
                for meter in self._led_meters:
                    # Show/hide the widget AND ensure it's visible in parent layout
                    if visible:
                        meter.setVisible(True)  # Explicitly set visible flag
                        meter.show()            # Show in layout
                        meter.raise_()          # Bring to front
                        # Enable simulation if audio is currently playing
                        if is_playing:
                            meter.enable_simulation(True)
                        meter.update()          # Force repaint
                    else:
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
    
    def _on_eq_changed_with_label(self, val, idx):
        """Handle EQ slider change and update the corresponding value label."""
        # Update the value label for this slider
        if hasattr(self, '_eq_value_labels') and idx < len(self._eq_value_labels):
            # Format: +12, +0, -12
            if val >= 0:
                self._eq_value_labels[idx].setText(f"+{val}")
            else:
                self._eq_value_labels[idx].setText(f"{val}")
        
        # Call the regular EQ changed handler
        self._on_eq_changed()
    
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
        """Apply EQ settings to audio playback."""
        try:
            if not hasattr(self, 'player') or not self.player:
                return
            
            # Send EQ values to player
            if hasattr(self.player, 'set_eq_values'):
                self.player.set_eq_values(eq_values)
                
            # Calculate overall volume adjustment based on EQ settings
            # This is a simplified approach - reduce volume if too many boosts
            total_boost = sum(max(0, val) for val in eq_values)
            
            # Apply a basic volume compensation to prevent clipping
            volume_compensation = 1.0
            if total_boost > 30:  # More than 30dB total boost
                volume_compensation = 0.6  # Significant reduction
            elif total_boost > 20:  # High boost
                volume_compensation = 0.75
            elif total_boost > 10:  # Moderate boost
                volume_compensation = 0.9
            
            # Get current volume setting and apply compensation
            if hasattr(self, '_volume_slider') and self._volume_slider and self._volume_slider.value() is not None:
                base_volume = self._volume_slider.value() / 100.0
                adjusted_volume = base_volume * volume_compensation
                
                # Apply to player
                if hasattr(self.player, 'set_volume'):
                    self.player.set_volume(adjusted_volume)
            else:
                # Default volume if no spinner available
                if hasattr(self.player, 'set_volume'):
                    self.player.set_volume(0.7 * volume_compensation)
                    
                # Calculate frequency-specific adjustments for user feedback
                bass_adjustment = eq_values[0] + eq_values[1]  # 60Hz + 150Hz
                mid_adjustment = eq_values[2] + eq_values[3]   # 400Hz + 1kHz
                treble_adjustment = eq_values[4] + eq_values[5] + eq_values[6]  # 2.4kHz + 6kHz + 15kHz
                
                print(f"[App] EQ Applied - Bass: {bass_adjustment:+.1f}dB, Mid: {mid_adjustment:+.1f}dB, Treble: {treble_adjustment:+.1f}dB")
                if hasattr(self, '_volume_slider') and self._volume_slider and self._volume_slider.value() is not None:
                    print(f"[App] Volume compensation: {volume_compensation:.2f} (base: {base_volume:.2f} -> adjusted: {adjusted_volume:.2f})")
                else:
                    print(f"[App] Volume compensation: {volume_compensation:.2f} (default volume used)")
        
        except Exception as e:
            print(f"[App] Failed to apply EQ to player: {e}")
    
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
            # Handle URLs differently - limited metadata
            if path.startswith(('http://', 'https://')):
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
        
        # Return in analyzer format for consistency
        return {
            'gains_db': eq_settings,
            'suggested_volume': suggested_volume,
            'bands_hz': [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
        }
    
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
        """Get the path to the queue state file."""
        home = Path.home()
        sidecar_dir = home / ".sidecar_eq"
        sidecar_dir.mkdir(exist_ok=True)
        return sidecar_dir / "queue_state.json"

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
            print(f"[App] Initialized panels: all expanded (default)")
        except Exception as e:
            print(f"[App] Failed to load panel states: {e}")
    
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
            store.set_record("panel_states", states)
            print(f"[App] Saved panel states: {states}")
        except Exception as e:
            print(f"[App] Failed to save panel states: {e}")
    
    def _on_panel_toggled(self):
        """Handle panel collapse/expand - accordion style window resize."""
        # Save the state
        self._save_panel_states()
        
        # Resize window to fit content (accordion style)
        # Use QTimer to defer resize until after panel animation completes
        QTimer.singleShot(10, lambda: self._resize_to_content())
    
    def _resize_to_content(self):
        """Resize the main window to fit its current content (accordion behavior)."""
        try:
            # Get the natural size needed for all visible content
            self.adjustSize()
            print(f"[App] Window resized (accordion): {self.width()}x{self.height()}")
        except Exception as e:
            print(f"[App] Failed to resize window: {e}")
    
    def _save_queue_state(self):
        """Save the current queue state to disk."""
        try:
            if self.model:
                queue_file = self._get_queue_state_file()
                self.model.save_queue_state(queue_file)
        except Exception as e:
            print(f"[App] Failed to save queue state: {e}")

    def _load_queue_state(self):
        """Load the saved queue state from disk."""
        try:
            if self.model:
                queue_file = self._get_queue_state_file()
                self.model.load_queue_state(queue_file)
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
    setattr(app, "_vol_filter", _vf)
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
