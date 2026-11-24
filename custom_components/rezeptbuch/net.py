"""Sicherer HTTP-Abruf über die aiohttp-Session von Home Assistant.

- nur http/https
- SSRF-Schutz: Ziel-Host wird aufgelöst, private/lokale/reservierte Adressen
  werden abgelehnt – auch bei jeder Weiterleitung (Redirects werden manuell
  verfolgt und einzeln geprüft)
- Gesamt-Timeout, Größenlimit (Content-Length *und* tatsächlich gelesene Bytes)
- eigener User-Agent

Restrisiko: DNS-Rebinding zwischen Prüfung und Verbindungsaufbau (aiohttp
löst erneut auf). Für den Einsatz im Heimnetz ist das vertretbar.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import ipaddress
import logging
import re
import socket

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from yarl import URL

from .errors import BlockedAddress, FetchFailed, InvalidUrl, ResponseTooLarge

_LOGGER = logging.getLogger(__name__)

VERSION = "0.1.0"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    f"Chrome/131.0 Safari/537.36 HomeAssistant-Rezeptbuch/{VERSION}"
)
DEFAULT_TIMEOUT = 15.0
MAX_HTML_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 5
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_CHUNK = 64 * 1024

_META_CHARSET_RE = re.compile(rb"""<meta[^>]+charset\s*=\s*["']?\s*([A-Za-z0-9_\-]+)""", re.IGNORECASE)


@dataclass(frozen=True)
class FetchResult:
    """Antwort eines erfolgreichen Abrufs."""

    url: str  # endgültige URL nach Weiterleitungen
    status: int
    content_type: str
    charset: str | None
    body: bytes

    def text(self) -> str:
        """Body als Text (Charset aus Header, sonst <meta charset>, sonst UTF-8)."""
        charset = self.charset
        if not charset:
            m = _META_CHARSET_RE.search(self.body[:4096])
            charset = m.group(1).decode("ascii") if m else "utf-8"
        try:
            return self.body.decode(charset, errors="replace")
        except LookupError:
            return self.body.decode("utf-8", errors="replace")


_CGNAT = ipaddress.ip_network("100.64.0.0/10")  # z. B. Tailscale


