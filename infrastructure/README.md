# Infrastructure — MCP Servers & Clients

This package contains the real **Model Context Protocol (MCP)** infrastructure for the Java → Python migration pipeline. It is split into two sub-packages that mirror each other: `servers/` and `clients/`.

---

## How it fits into the pipeline

```
agents/hub_agent.py
    │
    │  AsyncExitStack (4 clients started on enter, stopped on exit)
    ├── FilesystemClient  ──stdio──►  filesystem_server.py  (subprocess)
    ├── ExecutionClient   ──stdio──►  execution_server.py   (subprocess)
    ├── VectorDBClient    ──stdio──►  vectordb_server.py    (subprocess)
    └── GitHubClient      ──stdio──►  github_server.py      (subprocess)
```

Each client spawns its matching server as a **child process** connected over `stdin`/`stdout` (MCP stdio transport). The Hub Agent calls typed methods on the client; the client translates each call into an MCP `call_tool` RPC, sends it to the server over the pipe, and returns the result. You never start or stop the servers manually — `HubAgent.run()` manages them for the entire migration.

---

## `servers/` — MCP server processes

Each file is a standalone Python script that registers MCP tools and runs the `mcp.server.stdio.stdio_server()` event loop.

| File | MCP server name | Tools exposed |
|---|---|---|
| `filesystem_server.py` | `vb2py-filesystem` | `read_text`, `write_text`, `read_json`, `write_json`, `list_files`, `find_java_files` |
| `execution_server.py` | `vb2py-execution` | `run_pytest_collect`, `run_pytest`, `run_mypy` |
| `vectordb_server.py` | `vb2py-vectordb` | `store_pattern`, `search_patterns` |
| `github_server.py` | `vb2py-github` | `create_pr` |

### Running a server manually (for debugging)

```bash
# Filesystem server — base_dir is the directory it is allowed to read/write
python infrastructure/servers/filesystem_server.py output/

# Execution server — working_dir is where pytest/mypy are invoked
python infrastructure/servers/execution_server.py output/

# VectorDB server — pass --memory to use in-memory Qdrant (no Docker needed)
python infrastructure/servers/vectordb_server.py --memory

# GitHub server — reads GITHUB_TOKEN + GITHUB_REPO from environment
python infrastructure/servers/github_server.py
```

The server starts and waits for MCP JSON-RPC messages on `stdin`. Send `Ctrl-C` to stop it.

---

## `clients/` — typed async wrappers

Each client is an **async context manager** that spawns its server and exposes typed Python methods. Internally it uses `mcp.client.stdio.stdio_client()` + `ClientSession` from the `mcp` SDK.

| File | Wraps | Key methods |
|---|---|---|
| `base_client.py` | — | `_call(tool, **kwargs)` helper used by all subclasses |
| `filesystem_client.py` | `filesystem_server.py` | `read_text()`, `write_text()`, `read_json()`, `write_json()`, `list_files()`, `find_java_files()` |
| `execution_client.py` | `execution_server.py` | `run_pytest_collect()`, `run_pytest()`, `run_mypy()` |
| `vectordb_client.py` | `vectordb_server.py` | `store_pattern()`, `search_patterns()` |
| `github_client.py` | `github_server.py` | `create_pr()` |

### Usage pattern (from `hub_agent.py`)

```python
from contextlib import AsyncExitStack
from infrastructure.clients.filesystem_client import FilesystemClient
from infrastructure.clients.execution_client import ExecutionClient

async with AsyncExitStack() as stack:
    fs       = await stack.enter_async_context(FilesystemClient(output_dir))
    executor = await stack.enter_async_context(ExecutionClient(output_dir))

    content = await fs.read_text("some/file.py")     # → str
    result  = await executor.run_pytest("test_x.py") # → ExecResult
```

### `BaseMCPClient` — how the subprocess is launched

`base_client.py` handles the common lifecycle for all four clients:

1. **`__aenter__`** — builds `StdioServerParameters` with `sys.executable` (same Python as the parent) and injects `PYTHONPATH=<project_root>` so the server subprocess can import `config`, `utils`, etc.
2. Calls `stdio_client(params)` to start the process and get `(read_stream, write_stream)`.
3. Opens a `ClientSession`, calls `session.initialize()` to complete the MCP handshake.
4. **`__aexit__`** — tears down the session and the stdio streams, which terminates the subprocess cleanly.

```
BaseMCPClient.__aenter__
  └── StdioServerParameters(command=sys.executable, args=[server_script, ...], env={PYTHONPATH: ...})
        └── stdio_client(params)           # spawns subprocess, returns (read, write)
              └── ClientSession(read, write).initialize()   # MCP handshake
```

---

## Qdrant (VectorDB) — in-memory vs persistent

The VectorDB server starts in **in-memory mode** by default (`use_memory=True`), so no Docker is required. Translation memory (solved Java→Python patterns) is stored for the duration of the run but is lost when the process exits.

For persistent memory across multiple migration runs:

```bash
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant
```

Then set in `.env`:
```
QDRANT_URL=http://localhost:6333
```

---

## GitHub integration

`github_server.py` uses `PyGithub` to create a feature branch and pull request for each successfully migrated module. It is completely optional — if `GITHUB_TOKEN` or `GITHUB_REPO` are not set, `create_pr` returns `null` and the pipeline continues silently.

Required `.env` variables:
```
GITHUB_TOKEN=ghp_...        # scope: repo
GITHUB_REPO=owner/repo-name
```
