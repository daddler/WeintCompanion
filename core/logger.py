from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable


@dataclass
class LogEntry:

    timestamp: datetime
    level: str
    message: str


class Logger:

    def __init__(self):

        self._listeners: list[
            Callable[[LogEntry], None]
        ] = []

        self.history: list[LogEntry] = []

        #
        # Log-Datei
        #

        self.log_dir = Path("cache/logs")
        self.log_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.log_file = (
            self.log_dir / "companion.log"
        )

    # --------------------------------------------------

    def subscribe(self, callback):

        if callback not in self._listeners:

            self._listeners.append(callback)

    # --------------------------------------------------

    def unsubscribe(self, callback):

        if callback in self._listeners:

            self._listeners.remove(callback)

    # --------------------------------------------------

    def entries(self):

        return list(self.history)

    # --------------------------------------------------

    def clear(self):

        self.history.clear()

        self.log_file.write_text(
            "",
            encoding="utf-8",
        )

    # --------------------------------------------------

    def _emit(
        self,
        level: str,
        message: str,
    ):

        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
        )

        self.history.append(entry)

        #
        # Terminal
        #

        line = (
            f"[{entry.timestamp:%H:%M:%S}] "
            f"{level.upper():8} "
            f"{message}"
        )

        print(line)

        #
        # Datei
        #

        with self.log_file.open(
            "a",
            encoding="utf-8",
        ) as file:

            file.write(line + "\n")

        #
        # Widgets informieren
        #

        for listener in self._listeners:

            listener(entry)

    # --------------------------------------------------

    def info(self, message):

        self._emit(
            "info",
            message,
        )

    def success(self, message):

        self._emit(
            "success",
            message,
        )

    def warning(self, message):

        self._emit(
            "warning",
            message,
        )

    def error(self, message):

        self._emit(
            "error",
            message,
        )