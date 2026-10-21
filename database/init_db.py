"""
Inicialização do banco de dados.
Cria schema e tabelas se não existirem.
"""
import pymysql
from sqlalchemy import text
from database.db import engine
from database.models import Base
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


def create_database_if_not_exists() -> None:
    """Cria o banco coreaxis_deploy caso não exista."""
    try:
        conn = pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
        )
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{settings.DB_NAME}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Banco '%s' verificado/criado.", settings.DB_NAME)
    except Exception as exc:
        logger.error("Erro ao criar banco de dados: %s", exc)
        raise


def init_db() -> None:
    """Cria todas as tabelas definidas nos modelos."""
    try:
        create_database_if_not_exists()
        Base.metadata.create_all(bind=engine)
        logger.info("Tabelas inicializadas com sucesso.")
    except Exception as exc:
        logger.error("Erro ao inicializar banco: %s", exc)
        raise
