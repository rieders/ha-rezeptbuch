# Windows-Shims (nur lokale Entwicklung)

Home Assistant importiert die Unix-Module `fcntl` und `resource`. Damit die Tests
lokal unter Windows laufen, liegen hier minimale Ersatzmodule.

Sie werden **nicht** automatisch geladen. Lokal unter Windows wird der Ordner über eine
`.pth`-Datei im venv eingebunden:

```powershell
$sp = .venv\Scripts\python -c "import sysconfig; print(sysconfig.get_paths()['purelib'])"
(Resolve-Path tests\win_shims).Path | Out-File -Encoding ascii "$sp\rezeptbuch_win_shims.pth"
```

Unter Linux/CI ist der Ordner nicht im `sys.path`; zusätzlich verweigern beide Module
dort den Import (`ImportError`), damit sie die echten Module nie überdecken können.
Der `socketpair`-Patch in `tests/conftest.py` ist ebenfalls auf `sys.platform == "win32"`
beschränkt.
