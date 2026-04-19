#!/usr/bin/env bash
# run.sh — Harvest Copilot CLI sessions and compile into knowledge base.
#
# Usage:
#   ./run.sh              # harvest new + compile changed
#   ./run.sh --all        # re-harvest and recompile everything
#   ./run.sh harvest      # harvest only
#   ./run.sh compile      # compile only

set -euo pipefail
cd "$(dirname "$0")"

CMD="${1:-full}"
FLAG="${2:-}"

case "$CMD" in
  harvest)
    echo "═══ Harvesting sessions ═══"
    uv run python scripts/harvest.py $FLAG
    ;;
  compile)
    echo "═══ Compiling daily logs ═══"
    uv run python scripts/compile.py $FLAG
    ;;
  full|--all)
    if [ "$CMD" = "--all" ]; then
      FLAG="--all"
    fi
    echo "═══ Step 1: Harvesting sessions ═══"
    uv run python scripts/harvest.py $FLAG
    echo ""
    echo "═══ Step 2: Compiling daily logs ═══"
    uv run python scripts/compile.py $FLAG
    echo ""
    echo "═══ Done ═══"
    ;;
  *)
    echo "Usage: ./run.sh [harvest|compile|full|--all]"
    exit 1
    ;;
esac
