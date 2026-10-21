"""
CoreAxis Deploy — ponto de entrada principal.
Exibe o menu Rich e orquestra os módulos de deployment.
"""
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
from rich import box

# Garante que imports relativos funcionam ao rodar python3 main.py
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from database.init_db import init_db
from database.db import get_session
from database.models import Deployment, DeploymentStatus
from deployers.grafana import GrafanaDeployer
from deployers.zabbix import ZabbixDeployer
from utils.docker_utils import docker_ps, docker_logs
from utils.validators import (
    check_docker,
    check_docker_compose,
    check_python_version,
    check_db_connection,
    PrerequisiteError,
)
from utils.logger import get_logger

console = Console()
logger = get_logger(__name__)

DEPLOYERS = {
    "grafana": GrafanaDeployer(),
    "zabbix": ZabbixDeployer(),
}


# ─── Helpers de UI ────────────────────────────────────────────────────────────

def print_header() -> None:
    title = Text(settings.APP_NAME, style="bold white")
    subtitle = Text(f"v{settings.APP_VERSION}  ·  Plataforma de Provisionamento de Infraestrutura", style="dim")
    console.print(
        Panel(
            f"[bold white]{settings.APP_NAME}[/bold white]\n[dim]v{settings.APP_VERSION}  ·  Plataforma de Provisionamento de Infraestrutura[/dim]",
            style="bold blue",
            padding=(1, 4),
        )
    )


def print_menu() -> None:
    table = Table(box=box.ROUNDED, show_header=False, padding=(0, 2), style="cyan")
    table.add_column("Opção", style="bold yellow", width=6)
    table.add_column("Ação", style="white")

    menu_items = [
        ("1", "Implantar Grafana"),
        ("2", "Implantar Zabbix"),
        ("3", "Listar Serviços"),
        ("4", "Ver Status dos Containers"),
        ("5", "Ver Logs"),
        ("6", "Remover Serviço"),
        ("7", "Sair"),
    ]
    for opt, label in menu_items:
        table.add_row(f"[{opt}]", label)

    console.print(table)
    console.print(
        "[dim]─────────────────────────────────────────────────\n"
        " Gostou do CoreAxis Deploy? Nos siga no Instagram!\n"
        " [bold cyan]@coreaxis.tech[/bold cyan]  →  [link=https://instagram.com/coreaxis.tech]instagram.com/coreaxis.tech[/link]\n"
        "─────────────────────────────────────────────────[/dim]"
    )


def success_panel(title: str, body: str) -> None:
    console.print(Panel(body, title=f"[bold green]{title}[/bold green]", border_style="green"))


def error_panel(title: str, body: str) -> None:
    console.print(Panel(body, title=f"[bold red]{title}[/bold red]", border_style="red"))


# ─── Verificação de Pré-requisitos ────────────────────────────────────────────

def run_checks() -> bool:
    checks = [
        ("Python 3.12+", check_python_version),
        ("Docker Engine", check_docker),
        ("Docker Compose", check_docker_compose),
        ("MariaDB", check_db_connection),
    ]

    table = Table(title="Verificação de Pré-requisitos", box=box.SIMPLE_HEAVY)
    table.add_column("Componente", style="cyan")
    table.add_column("Status", justify="center")

    all_ok = True
    for label, fn in checks:
        try:
            fn()
            table.add_row(label, "[bold green]✓ OK[/bold green]")
        except PrerequisiteError as exc:
            table.add_row(label, "[bold red]✗ FALHA[/bold red]")
            console.print(f"  [red]→ {exc}[/red]")
            all_ok = False
        except Exception as exc:
            table.add_row(label, "[bold red]✗ ERRO[/bold red]")
            console.print(f"  [red]→ {exc}[/red]")
            all_ok = False

    console.print(table)
    return all_ok


# ─── Handlers do Menu ─────────────────────────────────────────────────────────

def handle_deploy(service_key: str) -> None:
    deployer = DEPLOYERS[service_key]
    logger.info("Iniciando deploy de %s", service_key)

    try:
        config = deployer.collect_config()
    except (ValueError, KeyboardInterrupt) as exc:
        error_panel("Entrada inválida", str(exc))
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(f"Implantando {deployer.display_name}...", total=None)
        result = deployer.deploy(config)

    if result.success:
        body = (
            f"[bold]{deployer.display_name}[/bold] implantado com sucesso!\n\n"
            f"[cyan]URL:[/cyan]     {result.url}\n"
            f"[cyan]Usuário:[/cyan] {config.extra.get('admin_user', 'admin')}"
        )
        success_panel(f"{deployer.display_name} Instalado", body)

        # Persiste no banco
        for session in get_session():
            dep = Deployment(
                service=config.service,
                name=config.name,
                url=result.url,
                status=DeploymentStatus.RUNNING,
            )
            session.add(dep)
        logger.info("Deployment '%s' salvo no banco.", config.name)
    else:
        error_panel("Falha no Deploy", result.message)


