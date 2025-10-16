"""Modern UI utilities for Sidecar EQ.

Provides system font detection, SF Symbols-style icons, smooth animations,
and native-looking color schemes for a polished, professional appearance.
"""

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QEasingCurve, QPropertyAnimation, QSize
from PySide6.QtGui import QFont, QIcon, QPainter, QPixmap, QColor
from PySide6.QtWidgets import QWidget
from PySide6.QtSvg import QSvgRenderer


class SystemFonts:
    """Detect and provide system-appropriate fonts."""
    
    @staticmethod
    def get_system_font(size: int = 13, weight: str = "Regular") -> QFont:
        """Get the system font for the current platform.
        
        Args:
            size: Font size in points
            weight: Font weight - "Regular", "Medium", "Semibold", "Bold"
            
        Returns:
            QFont configured for the system
        """
        if sys.platform == "darwin":  # macOS
            # SF Pro Text for body (up to 19pt), SF Pro Display for larger
            family = "SF Pro Display" if size >= 20 else "SF Pro Text"
            font = QFont(family, size)
        elif sys.platform == "win32":  # Windows
            # Segoe UI Variable is the Windows 11 system font
            font = QFont("Segoe UI Variable", size)
            if not font.exactMatch():
                # Fallback to regular Segoe UI
                font = QFont("Segoe UI", size)
        else:  # Linux
            font = QFont("Inter", size)
            if not font.exactMatch():
                font = QFont("Ubuntu", size)
                if not font.exactMatch():
                    font = QFont("Cantarell", size)
        
        # Set weight
        weight_map = {
            "Light": QFont.Light,
            "Regular": QFont.Normal,
            "Medium": QFont.Medium,
            "Semibold": QFont.DemiBold,
            "Bold": QFont.Bold,
        }
        font.setWeight(weight_map.get(weight, QFont.Normal))
        
        # Enable anti-aliasing
        font.setStyleHint(QFont.SansSerif)
        font.setHintingPreference(QFont.PreferDefaultHinting)
        
        return font
    
    @staticmethod
    def get_monospace_font(size: int = 12) -> QFont:
        """Get the system monospace font.
        
        Args:
            size: Font size in points
            
        Returns:
            QFont configured for monospace display
        """
        if sys.platform == "darwin":
            font = QFont("SF Mono", size)
        elif sys.platform == "win32":
            font = QFont("Cascadia Code", size)
            if not font.exactMatch():
                font = QFont("Consolas", size)
        else:
            font = QFont("Source Code Pro", size)
            if not font.exactMatch():
                font = QFont("DejaVu Sans Mono", size)
        
        font.setStyleHint(QFont.Monospace)
        return font


class ModernColors:
    """System-aware color palette for dark mode."""
    
    # macOS Big Sur / Windows 11 inspired colors
    BACKGROUND_PRIMARY = "#1c1c1e"      # Main background
    BACKGROUND_SECONDARY = "#2c2c2e"    # Cards, elevated surfaces
    BACKGROUND_TERTIARY = "#3a3a3c"     # Hover states
    
    TEXT_PRIMARY = "#ffffff"            # Primary text
    TEXT_SECONDARY = "#ebebf5"          # Secondary text (90% opacity)
    TEXT_TERTIARY = "#ebebf5"           # Tertiary text (60% opacity)
    TEXT_QUATERNARY = "#ebebf5"         # Disabled text (40% opacity)
    
    SEPARATOR = "#38383a"               # Divider lines
    FILL_PRIMARY = "#787880"            # Primary fill
    FILL_SECONDARY = "#787880"          # Secondary fill
    
    # Accent colors (macOS blue)
    ACCENT = "#007aff"
    ACCENT_HOVER = "#0051d5"
    ACCENT_PRESSED = "#0040a8"
    
    # Semantic colors
    SUCCESS = "#34c759"
    WARNING = "#ff9500"
    ERROR = "#ff3b30"
    INFO = "#5ac8fa"
    
    @classmethod
    def is_dark_mode(cls) -> bool:
        """Detect if system is in dark mode.
        
        Returns:
            True if dark mode is active
        """
        # For now, assume dark mode (we can enhance this with system detection)
        return True
    
    @classmethod
    def get_background(cls, level: int = 1) -> str:
        """Get background color for elevation level.
        
        Args:
            level: Elevation level (1=primary, 2=secondary, 3=tertiary)
            
        Returns:
            Hex color string
        """
        if level == 1:
            return cls.BACKGROUND_PRIMARY
        elif level == 2:
            return cls.BACKGROUND_SECONDARY
        else:
            return cls.BACKGROUND_TERTIARY
    
    @classmethod
    def with_opacity(cls, color: str, opacity: float) -> str:
        """Add opacity to a hex color.
        
        Args:
            color: Hex color (#RRGGBB)
            opacity: Opacity from 0.0 to 1.0
            
        Returns:
            RGBA color string
        """
        # Convert hex to RGB
        color = color.lstrip('#')
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
        return f"rgba({r}, {g}, {b}, {opacity})"


