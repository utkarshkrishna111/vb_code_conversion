"""
Filesystem MCP Client

Typed async wrapper around the vb2py-filesystem MCP server.
"""
from __future__ import annotations

import json
from pathlib import Path

from infrastructure.clients.base_client import BaseMCPClient

_SERVER = str(Path(__file__).parent.parent / "servers" / "filesystem_server.py")


class FilesystemClient(BaseMCPClient):
    server_script = _SERVER

    def __init__(self, base_dir: str | Path) -> None:
        super().__init__(str(base_dir))

    async def read_text(self, path: str) -> str:
        return await self._call("read_text", path=path)

    async def write_text(self, path: str, content: str) -> str:
        return await self._call("write_text", path=path, content=content)

    async def read_json(self, path: str) -> dict:
        raw = await self._call("read_json", path=path)
        return json.loads(raw)

    async def write_json(self, path: str, data: dict) -> str:
        return await self._call("write_json", path=path, data=data)

    async def list_files(self, pattern: str = "**/*") -> list[str]:
        raw = await self._call("list_files", pattern=pattern)
        return json.loads(raw)

    async def find_java_files(self, source_dir: str | Path) -> list[Path]:
        raw = await self._call("find_java_files", source_dir=str(source_dir))
        return [Path(p) for p in json.loads(raw)]
