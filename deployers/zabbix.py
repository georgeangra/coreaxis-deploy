"""
Deployer do Zabbix (Server + Web + Agent + MariaDB) via Docker Compose.
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


class ZabbixDeployer(BaseDeployer):
    @property
    def service_name(self) -> str:
        return "zabbix"

    @property
    def display_name(self) -> str:
        return "Zabbix"

    def collect_config(self) -> DeployConfig:
        console.print("\n[bold cyan]══ Configuração do Zabbix ══[/bold cyan]\n")

        machine_ip = get_machine_ip()
        console.print(
            f"[bold yellow]⚠  IP detectado:[/bold yellow] [white]{machine_ip}[/white]\n"
            "[dim]Se estiver em VirtualBox e o IP aparecer como 10.0.2.x ou 127.x,\n"
            "configure a VM em modo Bridge: Configurações → Rede → Placa em modo Bridge.\n"
            "Assim a VM recebe um IP real da sua rede e fica acessível de outros dispositivos.[/dim]\n"
        )

        name = validate_non_empty(
            Prompt.ask("[green]Nome da Instância[/green]", default="Zabbix-Lab"), "Nome"
        )
        port_web_str = Prompt.ask("[green]Porta Frontend[/green]", default="8080")
        port_web = validate_port(port_web_str)
        check_port_available(port_web)

        port_db_str = Prompt.ask("[green]Porta MariaDB[/green]", default="3307")
        port_db = validate_port(port_db_str)
        check_port_available(port_db)

        db_pass = Prompt.ask("[green]Senha do Banco[/green]", default="zabbix123", password=True)
        validate_non_empty(db_pass, "Senha do Banco")

        console.print(
            "\n[bold yellow]ℹ  Credenciais padrão do Zabbix:[/bold yellow]\n"
            "   Usuário: [bold white]Admin[/bold white]\n"
            "   Senha:   [bold white]zabbix[/bold white]\n"
            "[dim]Por segurança, altere a senha no primeiro acesso em:\n"
            "User Settings → Change password[/dim]\n"
        )

        return DeployConfig(
            name=name,
            service=self.service_name,
            port=port_web,
            extra={
                "port_db": port_db,
                "db_pass": db_pass,
                "admin_user": "Admin",
            },
        )

    def _generate_compose(self, config: DeployConfig, compose_dir: Path) -> None:
        slug = config.name.lower().replace(" ", "_")
        network_name = f"zabbix_net_{slug}"

        compose_data = {
            "version": "3.8",
            "networks": {
                network_name: {"driver": "bridge"},
            },
            "volumes": {
                f"zabbix_db_{slug}": None,
                f"zabbix_data_{slug}": None,
            },
            "services": {
                f"zabbix-db-{slug}": {
                    "image": "mariadb:10.11",
                    "container_name": f"zabbix_db_{slug}",
                    "restart": "unless-stopped",
                    "environment": {
                        "MYSQL_ROOT_PASSWORD": config.extra["db_pass"],
                        "MYSQL_DATABASE": "zabbix",
                        "MYSQL_USER": "zabbix",
                        "MYSQL_PASSWORD": config.extra["db_pass"],
                    },
                    "ports": [f"{config.extra['port_db']}:3306"],
                    "volumes": [f"zabbix_db_{slug}:/var/lib/mysql"],
                    "networks": [network_name],
                    "command": [
                        "--character-set-server=utf8",
                        "--collation-server=utf8_bin",
                        "--default-authentication-plugin=mysql_native_password",
                    ],
                },
                f"zabbix-server-{slug}": {
                    "image": "zabbix/zabbix-server-mysql:ubuntu-7.0-latest",
                    "container_name": f"zabbix_server_{slug}",
                    "restart": "unless-stopped",
                    "environment": {
                        "DB_SERVER_HOST": f"zabbix_db_{slug}",
                        "MYSQL_DATABASE": "zabbix",
                        "MYSQL_USER": "zabbix",
                        "MYSQL_PASSWORD": config.extra["db_pass"],
                    },
                    "volumes": [f"zabbix_data_{slug}:/var/lib/zabbix"],
                    "ports": ["10051:10051"],
                    "networks": [network_name],
                    "depends_on": [f"zabbix-db-{slug}"],
                },
                f"zabbix-web-{slug}": {
                    "image": "zabbix/zabbix-web-nginx-mysql:ubuntu-7.0-latest",
                    "container_name": f"zabbix_web_{slug}",
                    "restart": "unless-stopped",
                    "environment": {
                        "ZBX_SERVER_HOST": f"zabbix_server_{slug}",
                        "DB_SERVER_HOST": f"zabbix_db_{slug}",
                        "MYSQL_DATABASE": "zabbix",
                        "MYSQL_USER": "zabbix",
                        "MYSQL_PASSWORD": config.extra["db_pass"],
                        "PHP_TZ": "America/Sao_Paulo",
                    },
                    "ports": [f"{config.port}:8080"],
                    "networks": [network_name],
                    "depends_on": [f"zabbix-server-{slug}"],
                },
                f"zabbix-agent-{slug}": {
                    "image": "zabbix/zabbix-agent:ubuntu-6.4-latest",
                    "container_name": f"zabbix_agent_{slug}",
                    "restart": "unless-stopped",
                    "environment": {
                        "ZBX_SERVER_HOST": f"zabbix_server_{slug}",
                    },
                    "networks": [network_name],
                    "depends_on": [f"zabbix-server-{slug}"],
                },
            },
        }

        compose_dir.mkdir(parents=True, exist_ok=True)
        with open(compose_dir / "docker-compose.yml", "w") as f:
            yaml.dump(compose_data, f, default_flow_style=False, allow_unicode=True)

        logger.info("docker-compose.yml Zabbix gerado em %s", compose_dir)

    def deploy(self, config: DeployConfig) -> DeployResult:
        compose_dir = settings.DOCKER_DIR / "zabbix" / config.name
        try:
            self._generate_compose(config, compose_dir)
            success, output = compose_up(compose_dir)
            if not success:
                logger.error("Falha ao subir Zabbix: %s", output)
                return DeployResult(
                    success=False,
                    url=None,
                    message=f"Erro no docker compose up:\n{output}",
                    compose_dir=compose_dir,
                )
            ip = get_machine_ip()
            url = f"http://{ip}:{config.port}"
            logger.info("Zabbix '%s' implantado em %s", config.name, url)
            console.print(
                "\n[bold yellow]⏳ Aguarde 3 a 5 minutos[/bold yellow] para o Zabbix inicializar o banco de dados.\n"
                "[dim]Se aparecer erro de banco ao abrir a URL, aguarde e recarregue a página.[/dim]\n"
            )
            return DeployResult(
                success=True,
                url=url,
                message="Zabbix implantado com sucesso!",
                compose_dir=compose_dir,
            )
        except Exception as exc:
            logger.error("Erro inesperado no deploy Zabbix: %s", exc)
            return DeployResult(success=False, url=None, message=str(exc))

    def remove(self, compose_dir: Path, remove_volumes: bool = False) -> DeployResult:
        try:
            success, output = compose_down(compose_dir, remove_volumes)
            if not success:
                return DeployResult(success=False, url=None, message=output)
            logger.info("Zabbix removido de %s", compose_dir)
            return DeployResult(success=True, url=None, message="Zabbix removido com sucesso.")
        except Exception as exc:
            logger.error("Erro ao remover Zabbix: %s", exc)
            return DeployResult(success=False, url=None, message=str(exc))
