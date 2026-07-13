from pathlib import Path

import mysql.connector
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.common.config import get_db_config
from src.common.logging_conf import get_logger

logger = get_logger(__name__)


def get_connection(with_database: bool = True):
    db_config = get_db_config()
    kwargs = dict(
        host=db_config["host"],
        port=int(db_config["port"]),
        user=db_config["user"],
        password=db_config["password"],
    )
    if with_database:
        kwargs["database"] = db_config["database"]
    return mysql.connector.connect(**kwargs)


def get_engine() -> Engine:
    db_config = get_db_config()
    url = (
        f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}"
        f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    )
    return create_engine(url, pool_pre_ping=True)


def ensure_database_exists() -> None:
    db_config = get_db_config()
    conn = get_connection(with_database=False)
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db_config['database']}` "
            "DEFAULT CHARACTER SET utf8mb4"
        )
        conn.commit()
        cursor.close()
        logger.info("Base '%s' prête.", db_config["database"])
    finally:
        conn.close()


def table_exists(table_name: str) -> bool:
    db_config = get_db_config()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = %s AND table_name = %s",
            (db_config["database"], table_name),
        )
        (count,) = cursor.fetchone()
        cursor.close()
        return count > 0
    finally:
        conn.close()


def truncate_table(table_name: str) -> None:
    if not table_exists(table_name):
        raise RuntimeError(f"Table '{table_name}' introuvable. Lancez 'make database'.")
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"TRUNCATE TABLE `{table_name}`")
        conn.commit()
        cursor.close()
        logger.debug("Table '%s' vidée avant rechargement.", table_name)
    finally:
        conn.close()


def run_sql_file(path: Path) -> None:
    ensure_database_exists()
    sql_text = path.read_text(encoding="utf-8")
    statements = [s.strip() for s in sql_text.split(";") if s.strip()]

    conn = get_connection()
    try:
        cursor = conn.cursor()
        for statement in statements:
            cursor.execute(statement)
        conn.commit()
        cursor.close()
        logger.info(
            "Script SQL exécuté: %s (%d instructions)", path.name, len(statements)
        )
    finally:
        conn.close()
