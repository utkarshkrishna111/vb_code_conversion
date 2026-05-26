# Step 1 — Analyze & Design

Runs before any Python code is written. For each VB module it produces a
trustworthy architecture blueprint that Steps 2 and 3 build on.

---

## Agents

### 1-A: `UnderstandAgent`

Reads the raw VB source and asks Claude to extract a structured JSON analysis.

**Output (`AnalysisResult`):**

| Field | Description |
|---|---|
| `business_logic` | Plain-English description of each Sub/Function |
| `data_structures` | All UDTs, Classes, Arrays with their fields |
| `com_api_calls` | COM object calls (e.g. `Excel.Application.Open`) |
| `control_flow` | List of procedures, loops, On Error handlers |
| `complexity_score` | 0.0 (trivial) → 1.0 (deeply nested COM + error paths) |
| `raw_summary` | 2–3 sentence human summary |

**Validator A: `ASTChecker`** (runs immediately after)

Uses regex to independently scan the VB source for all `Sub`/`Function`/`Type`/`Class`
definitions and compares them against what the LLM captured. Flags any procedure that
was silently dropped. Also warns about `GoTo` and `On Error` constructs.

---

### 1-B: `DocumentAgent`

Takes the `AnalysisResult` JSON and turns it into a human-readable Markdown spec
saved to disk as `<ModuleName>_spec.md`.

**The Markdown spec always contains:**
1. Overview paragraph
2. Inputs & Outputs table
3. Business Rules — numbered invariants the Python code must honour
4. Data Structures tables
5. Error Conditions
6. Migration Notes — VB idioms needing special attention

---

### 1-C: `ArchitectAgent`

Takes both the analysis JSON and the Markdown spec, then designs the Python
architecture blueprint saved as `<ModuleName>_architecture.json`.

**Output (`ArchitectureDesign`):**

| Field | Description |
|---|---|
| `dataclasses` | Python dataclass definitions replacing VB UDTs |
| `type_hints` | PEP 484 type annotations for all identifiers |
| `module_boundaries` | Top-level Python module names to create |
| `dependency_injection` | Interfaces/protocols for external deps (e.g. COM → injected service) |
| `public_api` | Function signatures + docstrings for every public function |
| `design_notes` | Paragraph on key architectural decisions |

**Validator B: `ArchAuditor`** (runs immediately after)

An LLM audit of the design against these criteria:
1. No global mutable state
2. All public APIs have complete type annotations
3. No VB-isms carried over (GoTo, numeric error codes, Hungarian notation)
4. COM automation replaced by injected abstractions
5. Proper Python OOP (dataclasses/Pydantic, not ad-hoc dicts)
6. No god-modules

---

## Human Gate

Triggered at the end of Step 1 if either condition is true:
- `complexity_score >= threshold` (default 0.7)
- Architecture audit failed

The pipeline pauses and prompts the user to approve or reject the design before
Step 2 begins.

---

## Flow

```
VB source file
     │
     ▼
[UnderstandAgent] ──→ AnalysisResult
     │
     ▼
[ASTChecker] ── warns if procedures were missed
     │
     ▼
[DocumentAgent] ──→ <ModuleName>_spec.md
     │
     ▼
[ArchitectAgent] ──→ <ModuleName>_architecture.json
     │
     ▼
[ArchAuditor] ── flags VB-isms, missing types, bad structure
     │
     ▼
[Human Gate?] ── if complex or audit failed → pause for approval
     │
     ▼
  → Step 2 (generate_tests)
```

---

## Files

| File | Role |
|---|---|
| `understand_agent.py` | 1-A — extracts structured analysis from VB source |
| `document_agent.py` | 1-B — writes Markdown functional spec |
| `architect_agent.py` | 1-C — designs Python architecture blueprint |
| `ast_checker.py` | Validator A — regex cross-check of captured procedures |
| `arch_auditor.py` | Validator B — LLM audit of the architecture design |
