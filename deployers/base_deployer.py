"""
Interface base (plugin) para todos os deployers.
Novos serviços implementam esta classe sem alterar o core.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class DeployConfig:
    """Configuração genérica de um deployment."""
    name: str
    service: str
    port: int
    extra: dict


@dataclass
class DeployResult:
    success: bool
    url: Optional[str]
    message: str
    compose_dir: Optional[Path] = None


class BaseDeployer(ABC):
    """Contrato que todo deployer deve implementar."""

    @property
    @abstractmethod
    def service_name(self) -> str:
        """Nome canônico do serviço (ex: 'grafana')."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Nome amigável exibido no menu (ex: 'Grafana')."""

    @abstractmethod
    def collect_config(self) -> DeployConfig:
        """Coleta interativamente os parâmetros do usuário via Rich Prompt."""

    @abstractmethod
    def deploy(self, config: DeployConfig) -> DeployResult:
        """Executa o deployment completo."""

    @abstractmethod
    def remove(self, compose_dir: Path, remove_volumes: bool) -> DeployResult:
        """Remove o deployment."""
