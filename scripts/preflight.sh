#!/usr/bin/env bash
# ==============================================================================
# KrishiNet-BRICS - Preflight Health & Demonstration Readiness Check (Shell Wrapper)
# ==============================================================================
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo -e "${BLUE}${BOLD}===========================================================================${NC}"
echo -e "${BLUE}${BOLD}🚀 KrishiNet-BRICS — Staging & Production Preflight Verification Shell${NC}"
echo -e "${BLUE}${BOLD}===========================================================================${NC}"

# 1. Shell CLI tools verification
echo -e "\n${YELLOW}${BOLD}Checking Core System Utilities:${NC}"
for cmd in curl openssl git; do
  if command -v "$cmd" >/dev/null 2>&1; then
    echo -e "  ${GREEN}[PASS]${NC} Utility '$cmd' is available in PATH"
  else
    echo -e "  ${YELLOW}[WARN]${NC} Utility '$cmd' not found in PATH"
  fi
done

# 2. Python Environment Detection
echo -e "\n${YELLOW}${BOLD}Locating Python 3.10+ Environment:${NC}"
PYTHON_BIN=""

if [[ -f ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
elif [[ -f ".venv/Scripts/python.exe" ]]; then
  PYTHON_BIN=".venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo -e "  ${RED}[FAIL]${NC} No python executable detected! Please activate virtual environment."
  exit 1
fi

echo -e "  ${GREEN}[PASS]${NC} Using Python binary: $PYTHON_BIN"

# 3. Execute Full Python Preflight Suite
echo -e "\n${YELLOW}${BOLD}Executing Diagnostic Test Suite...${NC}\n"
"$PYTHON_BIN" scripts/preflight.py
EXIT_CODE=$?

if [[ $EXIT_CODE -eq 0 ]]; then
  echo -e "${GREEN}${BOLD}Preflight verification successful. Safe to demonstrate or deploy.${NC}"
else
  echo -e "${RED}${BOLD}Preflight verification encountered errors (Exit code: $EXIT_CODE).${NC}"
fi

exit $EXIT_CODE
