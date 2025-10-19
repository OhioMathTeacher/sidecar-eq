from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)

try:
    from .modern_ui import SystemFonts, ModernColors
    USE_MODERN_UI = True
except Exception:
    USE_MODERN_UI = False

from . import store


class SettingsDialog(QDialog):
    """Central preferences panel for Sidecar EQ."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent or main_window)
        self.main = main_window
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(420)

        if USE_MODERN_UI:
            system_font = SystemFonts.get_system_font(size=11).family()
            self.setStyleSheet(
                f"""
                QDialog {{ background: {ModernColors.BACKGROUND_PRIMARY}; }}
                QLabel {{ color: {ModernColors.TEXT_SECONDARY}; font-family: '{system_font}'; font-size: 11px; }}
                QCheckBox {{ color: {ModernColors.TEXT_PRIMARY}; font-family: '{system_font}'; font-size: 11px; }}
                QComboBox {{ background: {ModernColors.BACKGROUND_TERTIARY}; color: {ModernColors.TEXT_PRIMARY}; }}
                """
            )

        layout = QVBoxLayout()
        form = QFormLayout()

        # Queue appearance
        prefs = store.get_record("ui:settings") or {}

        self.cb_alt_stripes = QCheckBox("Alternating row stripes in queue")
        self.cb_alt_stripes.setChecked(bool(prefs.get("queue_alternating_stripes", True)))
        form.addRow(self.cb_alt_stripes)

        self.cb_empty_stripes = QCheckBox("Show stripes and hint when queue is empty")
        self.cb_empty_stripes.setChecked(bool(prefs.get("queue_empty_stripes", True)))
        form.addRow(self.cb_empty_stripes)

        # Layout presets
        self.cb_remember_layout = QCheckBox("Remember last layout preset on exit")
        self.cb_remember_layout.setChecked(bool(prefs.get("remember_layout", True)))
        form.addRow(self.cb_remember_layout)

        self.cmb_default_layout = QComboBox()
        self._layout_keys = ["full_view", "queue_only", "eq_only", "search_only"]
        self.cmb_default_layout.addItems(["Full View", "Queue Only", "EQ Only", "Search Only"])
        saved = prefs.get("default_layout_preset", "full_view")
        if saved in self._layout_keys:
            self.cmb_default_layout.setCurrentIndex(self._layout_keys.index(saved))
        form.addRow(QLabel("Default layout preset"), self.cmb_default_layout)

        layout.addLayout(form)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self._on_apply)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _apply_settings(self):
        # Persist settings (stored under a single key)
        prefs = {
            "queue_alternating_stripes": self.cb_alt_stripes.isChecked(),
            "queue_empty_stripes": self.cb_empty_stripes.isChecked(),
            "remember_layout": self.cb_remember_layout.isChecked(),
            "default_layout_preset": self._layout_keys[self.cmb_default_layout.currentIndex()],
        }
        store.set_record("ui:settings", prefs)

        # Apply immediately where possible
        try:
            if getattr(self.main, "table", None) is not None:
                self.main.table.setAlternatingRowColors(self.cb_alt_stripes.isChecked())
                # Toggle empty stripes/hint rendering
                if hasattr(self.main.table, "setShowEmptyStripes"):
                    self.main.table.setShowEmptyStripes(self.cb_empty_stripes.isChecked())
                self.main.table.viewport().update()
        except Exception:
            pass

        # Apply default layout if not remembering last
        try:
            if not self.cb_remember_layout.isChecked():
                self.main._apply_layout_preset(self._layout_keys[self.cmb_default_layout.currentIndex()])
        except Exception:
            pass

    def _on_apply(self):
        self._apply_settings()

    def _on_ok(self):
        self._apply_settings()
        self.accept()
