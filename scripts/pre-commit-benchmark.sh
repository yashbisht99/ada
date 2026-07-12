#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# ADA Pre-Commit Benchmark Hook
# Runs a lightweight benchmark check before each commit.
# Install: cp scripts/pre-commit-benchmark.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
# ──────────────────────────────────────────────────────────────────────

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
BENCHMARK_SCRIPT="$PROJECT_ROOT/scratch/ada_ai_benchmark.py"
REPORT_FILE="$PROJECT_ROOT/reports/ada_benchmark_report.json"
THRESHOLD=${BENCHMARK_THRESHOLD:-80}

# Only run if the benchmark script or backend modules changed
CHANGED_FILES=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || echo "")

# Check if any relevant files changed
SHOULD_RUN=false
if echo "$CHANGED_FILES" | grep -q "^backend/"; then
    SHOULD_RUN=true
fi
if echo "$CHANGED_FILES" | grep -q "^scratch/ada_ai_benchmark"; then
    SHOULD_RUN=true
fi
if echo "$CHANGED_FILES" | grep -q "^tests/"; then
    SHOULD_RUN=true
fi

if [ "$SHOULD_RUN" = false ]; then
    echo -e "${YELLOW}[benchmark] No backend/test changes detected — skipping benchmark.${NC}"
    exit 0
fi

echo -e "${YELLOW}[benchmark] Running AI benchmark suite (threshold: ${THRESHOLD}%)...${NC}"

# Activate virtualenv if it exists
if [ -f "$PROJECT_ROOT/venv_cad/bin/activate" ]; then
    source "$PROJECT_ROOT/venv_cad/bin/activate"
fi

# Run the benchmark
if ! python "$BENCHMARK_SCRIPT" 2>&1 | tail -50; then
    echo -e "${RED}[benchmark] Benchmark script failed to execute.${NC}"
    exit 1
fi

# Check the results
if [ ! -f "$REPORT_FILE" ]; then
    echo -e "${RED}[benchmark] No report file generated — benchmark may have crashed.${NC}"
    exit 1
fi

# Parse results
PASS_RATE=$(python3 -c "import json; r=json.load(open('$REPORT_FILE')); print(f\"{r['pass_rate']:.1f}\")")
GRADE=$(python3 -c "import json; r=json.load(open('$REPORT_FILE')); print(r['grade'])")
FAILED=$(python3 -c "import json; r=json.load(open('$REPORT_FILE')); print(r['failed'])")

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Benchmark Results: ${PASS_RATE}% pass rate (Grade: ${GRADE})"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check threshold
python3 -c "
import json, sys
r = json.load(open('$REPORT_FILE'))
threshold = float('$THRESHOLD')
if r['pass_rate'] < threshold:
    print(f'')
    print(f'  ❌ BLOCKED: Pass rate {r[\"pass_rate\"]:.1f}% is below {threshold}% threshold')
    print(f'  Fix the failing tests before committing.')
    print(f'')
    print(f'  Failed tests:')
    for res in r['results']:
        if not res['passed']:
            print(f'    - {res[\"name\"]} ({res[\"category\"]}): {res[\"score\"]:.0%}')
    sys.exit(1)
else:
    print(f'')
    print(f'  ✅ PASS: {r[\"pass_rate\"]:.1f}% >= {threshold}% threshold')
    print(f'')
    sys.exit(0)
"

exit $?