def is_allowed_ip(ip: str, allow_private: bool = False) -> bool:
    """Darf diese Adresse abgerufen werden?

    Immer gesperrt: Loopback, unspezifiziert (0.0.0.0/::), Link-Local (inkl.
    Cloud-Metadaten 169.254.169.254), Multicast, reservierte Bereiche.
    Private LAN-Bereiche (10/8, 172.16/12, 192.168/16, fc00::/7, 100.64/10)
    nur mit allow_private. Öffentliche Unicast-Adressen immer.
    """
    try:
        addr = ipaddress.ip_address(ip.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    if addr.is_loopback or addr.is_unspecified or addr.is_link_local or addr.is_multicast or addr.is_reserved:
        return False
    if addr.is_global:
        return True
    if not allow_private:
        return False
    return addr.is_private or (isinstance(addr, ipaddress.IPv4Address) and addr in _CGNAT)


def is_public_ip(ip: str) -> bool:
    """True nur für öffentlich routbare Unicast-Adressen."""
    return is_allowed_ip(ip, allow_private=False)


async def async_resolve_host(hass: HomeAssistant, host: str) -> list[str]:
    """Hostnamen auflösen (in Tests gepatcht)."""
    infos = await hass.loop.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    return list(dict.fromkeys(str(info[4][0]) for info in infos))


def parse_http_url(url: str) -> URL:
    """URL prüfen: nur http/https, mit Host, ohne Zugangsdaten."""
    try:
        parsed = URL(url.strip())
    except (ValueError, TypeError) as err:
        raise InvalidUrl(f"Ungültige URL: {url}", url=url) from err
    if parsed.scheme not in ("http", "https"):
        raise InvalidUrl(f"Nur http/https-Adressen sind erlaubt: {url}", url=url)
    if not parsed.host:
        raise InvalidUrl(f"URL ohne Host: {url}", url=url)
    if parsed.user or parsed.password:
        raise InvalidUrl("URLs mit Zugangsdaten sind nicht erlaubt", url=url)
    return parsed


_LOOPBACK_NAMES = ("localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback")
_LAN_SUFFIXES = (".local", ".internal", ".lan", ".home.arpa", ".fritz.box")


async def async_check_target(hass: HomeAssistant, url: URL, *, allow_private: bool = False) -> None:
    """SSRF-Schutz: alle aufgelösten Adressen müssen erlaubt sein.

    localhost/Loopback ist immer gesperrt – auch mit allow_private.
    """
    host = (url.host or "").lower().rstrip(".")
    if host in _LOOPBACK_NAMES or host.endswith(".localhost"):
        raise BlockedAddress(f"Lokale Adresse nicht erlaubt: {host}", host=host)
    if not allow_private and host.endswith(_LAN_SUFFIXES):
        raise BlockedAddress(f"Adresse im lokalen Netz nicht erlaubt: {host}", host=host)
    try:
        ipaddress.ip_address(host.strip("[]"))
        addresses = [host.strip("[]")]
    except ValueError:
        try:
            addresses = await async_resolve_host(hass, host)
        except OSError as err:
            raise FetchFailed(f"Host nicht gefunden: {host}", host=host, reason=str(err)) from err
    if not addresses:
        raise FetchFailed(f"Host nicht gefunden: {host}", host=host, reason="keine Adresse")
    for address in addresses:
        if not is_allowed_ip(address, allow_private):
            raise BlockedAddress(f"Private oder lokale Adresse nicht erlaubt: {host}", host=host)


async def async_safe_get(
    hass: HomeAssistant,
    url: str,
    *,
    max_bytes: int = MAX_HTML_BYTES,
    timeout: float = DEFAULT_TIMEOUT,
    accept: str = "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    allow_private: bool = False,
) -> FetchResult:
    """GET mit SSRF-Schutz, Größenlimit, Timeout und geprüften Weiterleitungen."""
    session = async_get_clientsession(hass)
    current = parse_http_url(url)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": accept,
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.5",
    }
    try:
        async with asyncio.timeout(timeout):
            for _ in range(MAX_REDIRECTS + 1):
                await async_check_target(hass, current, allow_private=allow_private)
                async with session.get(
                    current,
                    headers=headers,
                    allow_redirects=False,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as resp:
                    if resp.status in REDIRECT_STATUSES:
                        location = resp.headers.get("Location")
                        if not location:
                            raise FetchFailed("Weiterleitung ohne Ziel", url=str(current), reason="redirect")
                        current = parse_http_url(str(current.join(URL(location))))
                        continue
                    if resp.status >= 400:
                        raise FetchFailed(
                            f"Seite nicht erreichbar (HTTP {resp.status})",
                            url=str(current),
                            reason=f"HTTP {resp.status}",
                        )
                    length = resp.headers.get("Content-Length")
                    if length and length.isdigit() and int(length) > max_bytes:
                        raise ResponseTooLarge(
                            f"Antwort zu groß ({int(length)} Bytes)", url=str(current), limit=max_bytes
                        )
                    body = bytearray()
                    async for chunk in resp.content.iter_chunked(_CHUNK):
                        body.extend(chunk)
                        if len(body) > max_bytes:
                            raise ResponseTooLarge("Antwort zu groß", url=str(current), limit=max_bytes)
                    content_type = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                    return FetchResult(
                        url=str(current),
                        status=resp.status,
                        content_type=content_type,
                        charset=resp.charset,
                        body=bytes(body),
                    )
            raise FetchFailed("Zu viele Weiterleitungen", url=url, reason="redirects")
    except TimeoutError as err:
        raise FetchFailed("Zeitüberschreitung beim Abruf", url=url, reason="timeout") from err
    except aiohttp.ClientError as err:
        _LOGGER.debug("Abruf von %s fehlgeschlagen: %s", url, err)
        raise FetchFailed("Seite nicht erreichbar", url=url, reason=type(err).__name__) from err
