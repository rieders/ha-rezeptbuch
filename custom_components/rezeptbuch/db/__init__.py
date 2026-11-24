"""SQLite-Zugriff für das Rezeptbuch.

Alle Zugriffe laufen über einen eigenen Ein-Thread-Executor. Dadurch sind
Schreibzugriffe automatisch serialisiert und die Verbindung wird nur von
einem Thread benutzt. Repository-Funktionen (recipes, versions, …) sind
synchrone Funktionen `f(conn, ...)`; `Database.run` führt sie im Executor
innerhalb einer Transaktion aus.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import functools
import itertools
import logging
from pathlib import Path
import sqlite3
from typing import Any, TypeVar

from .schema import migrate

_LOGGER = logging.getLogger(__name__)
_T = TypeVar("_T")
_savepoint_counter = itertools.count(1)


class DatabaseError(Exception):
    """Fehler beim DB-Zugriff (fachlich oder technisch)."""


class NotFoundError(DatabaseError):
    """Datensatz nicht gefunden."""


class ConflictError(DatabaseError):
    """Fachlicher Konflikt (z. B. Zyklus im Kategoriebaum)."""


def connect(path: Path | str) -> sqlite3.Connection:
    """Verbindung öffnen, PRAGMAs setzen und Schema migrieren."""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    if str(path) != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
    migrate(conn)
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Transaktion; verschachtelt als SAVEPOINT."""
    if conn.in_transaction:
        name = f"sp_{next(_savepoint_counter)}"
        conn.execute(f"SAVEPOINT {name}")
        try:
            yield conn
        except BaseException:
            conn.execute(f"ROLLBACK TO {name}")
            conn.execute(f"RELEASE {name}")
            raise
        conn.execute(f"RELEASE {name}")
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    """sqlite3.Row → dict."""
    return dict(row) if row is not None else None


class Database:
    """Asynchroner Zugriff auf die Rezeptdatenbank."""

    def __init__(self, path: Path | str) -> None:
        """Initialisieren (noch ohne Verbindung)."""
        self.path = path
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="rezeptbuch_db")
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        """Die offene Verbindung (nur im DB-Thread benutzen!)."""
        if self._conn is None:
            raise DatabaseError("Datenbank ist nicht geöffnet")
        return self._conn

    async def _submit(self, func: Callable[..., _T], *args: Any, **kwargs: Any) -> _T:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, functools.partial(func, *args, **kwargs))

    async def async_open(self) -> None:
        """Verbindung im DB-Thread öffnen und migrieren."""

        def _open() -> None:
            self._conn = connect(self.path)

        await self._submit(_open)

    async def run(self, func: Callable[..., _T], *args: Any, **kwargs: Any) -> _T:
        """`func(conn, *args, **kwargs)` im DB-Thread in einer Transaktion ausführen."""

        def _call() -> _T:
            with transaction(self.conn) as conn:
                return func(conn, *args, **kwargs)

        return await self._submit(_call)

    async def async_close(self) -> None:
        """Verbindung schließen und Executor beenden."""

        def _close() -> None:
            if self._conn is not None:
                try:
                    self._conn.execute("PRAGMA optimize")
                finally:
                    self._conn.close()
                    self._conn = None

        try:
            await self._submit(_close)
        finally:
            self._executor.shutdown(wait=False)
