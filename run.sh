#!/usr/bin/env bash
# =============================================================================
#  CoreAxis Deploy — Script de Inicialização
# =============================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'
BOLD='\033[1m'; RESET='\033[0m'

# Suporta tanto /opt/coreaxis-deploy quanto o diretório local
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"

# Verificar venv
if [[ ! -f "$VENV/bin/activate" ]]; then
    echo -e "${RED}[ERRO]${RESET} Ambiente virtual não encontrado."
    echo -e "Execute primeiro: ${BOLD}sudo bash install.sh${RESET}"
    exit 1
fi

# Verificar serviços
if ! systemctl is-active --quiet mariadb 2>/dev/null; then
    echo -e "${CYAN}[INFO]${RESET}  Iniciando MariaDB..."
    sudo systemctl start mariadb
fi

if ! systemctl is-active --quiet docker 2>/dev/null; then
    echo -e "${CYAN}[INFO]${RESET}  Iniciando Docker..."
    sudo systemctl start docker
fi

# Ativar venv e rodar
source "$VENV/bin/activate"
echo -e "${GREEN}[OK]${RESET}    Iniciando CoreAxis Deploy..."
python3 "$SCRIPT_DIR/main.py"
