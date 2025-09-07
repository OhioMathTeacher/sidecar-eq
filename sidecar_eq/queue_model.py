from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from pathlib import Path
import os
from . import store

COLUMNS = ["Title", "Artist", "Album", "Play Count", "EQ Profile"]

class QueueModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        # each row: {path, title, artist, album, play_count, eq_profile}
        self._rows = []
        self._paths_set = set()

    # --- Qt model API ---
    def rowCount(self, parent=QModelIndex()):
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return len(COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole,):
            return None
        row = self._rows[index.row()]
        col = index.column()
        if col == 0:
            return row.get("title") or Path(row["path"]).name
        elif col == 1:
            return row.get("artist") or ""
        elif col == 2:
            return row.get("album") or ""
        elif col == 3:
            return str(row.get("play_count", 0))
        elif col == 4:
            prof = row.get("eq_profile")
            return "Yes" if isinstance(prof, dict) else ""
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return COLUMNS[section]
        return str(section + 1)

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    # --- Helpers ---
    def add_paths(self, paths):
        added = 0
        for p in paths:
            ap = os.path.abspath(p)
            if ap in self._paths_set:
                continue
            rec = store.get_record(ap) or {}
            row = {
                "path": ap,
                "title": None,
                "artist": None,
                "album": None,
                "play_count": rec.get("play_count", 0),
                "eq_profile": rec.get("eq_profile"),
            }
            self.beginInsertRows(QModelIndex(), len(self._rows), len(self._rows))
            self._rows.append(row)
            self._paths_set.add(ap)
            self.endInsertRows()
            added += 1
        return added

    def paths(self):
        return [r["path"] for r in self._rows]

    def remove_rows(self, rows):
        for r in sorted(set(rows), reverse=True):
            self.beginRemoveRows(QModelIndex(), r, r)
            ap = self._rows[r]["path"]
            self._rows.pop(r)
            self._paths_set.discard(ap)
            self.endRemoveRows()
