from sidecar_eq import app
from PySide6.QtWidgets import QApplication

if __name__ == '__main__':
    qapp = QApplication([])
    w = app.MainWindow()
    # call a few harmless methods
    try:
        w._build_toolbar()
        w._build_side_panel()
    except Exception:
        pass
    print('SMOKE: window created')
    w.deleteLater()
    print('SMOKE: done')
