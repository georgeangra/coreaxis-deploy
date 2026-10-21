#!/usr/bin/env bash
# =============================================================================
#  CoreAxis Deploy — Bootstrap
#  Execute este script em uma VM Ubuntu Server limpa.
#  Ele faz TUDO: atualiza o sistema, instala dependências e sobe o sistema.
#
#  COMO USAR (em uma VM nova, como root ou com sudo):
#
#     curl -fsSL https://raw.githubusercontent.com/georgeangra/coreaxis-deploy/main/bootstrap.sh | sudo bash
#
#  OU se preferir baixar antes de executar:
#
#     wget https://raw.githubusercontent.com/georgeangra/coreaxis-deploy/main/bootstrap.sh
#     sudo bash bootstrap.sh
# =============================================================================
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[AVISO]${RESET} $*"; }
error()   { echo -e "${RED}[ERRO]${RESET}  $*"; exit 1; }

clear
echo -e "${BOLD}${CYAN}"
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║          COREAXIS DEPLOY — BOOTSTRAP         ║"
echo "  ║   Preparando o ambiente do zero...           ║"
echo "  ╚══════════════════════════════════════════════╝"
echo -e "${RESET}"

# ─── Verificar root ───────────────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && error "Execute como root: sudo bash bootstrap.sh"

# ─── 1. Liberar locks e desativar atualizações automáticas ───────────────────
info "Preparando o ambiente..."

# Para e desativa atualizações automáticas que travam o apt
systemctl stop unattended-upgrades 2>/dev/null || true
systemctl disable unattended-upgrades 2>/dev/null || true
systemctl stop apt-daily.service apt-daily-upgrade.service 2>/dev/null || true
systemctl disable apt-daily.timer apt-daily-upgrade.timer 2>/dev/null || true

# Mata processos que seguram locks
kill -9 $(pgrep unattended-upgr) 2>/dev/null || true
kill -9 $(pgrep apt) 2>/dev/null || true
sleep 3

# Remove todos os locks conhecidos
rm -f /var/lib/dpkg/lock-frontend \
      /var/lib/dpkg/lock \
      /var/cache/apt/archives/lock \
      /var/cache/debconf/config.dat-old

# Libera lock do debconf se ainda estiver preso
fuser -k /var/cache/debconf/config.dat 2>/dev/null || true

# Corrige pacotes quebrados antes de qualquer instalação
dpkg --configure -a 2>/dev/null || true
apt-get --fix-broken install -y -qq 2>/dev/null || true
apt-get autoremove -y -qq 2>/dev/null || true

success "Ambiente preparado."

# ─── 2. Atualizar o sistema ───────────────────────────────────────────────────
info "Atualizando o sistema operacional..."
apt-get update -qq
apt-get upgrade -y -qq
success "Sistema atualizado."

# ─── 2. Instalar Git ──────────────────────────────────────────────────────────
info "Instalando Git..."
apt-get install -y -qq git curl
success "Git instalado: $(git --version)"

# ─── 3. Clonar o repositório ──────────────────────────────────────────────────
INSTALL_DIR="/opt/coreaxis-deploy"

if [[ -d "$INSTALL_DIR" ]]; then
    info "Projeto já existe em $INSTALL_DIR. Atualizando..."
    git -C "$INSTALL_DIR" pull
else
    info "Baixando CoreAxis Deploy..."
    git clone https://github.com/georgeangra/coreaxis-deploy.git "$INSTALL_DIR"
fi

success "Projeto disponível em $INSTALL_DIR"

# ─── 4. Rodar o instalador principal ─────────────────────────────────────────
info "Iniciando instalação completa..."
bash "$INSTALL_DIR/install.sh"
