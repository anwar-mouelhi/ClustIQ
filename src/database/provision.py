from pathlib import Path

from src.common.db import run_sql_file
from src.common.logging_conf import get_logger

logger = get_logger(__name__)

DATABASE_DIR = Path(__file__).resolve().parent


def main() -> None:
    sql_files = sorted(DATABASE_DIR.glob("*.sql"))
    if not sql_files:
        logger.warning("Aucun script .sql trouvé dans %s", DATABASE_DIR)
        return
    for sql_file in sql_files:
        run_sql_file(sql_file)
    logger.info("Schéma MySQL appliqué (%d scripts).", len(sql_files))


if __name__ == "__main__":
    main()
