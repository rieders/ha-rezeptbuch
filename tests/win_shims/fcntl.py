"""Minimaler fcntl-Ersatz, damit Home Assistant (runner.py) unter Windows für Tests importierbar ist.

Wird nur lokal unter Windows über eine .pth-Datei im venv eingebunden; unter Linux/CI ungenutzt.
"""

import sys

if sys.platform != "win32":  # pragma: no cover - Schutz: echtes Modul nie überdecken
    raise ImportError("tests/win_shims/fcntl.py ist nur für Windows gedacht")


LOCK_EX = 2
LOCK_NB = 4
LOCK_UN = 8
LOCK_SH = 1


def flock(fd, operation):
    return None


def fcntl(fd, cmd, arg=0):
    return 0


def ioctl(fd, request, arg=0, mutate_flag=True):
    return 0


def lockf(fd, cmd, length=0, start=0, whence=0):
    return None
