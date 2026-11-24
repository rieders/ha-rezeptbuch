"""Gemeinsame Fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import sqlite3
import sys

import pytest

from custom_components.rezeptbuch.db import connect, transaction

if sys.platform == "win32":
    # Windows: asyncio legt für die Eventloop (Self-Pipe) über socket.socketpair()
    # ein lokales TCP-Socket-Paar an, weil es dort keine Unix-Socketpaare gibt.
    # Das HA-Testplugin sperrt per pytest-socket aber jede Socket-Erzeugung außer
    # AF_UNIX. Die Sperre bleibt vollständig aktiv – nur socketpair() bekommt
    # für die Dauer des Aufrufs die echte Socket-Klasse. socketpair() verbindet
    # ausschließlich mit 127.0.0.1 (lokaler Listener), echte Netzwerkzugriffe
    # schlagen weiterhin mit SocketBlockedError fehl (siehe test_network_guard.py).
    import socket as _socket

    import pytest_socket

    _original_socketpair = _socket.socketpair

    def _local_socketpair(*args, **kwargs):
        guarded = _socket.socket
        _socket.socket = pytest_socket._true_socket
        try:
            return _original_socketpair(*args, **kwargs)
        finally:
            _socket.socket = guarded

    _socket.socketpair = _local_socketpair


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """Frisch migrierte Datenbank (synchron, für Repository-Tests)."""
    connection = connect(tmp_path / "rezepte.db")
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def tx(conn: sqlite3.Connection):
    """Hilfsfunktion: f(conn, ...) in einer Transaktion ausführen."""

    def _run(func, *args, **kwargs):
        with transaction(conn):
            return func(conn, *args, **kwargs)

    return _run
