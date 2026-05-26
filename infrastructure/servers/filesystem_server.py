"""
Filesystem MCP Server

Exposes file I/O operations as MCP tools over stdio transport.
Start: python infrastructure/servers/filesystem_server.py <base_dir>
"""
import asyncio
import json
import sys
from pathlib import Path

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

server = Server("vb2py-filesystem")

_base_dir: Path = Path(".").resolve()


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="read_text",
            description="Read a text file and return its contents.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or base-relative file path"},
                },
                "required": ["path"],
            },
        ),
        types.Tool(
            name="write_text",
            description="Write text content to a file, creating parent directories as needed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        ),
        types.Tool(
            name="read_json",
            description="Read a file and parse it as JSON, returning the raw JSON string.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                },
                "required": ["path"],
            },
        ),
        types.Tool(
            name="write_json",
            description="Serialise a JSON-compatible object and write it to a file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "data": {"type": "object"},
                },
                "required": ["path", "data"],
            },
        ),
        types.Tool(
            name="list_files",
            description="List files under the base directory matching a glob pattern.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern (default **/*)", "default": "**/*"},
                },
                "required": [],
            },
        ),
        types.Tool(
            name="find_java_files",
            description="Recursively find all Java source files (.java) under a directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_dir": {"type": "string"},
                },
                "required": ["source_dir"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    args = arguments or {}

    if name == "read_text":
        text = _resolve(args["path"]).read_text(encoding="utf-8")
        return [types.TextContent(type="text", text=text)]

    if name == "write_text":
        path = _resolve(args["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args["content"], encoding="utf-8")
        return [types.TextContent(type="text", text=str(path))]

    if name == "read_json":
        text = _resolve(args["path"]).read_text(encoding="utf-8")
        return [types.TextContent(type="text", text=text)]

    if name == "write_json":
        path = _resolve(args["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(args["data"], indent=2), encoding="utf-8")
        return [types.TextContent(type="text", text=str(path))]

    if name == "list_files":
        pattern = args.get("pattern", "**/*")
        files = [str(p) for p in _base_dir.glob(pattern) if p.is_file()]
        return [types.TextContent(type="text", text=json.dumps(files))]

    if name == "find_java_files":
        source_dir = Path(args["source_dir"])
        found = [str(p) for p in source_dir.rglob("*.java")]
        return [types.TextContent(type="text", text=json.dumps(found))]

    raise ValueError(f"Unknown tool: {name}")


def _resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else _base_dir / p


async def main() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="vb2py-filesystem",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        _base_dir = Path(sys.argv[1]).resolve()
    asyncio.run(main())
