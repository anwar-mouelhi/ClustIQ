import os
import re
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"

_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::([^}]*))?\}")

load_dotenv(PROJECT_ROOT / ".env")


class ConfigError(Exception):
    pass


def _interpolate_env_vars(value: Any) -> Any:
    if isinstance(value, str):

        def _replace(match: re.Match) -> str:
            var_name, default = match.group(1), match.group(2)
            return os.environ.get(var_name, default if default is not None else "")

        return _ENV_VAR_PATTERN.sub(_replace, value)
    if isinstance(value, dict):
        return {k: _interpolate_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_interpolate_env_vars(v) for v in value]
    return value


def load_yaml(path: Path) -> dict:
    if not path.exists():
        raise ConfigError(f"Fichier de configuration introuvable: {path}")
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return _interpolate_env_vars(raw)


def get_schema() -> dict:
    return load_yaml(CONFIG_DIR / "schema.yaml")


def get_db_config() -> dict:
    db_config = load_yaml(CONFIG_DIR / "database.yaml")
    if not db_config.get("database"):
        raise ConfigError("MYSQL_DATABASE non défini dans .env")
    return db_config


def get_segmentation_config() -> dict:
    return load_yaml(CONFIG_DIR / "segmentation.yaml")


def get_mapping(source: str) -> dict:
    path = CONFIG_DIR / f"mapping_{source}.yaml"
    mapping = load_yaml(path)
    if not mapping.get("entities"):
        raise ConfigError(f"Le mapping '{source}' ne définit aucune entité: {path}")
    return mapping


def get_active_source() -> str:
    source = os.environ.get("DATA_SOURCE")
    if not source:
        raise ConfigError("DATA_SOURCE non défini dans .env")
    return source
