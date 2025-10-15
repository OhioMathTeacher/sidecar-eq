"""Centralized stylesheet definitions for Sidecar EQ.

This module contains all Qt stylesheet strings used throughout the application,
organized by component for easy maintenance and theming.
"""


# Main window style
MAIN_WINDOW_STYLE = """
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
"""


# Music directory combo box style
MUSIC_DIR_COMBO_STYLE = """
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
"""


# Metadata label (LCD-style now playing display)
METADATA_LABEL_STYLE = """
    QLabel {
        color: #00ff00;
        font-family: 'Courier New', 'Courier', 'Lucida Console', monospace;
        font-size: 14px;
        font-weight: bold;
        padding: 8px 16px;
        background: #1e1e1e;
        border: 1px solid #2e2e2e;
        border-radius: 4px;
    }
"""


# Waveform panel background
WAVEFORM_PANEL_STYLE = """
    QWidget {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 4px;
    }
"""


# EQ panel background
EQ_PANEL_STYLE = """
    QWidget {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 4px;
    }
"""


# Volume label style
VOLUME_LABEL_STYLE = """
    color: #ff4d4d;
    font-size: 10px;
    font-family: 'Helvetica';
    font-weight: bold;
    background: transparent;
    border: none;
"""


# Volume value display style
VOLUME_VALUE_STYLE = """
    color: #ff8888;
    font-size: 9px;
    font-family: 'Courier New';
    background: transparent;
    border: none;
"""


# Time display box style
TIME_BOX_STYLE = """
    background: #1e1e1e;
    border: 1px solid #2e2e2e;
    border-radius: 4px;
    color: #808080;
    font-size: 12px;
"""


# EQ value label style (narrow, compact to match VOLUME style)
EQ_VALUE_LABEL_STYLE = """
    color: #6699cc;
    font-size: 8px;
    font-family: 'Helvetica Neue', 'Helvetica', 'Arial Narrow', 'Arial', sans-serif;
    font-weight: normal;
    background: transparent;
    border: none;
"""


# EQ frequency label style (narrow, compact)
EQ_FREQ_LABEL_STYLE = """
    color: #808080;
    font-size: 8px;
    font-family: 'Helvetica Neue', 'Helvetica', 'Arial Narrow', 'Arial', sans-serif;
    font-weight: normal;
    background: transparent;
    border: none;
"""
