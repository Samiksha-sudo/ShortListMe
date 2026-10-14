from pathlib import Path

from app.core.config import settings


def _root() -> Path:
    root = Path(settings.storage_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def load(key: str) -> bytes:
    path = (_root() / key).resolve()
    if _root().resolve() not in path.parents:
        raise ValueError("invalid storage key")
    return path.read_bytes()


def save(key: str, data: bytes) -> str:
    path = (_root() / key).resolve()
    if _root().resolve() not in path.parents:
        raise ValueError("invalid storage key")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return key


def delete(key: str) -> None:
    path = (_root() / key).resolve()
    if _root().resolve() not in path.parents:
        raise ValueError("invalid storage key")
    path.unlink(missing_ok=True)
