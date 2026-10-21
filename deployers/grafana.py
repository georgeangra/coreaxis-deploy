"""
Deployer do Grafana via Docker Compose.
"""
import yaml
from pathlib import Path
from rich.prompt import Prompt
from rich.console import Console
from deployers.base_deployer import BaseDeployer, DeployConfig, DeployResult
from utils.docker_utils import compose_up, compose_down, get_machine_ip
from utils.validators import validate_port, validate_non_empty, check_port_available
from utils.logger import get_logger
from config.settings import settings

console = Console()
logger = get_logger(__name__)


class GrafanaDeployer(BaseDeployer):
    @property
    def service_name(self) -> str:
        return "grafana"

    @property
    def display_name(self) -> str:
        return "Grafana"

    def collect_config(self) -> DeployConfig:
        console.print("\n[bold cyan]══ Configuração do Grafana ══[/bold cyan]\n")

        machine_ip = get_machine_ip()
        console.print(
            f"[bold yellow]⚠  IP detectado:[/bold yellow] [white]{machine_ip}[/white]\n"
            "[dim]Se estiver em VirtualBox e o IP aparecer como 10.0.2.x ou 127.x,\n"
            "configure a VM em modo Bridge: Configurações → Rede → Placa em modo Bridge.\n"
            "Assim a VM recebe um IP real da sua rede e fica acessível de outros dispositivos.[/dim]\n"
        )

        name = validate_non_empty(
            Prompt.ask("[green]Nome da Instância[/green]", default="Grafana-Lab"), "Nome"
        )
        port_str = Prompt.ask("[green]Porta[/green]", default="3000")
        port = validate_port(port_str)
        check_port_available(port)

        admin_user = validate_non_empty(
            Prompt.ask("[green]Usuário Administrador[/green]", default="admin"), "Usuário"
        )
        admin_pass = Prompt.ask(
            "[green]Senha Administrador[/green]", default="admin123", password=True
        )
        validate_non_empty(admin_pass, "Senha")

        return DeployConfig(
            name=name,
            service=self.service_name,
            port=port,
            extra={"admin_user": admin_user, "admin_pass": admin_pass},
        )

    def _generate_compose(self, config: DeployConfig, compose_dir: Path) -> None:
        compose_data = {
            "version": "3.8",
            "services": {
                "grafana": {
                    "image": "grafana/grafana:latest",
                    "container_name": f"grafana_{config.name.lower().replace(' ', '_')}",
                    "restart": "unless-stopped",
                    "ports": [f"{config.port}:3000"],
                    "environment": {
                        "GF_SECURITY_ADMIN_USER": config.extra["admin_user"],
                        "GF_SECURITY_ADMIN_PASSWORD": config.extra["admin_pass"],
                        "GF_USERS_ALLOW_SIGN_UP": "false",
                        "GF_DEFAULT_LOCALE": "pt-BR",
                        "GF_DATE_FORMATS_DEFAULT_TIMEZONE": "America/Sao_Paulo",
                    },
                    "volumes": [
                        f"grafana_data_{config.name}:/var/lib/grafana"
                    ],
                }
            },
            "volumes": {
                f"grafana_data_{config.name}": None,
            },
        }

        compose_dir.mkdir(parents=True, exist_ok=True)
        with open(compose_dir / "docker-compose.yml", "w") as f:
            yaml.dump(compose_data, f, default_flow_style=False, allow_unicode=True)

        logger.info("docker-compose.yml gerado em %s", compose_dir)

    def deploy(self, config: DeployConfig) -> DeployResult:
        compose_dir = settings.DOCKER_DIR / "grafana" / config.name
        try:
            self._generate_compose(config, compose_dir)
            success, output = compose_up(compose_dir)
            if not success:
                logger.error("Falha ao subir Grafana: %s", output)
                return DeployResult(
                    success=False,
                    url=None,
                    message=f"Erro no docker compose up:\n{output}",
                    compose_dir=compose_dir,
                )
            ip = get_machine_ip()
            url = f"http://{ip}:{config.port}"
            logger.info("Grafana '%s' implantado em %s", config.name, url)
            return DeployResult(
                success=True,
                url=url,
                message="Grafana implantado com sucesso!",
                compose_dir=compose_dir,
            )
        except Exception as exc:
            logger.error("Erro inesperado no deploy Grafana: %s", exc)
            return DeployResult(success=False, url=None, message=str(exc))

    def remove(self, compose_dir: Path, remove_volumes: bool = False) -> DeployResult:
        try:
            success, output = compose_down(compose_dir, remove_volumes)
            if not success:
                return DeployResult(success=False, url=None, message=output)
            logger.info("Grafana removido de %s (volumes=%s)", compose_dir, remove_volumes)
            return DeployResult(success=True, url=None, message="Grafana removido com sucesso.")
        except Exception as exc:
            logger.error("Erro ao remover Grafana: %s", exc)
            return DeployResult(success=False, url=None, message=str(exc))
