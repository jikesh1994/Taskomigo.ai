from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from app.storage.base import ObjectNotFoundError, StorageError, validate_key


class LocalStorage:
    """Stores objects as files under a root directory (development / single host)."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / validate_key(key)).resolve()
        if self.root not in path.parents:
            raise ValueError(f"Invalid storage key: {key!r}")
        return path

    async def put(self, key: str, data: bytes, *, content_type: str) -> None:
        await asyncio.to_thread(self._write, self._path(key), data)

    async def get(self, key: str) -> bytes:
        path = self._path(key)
        try:
            return await asyncio.to_thread(path.read_bytes)
        except FileNotFoundError as exc:
            raise ObjectNotFoundError(key) from exc
        except OSError as exc:
            raise StorageError(str(exc)) from exc

    async def delete(self, key: str) -> None:
        path = self._path(key)
        try:
            await asyncio.to_thread(path.unlink, True)
        except OSError as exc:
            raise StorageError(str(exc)) from exc

    @staticmethod
    def _write(path: Path, data: bytes) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            # Write to a temp file and rename, so readers never see a partial object.
            fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".upload-")
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(data)
                os.replace(tmp, path)
            except BaseException:
                Path(tmp).unlink(missing_ok=True)
                raise
        except OSError as exc:
            raise StorageError(str(exc)) from exc
