# `agents/generate_code` — Step 3: Conversion & Closed-Loop Execution

This package implements **Step 3** of the migration pipeline. It generates the Python application code from the architecture blueprint and iterates in a closed self-correction loop until all tests pass or the retry budget is exhausted.

---

## Flow

```
hub_agent._generate_code()
    │
    ├── ConverterAgent.run(design, test_suite, py_path)
    │       └── queries VectorDBClient for similar past patterns
    │       └── calls Claude API → writes {module}.py
    │
    ├── MypyChecker.check(py_path)          ← fast type check before full run
    │       └── ExecutionClient.run_mypy()
    │       │
    │       └── FAIL → previous_error = mypy output
    │                   retry ConverterAgent ──────────────────┐
    │                                                          │
    ├── PytestRunner.run(test_file, module_name)               │
    │       └── ExecutionClient.run_pytest()                   │
    │       │                                                  │
    │       └── PASS → mark COMPLETED, store pattern, create PR│
    │       └── FAIL → previous_error = pytest output          │
    │                   retry ConverterAgent ◄─────────────────┘
    │
    └── (retries exhausted) → escalate to CLI operator
```

The loop runs up to `MAX_RETRIES + 1` times (default: 4 total attempts). On each retry the full error output from mypy or pytest is prepended to the Converter's prompt as context for the fix.

---

## Files

### `converter_agent.py` — Agent 3-A

**Class:** `ConverterAgent`  
**Input:** `ArchitectureDesign`, `TestSuite`, `output_path`, optional `previous_error`, `retry_count`  
**Output:** `ConversionResult`

Calls the Claude API to write a complete, type-annotated Python module that satisfies every function in `design.public_api`. On retry, the previous mypy or pytest error output is included in the prompt with the instruction "Fix ALL failing tests."

Before generating, it queries the **VectorDB translation memory** for previously solved VB→Python patterns similar to the current module. Matching patterns are included in the prompt, reducing re-derivation of common constructs across modules.

```python
# Initial attempt
result = await ConverterAgent(vectordb_client).run(design, test_suite, "output/Module/Module.py")

# Retry with error context
result = await ConverterAgent(vectordb_client).run(
    design, test_suite, "output/Module/Module.py",
    previous_error="E   AssertionError: assert 90.0 == 100.0",
    retry_count=1,
)
```

Output file: `{module}.py`

---

### `mypy_checker.py` — Validator

**Class:** `MypyChecker`  
**Input:** `ExecutionClient` (injected), `python_file_path`, `module_name`  
**Output:** `ValidationResult`

Runs `mypy --strict` on the generated file via the Execution MCP client. Catching type errors here is cheaper than running the full test suite — a single type error typically causes multiple test failures.

```python
result = await MypyChecker(executor).check("output/Module/Module.py", "Module")
# result.passed  — True if mypy exits 0
# result.issues  — list of error lines (e.g. "Module.py:14: error: ...")
# result.details — full mypy stdout for the Converter's retry prompt
```

On failure, `result.details` is passed back to `ConverterAgent` as `previous_error`.

---

### `pytest_runner.py` — Runner

**Class:** `PytestRunner`  
**Input:** `ExecutionClient` (injected), `test_file_path`, `module_name`  
**Output:** `ValidationResult`

Executes the complete merged test suite via the Execution MCP client. On pass, the module is marked `COMPLETED`. On fail, a focused error report is extracted (lines containing `FAILED`, `ERROR`, `AssertionError`, `assert`, or `E `) and returned as `result.details` for the next Converter retry.

```python
result = await PytestRunner(executor).run("output/Module/test_Module.py", "Module")
# result.passed  — True if all tests pass
# result.issues  — filtered error lines
# result.details — full combined output for the Converter's retry prompt
```

---

## Retry logic (in `hub_agent._generate_code`)

```
attempt 0  →  Converter (initial)  →  mypy  →  pytest  →  PASS ✓
attempt 1  →  Converter + mypy_err →  mypy  →  pytest  →  FAIL
attempt 2  →  Converter + pytest_err → mypy →  pytest  →  PASS ✓
attempt 3  →  (not reached)
```

The error routed to the next attempt is always the **most recent** failure output — mypy if mypy failed, pytest if mypy passed but pytest failed. This keeps the error context focused and avoids overwhelming the prompt.

---

## Translation memory

`ConverterAgent` accepts an optional `VectorDBClient`. When provided:

- **On success** (`hub_agent._on_success`): the VB module name and first 500 chars of the generated Python code are stored as a pattern in Qdrant.
- **On next conversion**: similar patterns are retrieved and included in the prompt under `## Translation Memory — Similar Patterns`, giving the Converter examples of already-solved VB constructs.

Without a `VectorDBClient`, the Converter works fine but re-derives every pattern from scratch each time.

---

## Outputs written to disk

| File | Written by | Notes |
|---|---|---|
| `{module}.py` | `ConverterAgent` via `FilesystemClient` | Overwritten on each retry attempt |
| GitHub PR | `hub_agent._on_success` via `GitHubClient` | Created once on first successful run |

---

## What to check in the generated Python file

- All functions listed in `public_api` (from `{module}_architecture.json`) are present
- Full type annotations on every function — `mypy --strict` must exit 0
- No global mutable state (`dict`/`list` at module level)
- Error handling uses `try/except SpecificError`, not bare `except:` or error codes
- External dependencies (DB, file I/O, HTTP) are injected, not hardcoded

```bash
# Manual checks
mypy --strict output/Module/Module.py
pytest -v output/Module/test_Module.py
```
