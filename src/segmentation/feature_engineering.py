import pandas as pd

from src.common.config import get_db_config
from src.common.db import get_engine
from src.common.logging_conf import get_logger

logger = get_logger(__name__)


def read_customer_360(engine=None, db_config: dict | None = None) -> pd.DataFrame:
    db_config = db_config or get_db_config()
    engine = engine or get_engine()
    df = pd.read_sql(f"SELECT * FROM {db_config['customer_360_view']}", engine)
    for col in ("account_balance", "transaction_amount", "loan_amount"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def build_customer_features(customer_360: pd.DataFrame) -> pd.DataFrame:
    if customer_360.empty:
        raise RuntimeError(
            "La vue customer_360 est vide: lancez 'make database', 'make ingestion' puis 'make transformation'."
        )
    reference_date = pd.to_datetime(customer_360["transaction_date"]).max()
    logger.info("Date de référence: %s", reference_date.date())

    account_level = customer_360[
        [
            "customer_id",
            "account_id",
            "account_open_date",
            "loan_amount",
            "product_type",
        ]
    ].drop_duplicates("account_id")
    account_level["account_open_date"] = pd.to_datetime(
        account_level["account_open_date"]
    )

    latest_balance = (
        customer_360.sort_values(
            "transaction_date", ascending=False, na_position="last"
        )
        .drop_duplicates("account_id", keep="first")[["account_id", "account_balance"]]
        .rename(columns={"account_balance": "latest_account_balance"})
    )
    account_level = account_level.merge(latest_balance, on="account_id", how="left")

    account_features = account_level.groupby("customer_id", as_index=False).agg(
        avg_account_balance=("latest_account_balance", "mean"),
        nb_products=("product_type", "nunique"),
        account_age_days=(
            "account_open_date",
            lambda s: (reference_date - s.min()).days,
        ),
        total_loan_amount=("loan_amount", "sum"),
    )

    transaction_features = customer_360.groupby("customer_id", as_index=False).agg(
        avg_transaction_amount=("transaction_amount", "mean"),
        transaction_frequency=("transaction_frequency", "max"),
    )

    features = account_features.merge(
        transaction_features, on="customer_id", how="inner"
    )
    features = features.fillna(
        {
            "avg_account_balance": 0.0,
            "nb_products": 0,
            "account_age_days": 0,
            "total_loan_amount": 0.0,
            "avg_transaction_amount": 0.0,
            "transaction_frequency": 0,
        }
    )
    return features
