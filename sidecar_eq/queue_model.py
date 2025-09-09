from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from pathlib import Path
from mutagen import File as MutagenFile
import os
from . import store
from .metadata import read_tags

COLUMNS = ["Title", "Artist", "Album", "Play Count"]

class QueueModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        # each row: {path, title, artist, album, play_count}
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
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return COLUMNS[section]
        return str(section + 1)

    def flags(self, index):
        default = super().flags(index)
        return default | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled

    def supportedDropActions(self):
        return Qt.MoveAction

    def moveRows(self, sourceParent, sourceRow, count, destinationParent, destinationChild):
        # TODO: implement bulk‐add of multiple file paths
        return 0

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
                "play_count": rec.get("play_count", 0)
            }
            # now try to read tags via mutagen
            try:
                mf = MutagenFile(ap, easy=True)
                if mf:
                    row["title"]  = mf.get("title",  [Path(ap).stem])[0]
                    row["artist"] = mf.get("artist", [""])[0]
                    row["album"]  = mf.get("album",  [""])[0]
            except Exception:
                # leave title/artist/album as None if reading fails
                pass
            
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

    def add_track(self, track):
        """Add a single track dict (from Plex or local), expects keys: title, artist, album, stream_url or file."""
        # Normalize to your internal row format:
        row = {
            "path": track.get("file", ""),    # Will be blank for Plex (use stream_url instead)
            "title": track.get("title", ""),
            "artist": track.get("artist", ""),
            "album": track.get("album", ""),
            "play_count": 0,
            "stream_url": track.get("stream_url", None),  # This is for Plex tracks
            "source": track.get("source", "local"),
        }
        self.beginInsertRows(QModelIndex(), len(self._rows), len(self._rows))
        self._rows.append(row)
        self._paths_set.add(row["path"] or row["stream_url"])
        self.endInsertRows()
        return 1
