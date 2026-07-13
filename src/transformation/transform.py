import pandas as pd
from tqdm import tqdm

from src.common.config import get_db_config
from src.common.db import get_engine, truncate_table
from src.common.logging_conf import get_logger

logger = get_logger(__name__)


def _read_table(
    engine, table_name: str, decimal_cols: list[str] | None = None
) -> pd.DataFrame:
    df = pd.read_sql(f"SELECT * FROM {table_name}", engine)
    for col in decimal_cols or []:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _write_table(engine, df: pd.DataFrame, table_name: str, chunksize: int) -> None:
    truncate_table(table_name)
    df.to_sql(
        table_name,
        engine,
        if_exists="append",
        index=False,
        chunksize=chunksize,
        method="multi",
    )
    logger.info("Table '%s' rechargée (%d lignes).", table_name, len(df))


def _age_range(birth_dates: pd.Series, reference_date) -> pd.Series:
    age_days = (pd.Timestamp(reference_date) - pd.to_datetime(birth_dates)).dt.days
    age_years = age_days / 365.25

    def bucket(age: float) -> str | None:
        if pd.isna(age):
            return None
        if age < 25:
            return "<25"
        if age < 35:
            return "25-34"
        if age < 45:
            return "35-44"
        if age < 55:
            return "45-54"
        if age < 65:
            return "55-64"
        return "65+"

    return age_years.apply(bucket)


def build_agg_loans(loans: pd.DataFrame) -> pd.DataFrame:
    if loans.empty:
        return pd.DataFrame(columns=["account_id", "loan_amount", "loan_status"])
    latest_status = loans.sort_values(
        "loan_date", ascending=False, na_position="last"
    ).drop_duplicates("account_id", keep="first")[["account_id", "loan_status"]]
    totals = loans.groupby("account_id", as_index=False)["loan_amount"].sum()
    return totals.merge(latest_status, on="account_id", how="left")


def build_agg_cards(cards: pd.DataFrame, dispositions: pd.DataFrame) -> pd.DataFrame:
    merged = cards.merge(
        dispositions[["disposition_id", "account_id"]], on="disposition_id", how="inner"
    )
    if merged.empty:
        return pd.DataFrame(columns=["account_id", "card_type"])
    return merged.sort_values(
        "card_issue_date", ascending=False, na_position="last"
    ).drop_duplicates("account_id", keep="first")[["account_id", "card_type"]]


def build_agg_products(products: pd.DataFrame) -> pd.DataFrame:
    if products.empty:
        return pd.DataFrame(
            columns=["account_id", "product_type", "product_subscription_date"]
        )
    return products.sort_values(
        ["product_subscription_date", "product_id"],
        ascending=[False, False],
        na_position="last",
    ).drop_duplicates("account_id", keep="first")[
        ["account_id", "product_type", "product_subscription_date"]
    ]


def build_customer_attributes(
    customers: pd.DataFrame,
    districts: pd.DataFrame,
    dispositions: pd.DataFrame,
    transactions: pd.DataFrame,
    agg_loans: pd.DataFrame,
    agg_cards: pd.DataFrame,
    agg_products: pd.DataFrame,
    reference_date,
) -> pd.DataFrame:
    owners = dispositions.loc[
        dispositions["disposition_type"] == "OWNER", ["customer_id", "account_id"]
    ]

    base = customers.merge(districts, on="district_id", how="left")
    base["age_range"] = _age_range(base["birth_date"], reference_date)
    base = base[["customer_id", "age_range", "gender", "region"]]

    tx_frequency = (
        transactions.merge(owners, on="account_id", how="inner")
        .groupby("customer_id", as_index=False)
        .agg(transaction_frequency=("transaction_id", "count"))
    )

    loan_customer_ids = set(
        owners.merge(agg_loans[["account_id"]], on="account_id", how="inner")[
            "customer_id"
        ]
    )
    card_customer_ids = set(
        owners.merge(agg_cards[["account_id"]], on="account_id", how="inner")[
            "customer_id"
        ]
    )

    nb_products = (
        owners.merge(agg_products, on="account_id", how="inner")
        .groupby("customer_id", as_index=False)
        .agg(nb_products=("product_type", "nunique"))
    )

    result = base.merge(tx_frequency, on="customer_id", how="left").merge(
        nb_products, on="customer_id", how="left"
    )

    result["transaction_frequency"] = (
        result["transaction_frequency"].fillna(0).astype(int)
    )
    result["has_loan"] = result["customer_id"].isin(loan_customer_ids)
    result["has_card"] = result["customer_id"].isin(card_customer_ids)
    result["nb_products"] = result["nb_products"].fillna(0).astype(int)

    result["customer_category"] = "Basic"
    has_any_product = (
        result["has_loan"] | result["has_card"] | (result["nb_products"] > 0)
    )
    result.loc[has_any_product, "customer_category"] = "Standard"
    result.loc[result["has_loan"] & result["has_card"], "customer_category"] = "Premium"

    return result[
        [
            "customer_id",
            "age_range",
            "gender",
            "region",
            "customer_category",
            "transaction_frequency",
        ]
    ]


def run_transformation() -> None:
    logger.info("Transformation démarrée.")
    db_config = get_db_config()
    engine = get_engine()
    staging = db_config["staging_tables"]

    read_plan = [
        ("customers", staging["customers"], None),
        ("districts", staging["districts"], None),
        ("dispositions", staging["dispositions"], None),
        (
            "transactions",
            staging["transactions"],
            ["transaction_amount", "account_balance"],
        ),
        ("loans", staging["loans"], ["loan_amount"]),
        ("cards", staging["cards"], None),
        ("products", staging["products"], ["product_amount"]),
    ]
    tables = {}
    for key, table_name, decimal_cols in tqdm(
        read_plan, desc="Lecture staging", unit="table"
    ):
        tables[key] = _read_table(engine, table_name, decimal_cols)

    if tables["transactions"].empty:
        raise RuntimeError(
            "Aucune transaction en staging: lancez 'make ingestion' avant 'make transformation'."
        )
    reference_date = (
        pd.to_datetime(tables["transactions"]["transaction_date"]).max().date()
    )
    logger.info("Date de référence: %s", reference_date)

    agg_loans = build_agg_loans(tables["loans"])
    agg_cards = build_agg_cards(tables["cards"], tables["dispositions"])
    agg_products = build_agg_products(tables["products"])
    customer_attributes = build_customer_attributes(
        tables["customers"],
        tables["districts"],
        tables["dispositions"],
        tables["transactions"],
        agg_loans,
        agg_cards,
        agg_products,
        reference_date,
    )

    write_plan = [
        (agg_loans, db_config["transformation_tables"]["agg_loans"]),
        (agg_cards, db_config["transformation_tables"]["agg_cards"]),
        (agg_products, db_config["transformation_tables"]["agg_products"]),
        (
            customer_attributes,
            db_config["transformation_tables"]["customer_attributes"],
        ),
    ]
    for df, table_name in tqdm(write_plan, desc="Écriture", unit="table"):
        _write_table(engine, df, table_name, db_config["transformation_chunksize"])

    logger.info("Transformation terminée.")


def main() -> None:
    run_transformation()


if __name__ == "__main__":
    main()
