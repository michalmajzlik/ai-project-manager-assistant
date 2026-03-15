from __future__ import annotations

import os
from pathlib import Path

PRIMARY_RUNTIME_DIRNAME = "AIPMAssistant"


def appdata_dir() -> Path:
    return Path(os.getenv("APPDATA", ""))


def primary_runtime_dir() -> Path:
    return appdata_dir() / PRIMARY_RUNTIME_DIRNAME


def resolve_runtime_dir() -> Path:
    return primary_runtime_dir()


def resolve_runtime_file(*parts: str) -> Path:
    relative = Path(*parts)
    return primary_runtime_dir() / relative
