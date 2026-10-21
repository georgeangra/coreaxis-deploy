"""
Validações de pré-requisitos do sistema e entradas do usuário.
"""
import shutil
import socket
import subprocess
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class PrerequisiteError(Exception):
    """Falha em pré-requisito obrigatório."""


def _command_exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def check_docker() -> None:
    if not _command_exists("docker"):
        raise PrerequisiteError(
            "Docker não encontrado. Execute: curl -fsSL https://get.docker.com | sudo sh"
        )

    # Tenta acessar o socket diretamente antes de chamar docker info
    import os
    socket_path = "/var/run/docker.sock"
    if os.path.exists(socket_path) and not os.access(socket_path, os.R_OK):
        raise PrerequisiteError(
            "Sem permissão para acessar o Docker. Execute:\n"
            "  sudo usermod -aG docker $USER && newgrp docker\n"
            "Ou rode o sistema com: sudo bash run.sh"
        )

    result = subprocess.run(
        ["docker", "info"], capture_output=True, text=True
    )
    if result.returncode != 0:
        # Tenta iniciar automaticamente (Ubuntu Server com systemctl)
        start = subprocess.run(
            ["sudo", "systemctl", "start", "docker"],
            capture_output=True, text=True
        )
        if start.returncode != 0:
            # Fallback para service (WSL/Debian sem systemd)
            subprocess.run(["sudo", "service", "docker", "start"], capture_output=True)

        # Verifica novamente
        retry = subprocess.run(["docker", "info"], capture_output=True, text=True)
        if retry.returncode != 0:
            raise PrerequisiteError(
                "O serviço Docker não está ativo.\n"
                "  Ubuntu Server: sudo systemctl start docker\n"
                "  WSL:           sudo service docker start"
            )
    logger.info("Docker verificado: OK")


def check_docker_compose() -> None:
    # Suporta plugin v2 (docker compose) e binário v1 (docker-compose)
    result = subprocess.run(
        ["docker", "compose", "version"], capture_output=True, text=True
    )
    if result.returncode != 0:
        if not _command_exists("docker-compose"):
            raise PrerequisiteError(
                "Docker Compose não encontrado. Instale o plugin: sudo apt install docker-compose-plugin"
            )
    logger.info("Docker Compose verificado: OK")


def check_python_version() -> None:
    import sys
    if sys.version_info < (3, 12):
        raise PrerequisiteError(
            f"Python 3.12+ obrigatório. Versão atual: {sys.version}"
        )
    logger.info("Python verificado: %s", sys.version)


def check_port_available(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        result = s.connect_ex(("localhost", port))
        if result == 0:
            raise PrerequisiteError(
                f"Porta {port} já está em uso. Escolha outra porta."
            )
    logger.info("Porta %d disponível: OK", port)


def check_db_connection() -> None:
    from config.settings import settings
    import pymysql

    try:
        conn = pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            connect_timeout=5,
        )
        conn.close()
        logger.info("Conexão com MariaDB verificada: OK")
    except Exception as exc:
        raise PrerequisiteError(
            f"Não foi possível conectar ao MariaDB: {exc}\n"
            "Verifique as credenciais no arquivo .env e se o MariaDB está rodando."
        )


def validate_port(value: str) -> int:
    try:
        port = int(value)
        if not (1024 <= port <= 65535):
            raise ValueError
        return port
    except ValueError:
        raise ValueError(f"Porta inválida: '{value}'. Use um número entre 1024 e 65535.")


def validate_non_empty(value: str, field: str) -> str:
    if not value.strip():
        raise ValueError(f"O campo '{field}' não pode ser vazio.")
    return value.strip()
