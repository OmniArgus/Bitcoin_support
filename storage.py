"""Tiny JSON-file persistence for subscribers, threshold, and last price.

Keeps state across restarts without needing a database. For a low-traffic
notification bot this is plenty; swap for SQLite/Redis if you ever scale up.
"""

import json
import os
import threading
from typing import List, Optional


class Storage:
    def __init__(self, path: str) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._data = {"subscribers": [], "threshold": None, "last_price": None}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as fh:
                    self._data.update(json.load(fh))
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self) -> None:
        tmp = f"{self._path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh)
        os.replace(tmp, self._path)

    # --- subscribers --------------------------------------------------------

    def subscribe(self, chat_id: int) -> None:
        with self._lock:
            if chat_id not in self._data["subscribers"]:
                self._data["subscribers"].append(chat_id)
                self._save()

    def unsubscribe(self, chat_id: int) -> None:
        with self._lock:
            if chat_id in self._data["subscribers"]:
                self._data["subscribers"].remove(chat_id)
                self._save()

    def subscribers(self) -> List[int]:
        with self._lock:
            return list(self._data["subscribers"])

    # --- threshold ----------------------------------------------------------

    def get_threshold(self, default: float) -> float:
        with self._lock:
            value = self._data.get("threshold")
            return float(value) if value is not None else default

    def set_threshold(self, value: float) -> None:
        with self._lock:
            self._data["threshold"] = value
            self._save()

    # --- last notified price ------------------------------------------------

    def get_last_price(self) -> Optional[float]:
        with self._lock:
            value = self._data.get("last_price")
            return float(value) if value is not None else None

    def set_last_price(self, value: float) -> None:
        with self._lock:
            self._data["last_price"] = value
            self._save()
