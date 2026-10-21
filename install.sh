#!/usr/bin/env bash
# =============================================================================
#  CoreAxis Deploy — Script de Instalação Automática
#  Compatível com: Ubuntu Server 22.04 / 24.04 e Debian 12
# =============================================================================
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# ─── Cores ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERRO]${RESET}  $*"; exit 1; }

# ─── Banner ──────────────────────────────────────────────────────────────────
clear
echo -e "${BOLD}${CYAN}"
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║          COREAXIS DEPLOY — INSTALLER         ║"
echo "  ║     Provisionamento de Infraestrutura        ║"
echo "  ╚══════════════════════════════════════════════╝"
echo -e "${RESET}"

# ─── Verificações iniciais ───────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && error "Execute como root: sudo bash install.sh"

DISTRO=$(. /etc/os-release && echo "$ID")
[[ "$DISTRO" != "ubuntu" && "$DISTRO" != "debian" ]] && \
    warn "Distro '$DISTRO' não testada. Continuando mesmo assim..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_ROOT_PASS="CoreAxisRoot2024!"
DB_NAME="coreaxis_deploy"
DB_USER="coreaxis"
DB_PASS="SenhaForte"

# ─── 1. Atualizar sistema ─────────────────────────────────────────────────────
info "Atualizando lista de pacotes..."
apt-get update -qq

# ─── 2. Instalar dependências do sistema ──────────────────────────────────────
info "Instalando dependências do sistema..."
apt-get install -y -qq \
    curl wget gnupg2 ca-certificates lsb-release \
    software-properties-common apt-transport-https \
    python3 python3-pip python3-venv python3-dev \
    mariadb-server mariadb-client \
    git unzip net-tools > /dev/null

success "Dependências do sistema instaladas."

# ─── 3. Docker ────────────────────────────────────────────────────────────────
info "Verificando Docker..."
if command -v docker &>/dev/null; then
    success "Docker já instalado: $(docker --version)"
else
    info "Instalando Docker Engine..."
    curl -fsSL https://get.docker.com | sh > /dev/null 2>&1
    success "Docker instalado: $(docker --version)"
fi

# Habilitar e iniciar Docker
systemctl enable docker --quiet
systemctl start docker
success "Docker daemon ativo."

# Adicionar usuário atual ao grupo docker (se não for root)
SUDO_USER_NAME="${SUDO_USER:-}"
if [[ -n "$SUDO_USER_NAME" ]]; then
    usermod -aG docker "$SUDO_USER_NAME"
    info "Usuário '$SUDO_USER_NAME' adicionado ao grupo docker."
fi

# ─── 4. Docker Compose ────────────────────────────────────────────────────────
info "Verificando Docker Compose..."
if docker compose version &>/dev/null; then
    success "Docker Compose (plugin) disponível."
elif command -v docker-compose &>/dev/null; then
    success "docker-compose (v1) disponível."
else
    info "Instalando Docker Compose plugin..."
    apt-get install -y -qq docker-compose-plugin > /dev/null
    success "Docker Compose instalado."
fi

# ─── 5. MariaDB ───────────────────────────────────────────────────────────────
info "Configurando MariaDB..."
systemctl enable mariadb --quiet
systemctl start mariadb

# Criar banco, usuário e tabelas
mariadb -u root <<SQL
ALTER USER 'root'@'localhost' IDENTIFIED BY '${DB_ROOT_PASS}';
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\`
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL

success "MariaDB configurado. Banco '${DB_NAME}' criado."

# ─── 6. Arquivo .env ──────────────────────────────────────────────────────────
info "Gerando arquivo .env..."
cat > "$SCRIPT_DIR/.env" <<ENV
DB_HOST=localhost
DB_PORT=3306
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASS}
ENV
success ".env criado."

# ─── 7. Ambiente Python virtual ───────────────────────────────────────────────
info "Criando ambiente virtual Python..."
python3 -m venv "$SCRIPT_DIR/.venv"
source "$SCRIPT_DIR/.venv/bin/activate"

info "Instalando dependências Python..."
pip install --quiet --upgrade pip
pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
success "Dependências Python instaladas."

# ─── 8. Inicializar banco via SQLAlchemy ──────────────────────────────────────
info "Inicializando schema do banco..."
python3 - <<PYINIT
import sys
sys.path.insert(0, "$SCRIPT_DIR")
from database.init_db import init_db
init_db()
print("Schema criado com sucesso.")
PYINIT
success "Banco de dados inicializado."

# ─── 9. Permissões de diretórios ──────────────────────────────────────────────
mkdir -p "$SCRIPT_DIR/logs" "$SCRIPT_DIR/docker/grafana" "$SCRIPT_DIR/docker/zabbix"
[[ -n "$SUDO_USER_NAME" ]] && chown -R "$SUDO_USER_NAME":"$SUDO_USER_NAME" "$SCRIPT_DIR"

# ─── 10. Tornar run.sh executável ─────────────────────────────────────────────
chmod +x "$SCRIPT_DIR/run.sh" 2>/dev/null || true

# ─── Resumo final ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}"
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║         INSTALAÇÃO CONCLUÍDA COM SUCESSO     ║"
echo "  ╚══════════════════════════════════════════════╝"
echo -e "${RESET}"
echo -e "  ${BOLD}MariaDB${RESET}       → usuário: ${CYAN}${DB_USER}${RESET} / banco: ${CYAN}${DB_NAME}${RESET}"
echo -e "  ${BOLD}Docker${RESET}        → $(docker --version)"
echo -e "  ${BOLD}Python${RESET}        → $(python3 --version)"
echo ""
echo -e "  Para iniciar o sistema:"
echo -e "  ${BOLD}${CYAN}  bash ${SCRIPT_DIR}/run.sh${RESET}"
echo ""
