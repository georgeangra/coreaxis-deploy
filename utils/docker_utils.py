"""
Utilitários para operações Docker: up, down, ps, logs.
"""
import subprocess
from pathlib import Path
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


def _run(cmd: list[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    logger.debug("Executando: %s", " ".join(cmd))
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(cwd) if cwd else None
    )
    if result.stdout:
        logger.debug("stdout: %s", result.stdout.strip())
    if result.stderr:
        logger.debug("stderr: %s", result.stderr.strip())
    return result


def compose_up(compose_dir: Path) -> tuple[bool, str]:
    """Executa docker compose up -d no diretório informado."""
    result = _run(["docker", "compose", "up", "-d"], cwd=compose_dir)
    if result.returncode != 0:
        # Fallback para docker-compose v1
        result = _run(["docker-compose", "up", "-d"], cwd=compose_dir)
    success = result.returncode == 0
    output = result.stdout + result.stderr
    return success, output


def compose_down(compose_dir: Path, remove_volumes: bool = False) -> tuple[bool, str]:
    """Executa docker compose down, opcionalmente removendo volumes."""
    cmd = ["docker", "compose", "down"]
    if remove_volumes:
        cmd.append("-v")
    result = _run(cmd, cwd=compose_dir)
    if result.returncode != 0:
        cmd[0:2] = ["docker-compose"]
        result = _run(cmd, cwd=compose_dir)
    return result.returncode == 0, result.stdout + result.stderr


def docker_ps() -> list[dict]:
    """Retorna lista de containers em execução."""
    result = _run([
        "docker", "ps",
        "--format", "{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}|{{.RunningFor}}"
    ])
    containers = []
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split("|")
        if len(parts) == 5:
            containers.append({
                "name": parts[0],
                "image": parts[1],
                "status": parts[2],
                "ports": parts[3],
                "uptime": parts[4],
            })
    return containers


def get_machine_ip() -> str:
    """Retorna o IP principal da máquina na rede local."""
    import socket
    try:
        # Abre conexão UDP fictícia para descobrir o IP da interface ativa
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def docker_logs(container_name: str, tail: int = 100) -> str:
    """Retorna os últimos logs de um container."""
    result = _run(["docker", "logs", "--tail", str(tail), container_name])
    return result.stdout + result.stderr
