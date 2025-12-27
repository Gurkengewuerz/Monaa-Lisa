import os
from pathlib import Path
import configparser

"""
21-September-2025 - Basti
Abstract: Handles reading from config.ini and environment variables.
"""
class AppConfig:
    def __init__(self):
        self._config = configparser.ConfigParser()
        self._path = self._resolve_path()
        if self._path and self._path.exists():
            self._config.read(self._path)

    def _resolve_path(self) -> Path | None:
        env_path = os.getenv("CONFIG_INI_PATH")
        if env_path:
            return Path(env_path)
        candidates = [
            Path("/app/config.ini"),
            Path(__file__).resolve().parents[1] / "config.ini",
        ]
        for p in candidates:
            if p.exists():
                return p
        return candidates[-1]  # default location even if not present yet

    def get(self, section: str, option: str, default: str | None = None) -> str | None:
        try:
            return self._config.get(section, option)
        except Exception:
            return default

    def get_int(self, section: str, option: str, default: int) -> int:
        try:
            return self._config.getint(section, option)
        except Exception:
            return default

    def get_float(self, section: str, option: str, default: float) -> float:
        try:
            return self._config.getfloat(section, option)
        except Exception:
            return default

    def get_bool(self, section: str, option: str, default: bool) -> bool:
        try:
            return self._config.getboolean(section, option)
        except Exception:
            return default


# Singleton instance to import elsewhere
cfg = AppConfig()
