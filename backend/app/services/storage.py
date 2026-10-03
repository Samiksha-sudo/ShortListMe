from pathlib import Path

from app.core.config import settings


def _root() -> Path:
    root = Path(settings.storage_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def save(key: str, data: bytes) -> str:
    path = (_root() / key).resolve()
    if _root().resolve() not in path.parents:
        raise ValueError("invalid storage key")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return key
