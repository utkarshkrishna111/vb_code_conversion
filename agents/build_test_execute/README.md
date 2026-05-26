# `agents/build_test_execute` — Step 2: Test-Driven Development

This package implements **Step 2** of the migration pipeline. It generates the complete test suite for a module *before* any Python application code is written, so the converter in Step 3 is judged against an objective standard derived from the original VB behaviour.

---

## Flow

```
hub_agent._build_test_execute()
    │
    ├── asyncio.gather() ──────────────────────────────────┐
    │       │                                               │
    │   FunctionalTestsAgent.run()               GoldenMasterAgent.run()
    │   (spec + architecture → unit tests)       (spec + I/O data → characterisation tests)
    │       │                                               │
    │       └───────────────────┬───────────────────────────┘
    │                           ▼
    │                   TestAuditor.audit()
    │                   (merge, dedupe, fill gaps → merged test file)
    │                           │
    └────────────────── DryRunRunner.run()
                        pytest --collect-only  (validates syntax, no execution)
```

Both test agents run **simultaneously** via `asyncio.gather()`, cutting generation time roughly in half. Their outputs are merged and improved by the Test Auditor before the Dry Run confirms the file is syntactically valid.

---

## Files

### `functional_tests_agent.py` — Agent 2-A

**Class:** `FunctionalTestsAgent`  
**Input:** `MarkdownSpec`, `ArchitectureDesign`, `output_path`  
**Output:** `TestSuite(test_type="functional")`

Calls the Claude API with the Markdown spec and architecture blueprint. Produces pytest unit tests covering every business rule, boundary condition, and error path. Uses `@pytest.mark.parametrize` for data-driven cases.

```python
suite = FunctionalTestsAgent().run(spec, design, "output/Module/test_Module_functional.py")
```

Output file: `test_{module}_functional.py`

---

### `golden_master_agent.py` — Agent 2-B

**Class:** `GoldenMasterAgent`  
**Input:** `MarkdownSpec`, `output_path`, optional `io_samples: list[dict]`  
**Output:** `TestSuite(test_type="golden_master")`

Creates characterisation tests that assert exact output matches against recorded VB system inputs/outputs. If no real I/O data is provided, it synthesises representative samples from the spec — real data is always stronger.

```python
# With real I/O data
suite = GoldenMasterAgent().run(spec, "output/Module/test_Module_golden.py", io_samples=[...])

# Without — generates synthetic samples
suite = GoldenMasterAgent().run(spec, "output/Module/test_Module_golden.py")
```

Output file: `test_{module}_golden.py`

---

### `test_auditor.py` — Validator

**Class:** `TestAuditor`  
**Input:** `functional: TestSuite`, `golden: TestSuite`, `output_path`  
**Output:** `TestSuite(test_type="merged")`

Reviews both test files with Claude. Removes trivial assertions (`assert True`, `assert 1 == 1`), eliminates over-mocking of business logic, fills coverage gaps identified from the spec, and merges them into a single authoritative file. Logs the before/after test count.

```python
merged = TestAuditor().audit(functional_suite, golden_suite, "output/Module/test_Module.py")
```

Output file: `test_{module}.py` (the merged suite used by Step 3)

---

### `dry_run_runner.py` — Runner

**Class:** `DryRunRunner`  
**Input:** `ExecutionClient` (injected), `TestSuite`  
**Output:** `ValidationResult`

Calls `pytest --collect-only -q` via the Execution MCP client. Validates Python syntax and import paths in the merged test file **without executing any tests** — which would fail because the application code does not exist yet. Failures are logged as non-blocking warnings; Step 3 proceeds regardless.

```python
result = await DryRunRunner(executor).run(merged_suite)
# result.passed — True if all tests collected cleanly
# result.issues — list of collection error lines if False
```

---

## Outputs written to disk

| File | Written by | Used by |
|---|---|---|
| `test_{module}_functional.py` | `FunctionalTestsAgent` | `TestAuditor` |
| `test_{module}_golden.py` | `GoldenMasterAgent` | `TestAuditor` |
| `test_{module}.py` | `TestAuditor` via `FilesystemClient` | Step 3 (`ConverterAgent`, `PytestRunner`) |

The intermediate files (`_functional.py`, `_golden.py`) are kept for traceability. The merged `test_{module}.py` is the authoritative test suite used by the rest of the pipeline.

---

## Providing real I/O samples

Place historical VB input/output data as a JSON file alongside your VB source:

```
your_vb_project/io_samples/InvoiceCalculator_io.json
```

```json
[
  {
    "input":  { "items": [{"qty": 2, "unit_price": 50.0}], "discount_pct": 0.1, "vat_rate": 0.2 },
    "expected_output": 108.0
  }
]
```

Pass the loaded data to `GoldenMasterAgent.run(spec, path, io_samples=data)`. Without it, synthetic samples are generated automatically — still useful but less rigorous than real production data.

---

## What to review after Step 2

Open `output/{module}/test_{module}.py` and check:

- At least one `def test_…` per numbered rule in the Markdown spec
- Boundary values present (zero, max, negative, empty collections)
- `pytest.raises(ExceptionType)` for every error condition in the spec
- No `assert True` or `assert 1 == 1` placeholders
- Golden master parametrize blocks contain realistic values
- `pytest --collect-only output/{module}/test_{module}.py` exits 0
