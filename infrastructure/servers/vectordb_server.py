"""
VectorDB MCP Server (Qdrant)

Translation memory: stores and retrieves Java→Python conversion patterns.
Start: python infrastructure/servers/vectordb_server.py [--memory]
"""
import asyncio
import hashlib
import json
import sys
from pathlib import Path

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Add project root to path so config is importable when run as subprocess
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import Config  # noqa: E402

server = Server("vb2py-vectordb")

_client = None
_PointStruct = None
_available = False
_COLLECTION = Config.QDRANT_COLLECTION


def _init_qdrant(use_memory: bool) -> None:
    global _client, _PointStruct, _available
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, PointStruct, VectorParams

        _client = (
            QdrantClient(":memory:")
            if use_memory
            else QdrantClient(url=Config.QDRANT_URL, api_key=Config.QDRANT_API_KEY or None)
        )
        _PointStruct = PointStruct

        existing = {c.name for c in _client.get_collections().collections}
        if _COLLECTION not in existing:
            _client.create_collection(
                collection_name=_COLLECTION,
                vectors_config=VectorParams(size=128, distance=Distance.COSINE),
            )
        _available = True
        sys.stderr.write("VectorDB ready\n")
    except Exception as exc:
        sys.stderr.write(f"VectorDB unavailable — translation memory disabled. ({exc})\n")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="store_pattern",
            description="Store a successfully converted VB→Python pattern in translation memory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "java_snippet": {"type": "string"},
                    "python_snippet": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["java_snippet", "python_snippet", "description"],
            },
        ),
        types.Tool(
            name="search_patterns",
            description="Retrieve the top-k most similar VB→Python patterns from translation memory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "java_snippet": {"type": "string"},
                    "top_k": {"type": "integer", "default": 3},
                },
                "required": ["java_snippet"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    args = arguments or {}

    if name == "store_pattern":
        if _available and _client and _PointStruct:
            vec = _embed(args["java_snippet"])
            point = _PointStruct(
                id=int(hashlib.md5(args["java_snippet"].encode()).hexdigest(), 16) % (2**63),
                vector=vec,
                payload={
                    "java_snippet": args["java_snippet"],
                    "python_snippet": args["python_snippet"],
                    "description": args["description"],
                },
            )
            _client.upsert(collection_name=_COLLECTION, points=[point])
        return [types.TextContent(type="text", text="ok")]

    if name == "search_patterns":
        if not _available or not _client:
            return [types.TextContent(type="text", text=json.dumps([]))]
        vec = _embed(args["java_snippet"])
        hits = _client.search(
            collection_name=_COLLECTION,
            query_vector=vec,
            limit=args.get("top_k", 3),
        )
        return [types.TextContent(type="text", text=json.dumps([h.payload for h in hits]))]

    raise ValueError(f"Unknown tool: {name}")


def _embed(text: str) -> list[float]:
    # Deterministic 128-dim hash embedding.
    # Replace with a real model (e.g. sentence-transformers) in production.
    digest = hashlib.sha512(text.encode()).digest()
    return [(b - 128) / 128.0 for b in digest]


async def main() -> None:
    use_memory = "--memory" in sys.argv
    _init_qdrant(use_memory=use_memory)

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="vb2py-vectordb",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