def handle_list_services() -> None:
    table = Table(
        title="Serviços Implantados",
        box=box.ROUNDED,
        show_lines=True,
        style="cyan",
    )
    table.add_column("ID", style="bold yellow", justify="right")
    table.add_column("Serviço", style="bold magenta")
    table.add_column("Nome", style="white")
    table.add_column("URL", style="blue")
    table.add_column("Status", justify="center")
    table.add_column("Criado em")

    for session in get_session():
        deployments = session.query(Deployment).filter(
            Deployment.status != DeploymentStatus.REMOVED
        ).all()

        if not deployments:
            console.print("[yellow]Nenhum serviço implantado ainda.[/yellow]")
            return

        status_colors = {
            DeploymentStatus.RUNNING: "[bold green]● RUNNING[/bold green]",
            DeploymentStatus.STOPPED: "[bold yellow]● STOPPED[/bold yellow]",
            DeploymentStatus.ERROR:   "[bold red]● ERROR[/bold red]",
            DeploymentStatus.REMOVED: "[dim]● REMOVED[/dim]",
        }

        for dep in deployments:
            table.add_row(
                str(dep.id),
                dep.service.upper(),
                dep.name,
                dep.url or "-",
                status_colors.get(dep.status, dep.status.value),
                dep.created_at.strftime("%d/%m/%Y %H:%M"),
            )

    console.print(table)


def handle_container_status() -> None:
    containers = docker_ps()
    if not containers:
        console.print("[yellow]Nenhum container em execução.[/yellow]")
        return

    table = Table(title="Containers em Execução", box=box.ROUNDED, style="cyan")
    table.add_column("Nome", style="bold white")
    table.add_column("Imagem", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Portas", style="blue")
    table.add_column("Uptime", style="dim")

    for c in containers:
        table.add_row(c["name"], c["image"], c["status"], c["ports"], c["uptime"])

    console.print(table)


def handle_logs() -> None:
    handle_list_services()

    for session in get_session():
        deployments = session.query(Deployment).filter(
            Deployment.status != DeploymentStatus.REMOVED
        ).all()
        if not deployments:
            return

        dep_id_str = Prompt.ask("\n[green]ID do deployment[/green]")
        try:
            dep_id = int(dep_id_str)
        except ValueError:
            error_panel("Entrada inválida", "ID deve ser um número inteiro.")
            return

        dep = session.query(Deployment).get(dep_id)
        if not dep:
            error_panel("Não encontrado", f"Deployment ID {dep_id} não existe.")
            return

        container_name = dep.name.lower().replace(" ", "_")
        logs = docker_logs(container_name)
        console.print(Panel(logs or "(sem logs)", title=f"Logs — {dep.name}", border_style="blue"))


def handle_remove() -> None:
    handle_list_services()

    for session in get_session():
        dep_id_str = Prompt.ask("\n[green]Digite o ID do serviço a remover[/green]")
        try:
            dep_id = int(dep_id_str)
        except ValueError:
            error_panel("Entrada inválida", "ID deve ser um número inteiro.")
            return

        dep = session.query(Deployment).get(dep_id)
        if not dep or dep.status == DeploymentStatus.REMOVED:
            error_panel("Não encontrado", f"Deployment ID {dep_id} não encontrado ou já removido.")
            return

        rm_vols = Confirm.ask("[yellow]Remover volumes persistentes?[/yellow]", default=False)

        deployer = DEPLOYERS.get(dep.service)
        if not deployer:
            error_panel("Serviço desconhecido", f"Deployer para '{dep.service}' não registrado.")
            return

        compose_dir = settings.DOCKER_DIR / dep.service / dep.name
        result = deployer.remove(compose_dir, remove_volumes=rm_vols)

        if result.success:
            dep.status = DeploymentStatus.REMOVED
            session.add(dep)
            success_panel("Removido", result.message)
            logger.info("Serviço '%s' (ID=%d) removido.", dep.name, dep.id)
        else:
            error_panel("Falha ao Remover", result.message)


# ─── Loop Principal ───────────────────────────────────────────────────────────

def main() -> None:
    print_header()

    console.print("\n[bold]Verificando pré-requisitos...[/bold]")
    all_ok = run_checks()

    if not all_ok:
        error_panel(
            "Pré-requisitos não atendidos",
            "Corrija os problemas acima antes de prosseguir.",
        )
        sys.exit(1)

    # Inicializa banco
    try:
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), transient=True) as p:
            p.add_task("Inicializando banco de dados...", total=None)
            init_db()
    except Exception as exc:
        error_panel("Erro de Banco", str(exc))
        sys.exit(1)

    console.print("[bold green]Sistema pronto.[/bold green]\n")
    logger.info("CoreAxis Deploy iniciado.")

    handlers = {
        "1": lambda: handle_deploy("grafana"),
        "2": lambda: handle_deploy("zabbix"),
        "3": handle_list_services,
        "4": handle_container_status,
        "5": handle_logs,
        "6": handle_remove,
        "7": None,
    }

    while True:
        console.rule()
        print_menu()
        choice = Prompt.ask("\n[bold yellow]Escolha uma opção[/bold yellow]")

        if choice == "7":
            console.print("[bold cyan]Até logo![/bold cyan]")
            logger.info("CoreAxis Deploy encerrado pelo usuário.")
            break

        handler = handlers.get(choice)
        if handler is None:
            console.print("[red]Opção inválida. Tente novamente.[/red]")
            continue

        try:
            handler()
        except KeyboardInterrupt:
            console.print("\n[yellow]Operação cancelada.[/yellow]")
        except Exception as exc:
            error_panel("Erro inesperado", str(exc))
            logger.exception("Erro inesperado na opção %s", choice)

        console.print()


if __name__ == "__main__":
    main()
