import argparse

import pandas as pd
from tqdm import tqdm

from src.common.config import (
    PROJECT_ROOT,
    get_active_source,
    get_db_config,
    get_mapping,
)
from src.common.db import ensure_database_exists, get_engine, truncate_table
from src.common.logging_conf import get_logger
from src.ingestion.column_transforms import apply_transform

logger = get_logger(__name__)


def _stringify_id_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if col.endswith("_id"):
            df[col] = df[col].astype(str).where(df[col].notna(), None)
    return df


def _write_dataframe(df: pd.DataFrame, table_name: str, engine, chunksize: int) -> None:
    truncate_table(table_name)
    if df.empty:
        return
    for start in tqdm(
        range(0, len(df), chunksize),
        desc=f"  -> {table_name}",
        unit="chunk",
        leave=False,
    ):
        df.iloc[start : start + chunksize].to_sql(
            table_name, engine, if_exists="append", index=False, method="multi"
        )


def ingest_entity(
    engine, mapping: dict, entity_name: str, entity_cfg: dict, db_config: dict
) -> int:
    base_path = PROJECT_ROOT / mapping["base_path"]
    source_path = base_path / entity_cfg["source_file"]

    if not source_path.exists():
        logger.warning(
            "Entité '%s': fichier source introuvable (%s) — ignorée.",
            entity_name,
            source_path,
        )
        return 0

    df = pd.read_csv(
        source_path,
        sep=mapping.get("delimiter", ";"),
        quotechar=mapping.get("quote_char", '"'),
        encoding=mapping.get("encoding", "utf-8"),
    )

    for transform_cfg in entity_cfg.get("transforms", []):
        df = apply_transform(df, transform_cfg)

    rename_map = entity_cfg.get("columns", {}) or {}
    output_columns = list(rename_map.values())
    for transform_cfg in entity_cfg.get("transforms", []):
        output_columns.extend(
            transform_cfg.get("outputs") or [transform_cfg.get("output")]
        )

    df = df.rename(columns=rename_map)

    for missing_col in entity_cfg.get("unavailable_columns", []):
        df[missing_col] = None
        output_columns.append(missing_col)

    df = df[output_columns]
    df = _stringify_id_columns(df)

    staging_table = db_config["staging_tables"][entity_name]
    _write_dataframe(df, staging_table, engine, db_config["ingestion_chunksize"])

    logger.info(
        "Entité '%s' -> table '%s' (%d lignes)", entity_name, staging_table, len(df)
    )
    return len(df)


def run_ingestion(source: str) -> None:
    logger.info("Ingestion démarrée pour la source '%s'", source)
    ensure_database_exists()

    mapping = get_mapping(source)
    db_config = get_db_config()
    engine = get_engine()

    total = 0
    entities = list(mapping["entities"].items())
    for entity_name, entity_cfg in tqdm(entities, desc="Ingestion", unit="entité"):
        total += ingest_entity(engine, mapping, entity_name, entity_cfg, db_config)
    logger.info("Ingestion terminée: %d lignes chargées au total.", total)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=None)
    args = parser.parse_args()
    run_ingestion(args.source or get_active_source())


if __name__ == "__main__":
    main()
