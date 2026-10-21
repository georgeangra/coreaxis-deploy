"""
Configurações centralizadas do CoreAxis Deploy.
Carregadas via .env com fallback para defaults seguros.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


class Settings:
    # --- Banco de dados ---
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_NAME: str = os.getenv("DB_NAME", "coreaxis_deploy")
    DB_USER: str = os.getenv("DB_USER", "coreaxis")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "SenhaForte")

    @classmethod
    def get_database_url(cls) -> str:
        return (
            f"mysql+pymysql://{cls.DB_USER}:{cls.DB_PASSWORD}"
            f"@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
        )

    # --- Diretórios ---
    LOGS_DIR: Path = BASE_DIR / "logs"
    DOCKER_DIR: Path = BASE_DIR / "docker"
    TEMPLATES_DIR: Path = BASE_DIR / "templates"

    # --- App ---
    APP_NAME: str = "CoreAxis Deploy"
    APP_VERSION: str = "1.0.0"
    LOG_FILE: Path = BASE_DIR / "logs" / "coreaxis.log"


settings = Settings()
