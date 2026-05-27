#!/usr/bin/env bash
# run.sh — Interactive launcher for Java → Python Migration Orchestrator
# Usage:  ./run.sh              # fully interactive
#         ./run.sh sample_java/ # pre-fill source dir

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_FOLDER="${DATA_FOLDER:-$HOME/data_code_conversion}"

# ── Colours ───────────────────────────────────────────────────────────────────
bold()   { printf '\033[1m%s\033[0m'  "$*"; }
cyan()   { printf '\033[36m%s\033[0m' "$*"; }
green()  { printf '\033[32m%s\033[0m' "$*"; }
yellow() { printf '\033[33m%s\033[0m' "$*"; }
dim()    { printf '\033[2m%s\033[0m'  "$*"; }
hr()     { printf '%0.s─' {1..60}; printf '\n'; }

# ── Banner ────────────────────────────────────────────────────────────────────
printf '\n'
echo "$(bold '╔══════════════════════════════════════════════════════════╗')"
printf "$(bold '║')  $(cyan 'Java → Python Migration Orchestrator')\n"
echo "$(bold '║')  $(dim 'Hub & Spoke · Test-Driven · MCP Infrastructure')"
echo "$(bold '╚══════════════════════════════════════════════════════════╝')"
printf '\n'

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — Environment setup
# ══════════════════════════════════════════════════════════════════════════════
hr
echo "  $(bold 'PHASE 1 — Environment Setup')"
hr
printf '\n'
printf '  Has the environment been configured? (Python deps, API keys)\n\n'
printf '  %-5s Run setup.sh now\n'      "$(bold 'Y')"
printf '  %-5s Setup already done\n'    "$(bold 'N')"
printf '  %-5s Quit\n\n'                "$(bold 'Q')"

while true; do
    read -rp "  Choice [Y/N/Q]: " _a
    case "${_a^^}" in
        Y)
            printf '\n'
            bash "$SCRIPT_DIR/setup.sh"
            printf '\n'
            break
            ;;
        N)  break ;;
        Q)  printf '\n  Goodbye.\n'; exit 0 ;;
        *)  printf '  %s\n' "$(yellow 'Enter Y, N, or Q')" ;;
    esac
done

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — Source directory
# ══════════════════════════════════════════════════════════════════════════════
printf '\n'
hr
echo "  $(bold 'PHASE 2 — Source Code Location')"
hr
printf '\n'

SOURCE_DIR=""
_preload="${1:-}"

while true; do
    if [ -n "$_preload" ]; then
        _src="$_preload"; _preload=""
    else
        read -rp "  Source directory [sample_java/]: " _src
        _src="${_src:-sample_java/}"
    fi

    printf '\n'
    if [ -d "$_src" ]; then
        _jc=$(find "$_src" -name '*.java' 2>/dev/null | wc -l | tr -d ' ')
        printf '  %s  %s  %s\n\n' "$(green '✓')" "$(bold "$_src")" "$(dim "($_jc .java files)")"
    else
        printf '  %s  Directory %s not found — will be resolved at runtime.\n\n' \
               "$(yellow '⚠')" "$(bold "'$_src'")"
    fi

    while true; do
        read -rp "  Continue with '$(bold "$_src")'? [Y/N/Q]: " _c
        case "${_c^^}" in
            Y|"")  SOURCE_DIR="$_src"; break 2 ;;
            N)     printf '\n'; break ;;
            Q)     printf '\n  Goodbye.\n'; exit 0 ;;
            *)     printf '  %s\n' "$(yellow 'Enter Y, N, or Q')" ;;
        esac
    done
done

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — Pipeline stage selection
# ══════════════════════════════════════════════════════════════════════════════
_proj="$(basename "${SOURCE_DIR%/}")"
OUTPUT_DIR="$DATA_FOLDER/$_proj"
_state_file="$OUTPUT_DIR/migration_state.json"

# Defaults if no state or python unavailable
_status="none"
_suggested="1"
_state_display=""

if [ -f "$_state_file" ] && command -v python3 &>/dev/null; then
    _pyout=$(python3 - "$_state_file" 2>/dev/null <<'PYEOF' || true
import json, sys

MENU_MAP = {
    "pending":         ("1", "Not yet started"),
    "analyzing":       ("1", "Mid-analysis — re-run Step 1"),
    "documented":      ("1", "Analysis done, architecture pending"),
    "architected":     ("2", "Step 1 complete — ready for Step 2"),
    "human_review":    ("2", "Awaiting review — proceed to Step 2"),
    "tests_generated": ("3", "Step 2 complete — ready for Step 3"),
    "converting":      ("3", "Mid-conversion — re-run Step 3"),
    "completed":       ("A", "All steps complete — restart to redo"),
    "failed":          ("1", "Previous run failed — restart Step 1"),
}

try:
    with open(sys.argv[1]) as f:
        state = json.load(f)
except Exception as e:
    print(f"__STATUS__:error")
    print(f"__NEXT__:1")
    print(f"  (Could not read state: {e})")
    sys.exit(0)

modules = state.get("modules", {})
if not modules:
    print("__STATUS__:none")
    print("__NEXT__:1")
    print("  (State file has no module data)")
    sys.exit(0)

last_status = "pending"
last_next   = "1"
for mname, m in modules.items():
    status   = m.get("status", "pending")
    next_s, reason = MENU_MAP.get(status, ("1", "Unknown"))
    arts     = ", ".join(m.get("artifacts", {}).keys()) or "none"
    print(f"  Module : {mname}")
    print(f"  Status : {status}")
    print(f"  Note   : {reason}")
    print(f"  Files  : {arts}")
    print()
    last_status = status
    last_next   = next_s

print(f"__STATUS__:{last_status}")
print(f"__NEXT__:{last_next}")
PYEOF
    )

    _status=$(grep '^__STATUS__:' <<< "$_pyout" 2>/dev/null | head -1 | sed 's/^__STATUS__://' || echo "none")
    _suggested=$(grep '^__NEXT__:' <<< "$_pyout" 2>/dev/null | head -1 | sed 's/^__NEXT__://' || echo "1")
    _state_display=$(grep -v '^__STATUS__:\|^__NEXT__:' <<< "$_pyout" 2>/dev/null || true)
