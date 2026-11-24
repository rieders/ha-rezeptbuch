"""URL-Normalisierung für Quellen-URLs und Duplikaterkennung."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMS = frozenset(
    {
        "fbclid",
        "gclid",
        "dclid",
        "gbraid",
        "wbraid",
        "msclkid",
        "yclid",
        "igshid",
        "mc_cid",
        "mc_eid",
        "_ga",
        "_gl",
        "ref",
        "ref_src",
        "ref_url",
        "referrer",
        "share",
        "shared",
        "si",
        "spm",
        "cmp",
        "ito",
        "wt_mc",
        "wt.mc_id",
        "ncid",
        "trk",
        "source",
        "s_cid",
        "portal",
    }
)
TRACKING_PREFIXES = ("utm_", "pk_", "mtm_", "at_", "hsa_", "oly_")


class InvalidUrlError(ValueError):
    """Keine gültige http(s)-URL."""


def normalize_url(url: str) -> str:
    """https, Host klein, ohne Tracking-Parameter, ohne Fragment und ohne "/" am Ende."""
    url = (url or "").strip()
    if not url:
        raise InvalidUrlError("Leere URL")
    if "://" not in url:
        url = "https://" + url.lstrip("/")
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    if scheme not in ("http", "https"):
        raise InvalidUrlError(f"Nicht unterstütztes Schema: {parts.scheme}")
    host = (parts.hostname or "").lower()
    if not host or "." not in host:
        raise InvalidUrlError("Ungültiger Host")
    netloc = host
    if parts.port and parts.port not in (80, 443):
        netloc += f":{parts.port}"
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k.lower() not in TRACKING_PARAMS and not k.lower().startswith(TRACKING_PREFIXES)
    ]
    query.sort()
    path = parts.path or ""
    while path.endswith("/"):
        path = path[:-1]
    return urlunsplit(("https", netloc, path, urlencode(query, doseq=True), ""))


def url_key(url: str) -> str:
    """Vergleichsschlüssel für Duplikate: normalisiert, ohne "www." und Schema."""
    normalized = normalize_url(url)
    parts = urlsplit(normalized)
    host = parts.netloc
    if host.startswith(("www.", "m.")):
        host = host.split(".", 1)[1]
    key = host + parts.path
    if parts.query:
        key += "?" + parts.query
    return key.lower()
