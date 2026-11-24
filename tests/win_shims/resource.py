"""Minimaler resource-Ersatz für Tests unter Windows (siehe fcntl.py)."""

import sys

if sys.platform != "win32":  # pragma: no cover - Schutz: echtes Modul nie überdecken
    raise ImportError("tests/win_shims/resource.py ist nur für Windows gedacht")


RLIMIT_NOFILE = 7
RLIM_INFINITY = -1


def getrlimit(resource):
    return (8192, 8192)


def setrlimit(resource, limits):
    return None