fi

# Sub-step to suggest when user picks option 1 with partial Step 1 progress
_sub_default="1a"
[ "$_status" = "documented" ] && _sub_default="1c"
[ "$_status" = "analyzing"  ] && _sub_default="1a"

printf '\n'
hr
echo "  $(bold 'PHASE 3 — Pipeline Stage')"
hr
printf '\n'
printf '  Project : %s\n'   "$(bold "$_proj")"
printf '  Output  : %s\n\n' "$(bold "$OUTPUT_DIR")"

if [ -n "$_state_display" ]; then
    printf '  %s\n' "$(cyan 'Previous run state:')"
    echo "$_state_display"
else
    printf '  %s\n\n' "$(dim 'No previous state — fresh project.')"
fi

hr
printf '\n  Select a pipeline stage:\n\n'

_sug_tag() { [ "$_suggested" = "$1" ] && printf '  %s' "$(green '◄ suggested')"; printf '\n'; }

printf '  %s  %-22s %s' "$(bold '1.')" 'Analyze & Design'  "$(dim '— understand, document, architect')";  _sug_tag "1"
printf '  %s  %-22s %s' "$(bold '2.')" 'Generate Tests'    "$(dim '— test-driven development')";           _sug_tag "2"
printf '  %s  %-22s %s' "$(bold '3.')" 'Convert & Run'     "$(dim '— generate Python code + execute')";   _sug_tag "3"
printf '  %s  %-22s %s\n' "$(bold 'A.')" 'Restart All'     "$(dim '— wipe state, start from scratch')"
printf '  %s  Quit\n\n'   "$(bold 'Q.')"

START_STEP="1a"

while true; do
    read -rp "  Choice [$_suggested]: " _ch
    _ch="${_ch:-$_suggested}"
    case "${_ch^^}" in
        1)
            if [ "$_status" = "documented" ] || [ "$_status" = "analyzing" ]; then
                printf '\n  %s\n\n' "$(cyan 'Step 1 is partially complete — where to resume?')"
                printf '  %-6s  Re-analyze from scratch\n'   "$(bold '1a')"
                printf '  %-6s  Re-run Document agent\n'     "$(bold '1b')"
                printf '  %-6s  Re-run Architect agent\n\n'  "$(bold '1c')"
                while true; do
                    read -rp "  Sub-step [$_sub_default]: " _ss
                    _ss="${_ss:-$_sub_default}"
                    case "${_ss,,}" in
                        1a) START_STEP="1a"; break ;;
                        1b) START_STEP="1b"; break ;;
                        1c) START_STEP="1c"; break ;;
                        q)  printf '\n  Goodbye.\n'; exit 0 ;;
                        *)  printf '  %s\n' "$(yellow 'Enter 1a, 1b, 1c, or Q')" ;;
                    esac
                done
            else
                START_STEP="1a"
            fi
            break
            ;;
        2)  START_STEP="2";  break ;;
        3)  START_STEP="3";  break ;;
        A)  START_STEP="1a"; break ;;
        Q)  printf '\n  Goodbye.\n'; exit 0 ;;
        *)  printf '  %s\n' "$(yellow 'Enter 1, 2, 3, A, or Q')" ;;
    esac
done

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 4 — Options
# ══════════════════════════════════════════════════════════════════════════════
printf '\n'
hr
echo "  $(bold 'PHASE 4 — Options')"
hr
printf '\n'

MAX_RETRIES=3

read -rp "  Log level (DEBUG/INFO/WARNING) [INFO]: " _l
LOG_LEVEL="${_l:-INFO}"

# ══════════════════════════════════════════════════════════════════════════════
# Summary & launch
# ══════════════════════════════════════════════════════════════════════════════
printf '\n'
hr
printf '\n'
printf '  %-14s %s\n' 'Source:'      "$(bold "$SOURCE_DIR")"
printf '  %-14s %s\n' 'Output:'      "$(bold "$OUTPUT_DIR")"
printf '  %-14s %s\n' 'Start step:'  "$(bold "$START_STEP")"
printf '  %-14s %s\n' 'Max retries:' "$(bold "$MAX_RETRIES")"
printf '  %-14s %s\n' 'Log level:'   "$(bold "$LOG_LEVEL")"
printf '\n'
hr
printf '\n'

while true; do
    read -rp "  $(bold 'Start migration? [Y/N/Q]: ')" _go
    case "${_go^^}" in
        Y|"") break ;;
        N)    printf '\n  Aborted.\n'; exit 0 ;;
        Q)    printf '\n  Goodbye.\n'; exit 0 ;;
        *)    printf '  %s\n' "$(yellow 'Enter Y, N, or Q')" ;;
    esac
done

printf '\n'
cd "$SCRIPT_DIR"
exec python3 main.py "$SOURCE_DIR" \
    --start-step "$START_STEP" \
    --retries    "$MAX_RETRIES" \
    --log-level  "$LOG_LEVEL"
