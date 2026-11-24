"""Belegt, dass Tests keinen echten Netzwerkzugriff haben – auch unter Windows."""

from __future__ import annotations

import asyncio
import socket

import aiohttp
import pytest
from pytest_homeassistant_custom_component.plugins import HASocketBlockedError
from pytest_socket import SocketBlockedError


@pytest.fixture
def expect_blocked_attempts():
    """Das HA-Plugin lässt jeden Test fehlschlagen, der Sockets öffnen will.

    Hier sind die Versuche Absicht: Nach dem Test prüfen, dass sie tatsächlich
    blockiert wurden, und die Zählung zurücksetzen.
    """
    HASocketBlockedError.instances = []
    yield
    assert HASocketBlockedError.instances, "Erwarteter Socket-Zugriff wurde nicht blockiert"
    HASocketBlockedError.instances = []


@pytest.mark.usefixtures("expect_blocked_attempts")
def test_external_socket_blocked() -> None:
    """Direkter Verbindungsaufbau zu einer externen Adresse wird blockiert."""
    with pytest.raises(SocketBlockedError):
        socket.create_connection(("93.184.215.14", 80), timeout=1)


@pytest.mark.usefixtures("expect_blocked_attempts")
def test_socket_creation_blocked() -> None:
    """Schon das Anlegen eines TCP-Sockets ist gesperrt."""
    with pytest.raises(SocketBlockedError):
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def test_dns_blocked() -> None:
    """Auch Namensauflösung ist gesperrt (HA-Plugin bzw. pytest-socket)."""
    with pytest.raises(RuntimeError, match=r"(?i)dns|getaddrinfo"):
        socket.getaddrinfo("example.com", 443)


@pytest.mark.usefixtures("expect_blocked_attempts")
async def test_event_loop_works_but_network_blocked() -> None:
    """Die Eventloop läuft (lokales socketpair), echte HTTP-Zugriffe nicht."""
    await asyncio.sleep(0)
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    loop.call_soon_threadsafe(fut.set_result, 42)  # nutzt die Self-Pipe der Loop
    assert await fut == 42
    async with aiohttp.ClientSession() as session:
        with pytest.raises((SocketBlockedError, aiohttp.ClientError)) as exc_info:
            await session.get("http://93.184.215.14/", timeout=aiohttp.ClientTimeout(total=2))
    # aiohttp verpackt den Fehler ggf. – die Ursache muss die Socket-Sperre sein
    err: BaseException | None = exc_info.value
    while err is not None and not isinstance(err, SocketBlockedError):
        err = err.__cause__ or err.__context__
    assert isinstance(err, SocketBlockedError)
