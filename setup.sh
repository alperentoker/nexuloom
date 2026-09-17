#!/usr/bin/env bash
# ==============================================================================
# Nexuloom - One-Step Setup & Environment Installer Script
# ==============================================================================
set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo -e "${CYAN}====================================================${NC}"
echo -e "${CYAN}       Nexuloom Setup & Environment Installer       ${NC}"
echo -e "${CYAN}====================================================${NC}"

# 1. Check Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[!] Error: Python 3 is not installed. Please install Python >= 3.11.${NC}"
    exit 1
fi

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}[✓] Detected Python $PY_VER${NC}"

# 2. Setup Virtual Environment
if [ ! -d ".venv" ]; then
    echo -e "${CYAN}[*] Creating virtual environment (.venv)...${NC}"
    python3 -m venv .venv
else
    echo -e "${GREEN}[✓] Existing virtual environment found (.venv).${NC}"
fi

# 3. Upgrade pip and install requirements
echo -e "${CYAN}[*] Installing dependencies from requirements.txt...${NC}"
.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install -r requirements.txt --quiet
echo -e "${GREEN}[✓] Dependencies installed successfully.${NC}"

# 4. Make scripts executable
chmod +x main.py nexuloom.py udi.py setup.sh 2>/dev/null || true

# 5. Initialize demo enterprise database if not present
if [ ! -f "data/demo_enterprise.db" ]; then
    echo -e "${CYAN}[*] Initializing demo enterprise database...${NC}"
    .venv/bin/python scripts/seed_demo_db.py
    echo -e "${GREEN}[✓] Enterprise demo database created.${NC}"
fi

# 6. Create symlink in ~/.local/bin
mkdir -p "$HOME/.local/bin"
ln -sf "$PROJECT_DIR/nexuloom.py" "$HOME/.local/bin/nexuloom"
ln -sf "$PROJECT_DIR/udi.py" "$HOME/.local/bin/udi"
echo -e "${GREEN}[✓] Global symlinks created in ~/.local/bin/nexuloom and ~/.local/bin/udi${NC}"

# 7. Run verification tests
echo -e "${CYAN}[*] Running test suite...${NC}"
.venv/bin/pytest tests/ --quiet
echo -e "${GREEN}[✓] All 29 verification tests passed!${NC}"

echo -e "\n${CYAN}====================================================${NC}"
echo -e "${GREEN}Nexuloom is ready to use!${NC}"
echo -e "${CYAN}Try the following commands:${NC}"
echo -e "  nexuloom health                  # Check platform health"
echo -e "  nexuloom inspect --database demo_enterprise  # Inspect schema"
echo -e "  nexuloom profile --database demo_enterprise --table orders"
echo -e "  python main.py                   # Launch Web Dashboard on http://localhost:8000"
echo -e "${CYAN}====================================================${NC}"