class IconManager:
    """Modern icon system with dynamic coloring."""
    
    _cache = {}
    
    @classmethod
    def get_icon(cls, name: str, color: Optional[str] = None, size: int = 24) -> QIcon:
        """Get an icon with optional color override.
        
        Args:
            name: Icon name (e.g., "play", "trash", "download")
            color: Optional hex color to apply (#RRGGBB)
            size: Icon size in pixels
            
        Returns:
            QIcon ready to use
        """
        # Build cache key
        cache_key = f"{name}_{color}_{size}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]
        
        # Try to load from icons folder
        icon_path = Path(f"icons/{name}.svg")
        if not icon_path.exists():
            # Fallback to creating a simple colored square
            return cls._create_placeholder_icon(color or "#888888", size)
        
        # Load and optionally recolor SVG
        if color:
            icon = cls._load_svg_with_color(icon_path, color, size)
        else:
            icon = QIcon(str(icon_path))
        
        cls._cache[cache_key] = icon
        return icon
    
    @classmethod
    def _load_svg_with_color(cls, path: Path, color: str, size: int) -> QIcon:
        """Load SVG and apply color tint.
        
        Args:
            path: Path to SVG file
            color: Hex color to apply
            size: Icon size
            
        Returns:
            Colored QIcon
        """
        renderer = QSvgRenderer(str(path))
        pixmap = QPixmap(QSize(size, size))
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        
        # Apply color tint
        colored_pixmap = QPixmap(pixmap.size())
        colored_pixmap.fill(Qt.transparent)
        painter = QPainter(colored_pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(color))
        painter.end()
        
        return QIcon(colored_pixmap)
    
    @classmethod
    def _create_placeholder_icon(cls, color: str, size: int) -> QIcon:
        """Create a simple placeholder icon.
        
        Args:
            color: Hex color
            size: Icon size
            
        Returns:
            QIcon placeholder
        """
        pixmap = QPixmap(QSize(size, size))
        pixmap.fill(QColor(color))
        return QIcon(pixmap)


class SmoothAnimation:
    """Utilities for smooth, native-feeling animations."""
    
    @staticmethod
    def animate_height(widget: QWidget, target_height: int, duration: int = 250) -> QPropertyAnimation:
        """Animate widget height with smooth easing.
        
        Args:
            widget: Widget to animate
            target_height: Target height in pixels
            duration: Animation duration in milliseconds
            
        Returns:
            QPropertyAnimation (starts automatically)
        """
        animation = QPropertyAnimation(widget, b"maximumHeight")
        animation.setDuration(duration)
        animation.setStartValue(widget.height())
        animation.setEndValue(target_height)
        animation.setEasingCurve(QEasingCurve.InOutCubic)  # Smooth ease
        animation.start()
        return animation
    
    @staticmethod
    def animate_opacity(widget: QWidget, target_opacity: float, duration: int = 200) -> QPropertyAnimation:
        """Animate widget opacity.
        
        Args:
            widget: Widget to animate
            target_opacity: Target opacity (0.0 to 1.0)
            duration: Animation duration in milliseconds
            
        Returns:
            QPropertyAnimation (starts automatically)
        """
        animation = QPropertyAnimation(widget, b"windowOpacity")
        animation.setDuration(duration)
        animation.setEndValue(target_opacity)
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        animation.start()
        return animation


class Typography:
    """Typography scale and helper functions."""
    
    # Type scale (in points)
    CAPTION_1 = 12      # Small labels, captions
    CAPTION_2 = 11      # Very small text
    BODY = 13           # Standard body text
    CALLOUT = 14        # Emphasized body
    SUBHEADLINE = 15    # Section subheadings
    HEADLINE = 17       # Section headlines
    TITLE_3 = 20        # Card titles
    TITLE_2 = 22        # Modal titles
    TITLE_1 = 28        # Page titles
    LARGE_TITLE = 34    # Hero titles
    
    @classmethod
    def get_font(cls, style: str = "body", weight: str = "Regular") -> QFont:
        """Get a font for a specific typographic style.
        
        Args:
            style: Typography style name (e.g., "body", "headline", "title1")
            weight: Font weight
            
        Returns:
            QFont configured for the style
        """
        size_map = {
            "caption1": cls.CAPTION_1,
            "caption2": cls.CAPTION_2,
            "body": cls.BODY,
            "callout": cls.CALLOUT,
            "subheadline": cls.SUBHEADLINE,
            "headline": cls.HEADLINE,
            "title3": cls.TITLE_3,
            "title2": cls.TITLE_2,
            "title1": cls.TITLE_1,
            "largetitle": cls.LARGE_TITLE,
        }
        
        size = size_map.get(style.lower(), cls.BODY)
        return SystemFonts.get_system_font(size, weight)
