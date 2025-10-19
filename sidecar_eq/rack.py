from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class OutputCanvas(QStackedWidget):
    """Single large display area that swaps pages based on active module.

    API:
    - add_page(page_id: str, widget: QWidget, title: str)
    - show_page(page_id: str)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # page_id -> stacked index
        self._pages = {}
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Simple LED-like styling; can be themed by Modern UI later
        self.setStyleSheet(
            """
            QStackedWidget {
                background: #141414;
                border-left: 1px solid #303030;
            }
            QLabel#LedPlaceholder {
                color: #9ad04b;
                font-size: 14px;
                padding: 12px;
            }
            """
        )

    def add_page(self, page_id: str, widget: QWidget, title: str):
        if page_id in self._pages:
            # replace existing
            self.removeWidget(self.widget(self._pages[page_id]))
        idx = self.addWidget(widget)
        self._pages[page_id] = idx

    def show_page(self, page_id: str):
        idx = self._pages.get(page_id)
        if idx is not None:
            self.setCurrentIndex(idx)


class RackView(QWidget):
    """Vertical strip of uniform-size module buttons.

    Emits module_selected(page_id: str) when a button is clicked.
    """

    module_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RackView")
        self.setFixedWidth(180)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._list = QVBoxLayout()
        self._list.setContentsMargins(0, 0, 0, 0)
        self._list.setSpacing(0)

        container = QFrame()
        container.setLayout(self._list)
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        container.setStyleSheet(
            """
            QFrame { background: #1a1a1a; border-right: 1px solid #303030; }
            QPushButton[class='Module'] {
                text-align: left;
                padding: 10px 12px;
                color: #e0e0e0;
                background: transparent;
                border: none;
            }
            QPushButton[class='Module']:hover { background: #222; }
            QPushButton[class='Module']:checked { background: #2b2b2b; color: #9ad04b; }
            """
        )

        root.addWidget(container)
        self.setLayout(root)
        # Map page_id -> button
        self._buttons = {}

    def add_module(self, page_id: str, title: str):
        btn = QPushButton(title)
        btn.setCheckable(True)
        btn.setChecked(False)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # Use a style property to target in Qt stylesheets
        btn.setProperty("class", "Module")

        def on_click():
            for other in self._buttons.values():
                if other is not btn:
                    other.setChecked(False)
            btn.setChecked(True)
            self.module_selected.emit(page_id)

        btn.clicked.connect(on_click)
        self._list.addWidget(btn)
        self._buttons[page_id] = btn

    def select(self, page_id: str):
        btn = self._buttons.get(page_id)
        if btn is not None:
            btn.click()
