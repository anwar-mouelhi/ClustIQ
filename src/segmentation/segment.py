from src.common.config import get_db_config, get_segmentation_config
from src.common.db import get_engine, truncate_table
from src.common.logging_conf import get_logger
from src.segmentation.clustering import run_kmeans
from src.segmentation.feature_engineering import (
    build_customer_features,
    read_customer_360,
)

logger = get_logger(__name__)


def run_segmentation() -> None:
    logger.info("Segmentation démarrée.")
    db_config = get_db_config()
    segmentation_config = get_segmentation_config()
    engine = get_engine()

    customer_360 = read_customer_360(engine, db_config)
    features = build_customer_features(customer_360)
    feature_cols = segmentation_config["features"]["numeric"]

    result = run_kmeans(
        features,
        feature_cols=feature_cols,
        k_min=segmentation_config["kmeans"]["k_min"],
        k_max=segmentation_config["kmeans"]["k_max"],
        seed=segmentation_config["kmeans"]["seed"],
        max_iter=segmentation_config["kmeans"]["max_iter"],
        tol=segmentation_config["kmeans"]["tol"],
        fixed_k=segmentation_config["kmeans"].get("fixed_k"),
    )

    output_columns = ["customer_id", "segment"] + feature_cols
    output_df = result.predictions[output_columns]

    output_table = db_config["segmentation_table"]
    truncate_table(output_table)
    output_df.to_sql(
        output_table,
        engine,
        if_exists="append",
        index=False,
        chunksize=db_config["segmentation_chunksize"],
        method="multi",
    )
    logger.info(
        "Segmentation écrite dans '%s' (k=%d, %d clients).",
        output_table,
        result.k,
        len(output_df),
    )


def main() -> None:
    run_segmentation()


if __name__ == "__main__":
    main()
