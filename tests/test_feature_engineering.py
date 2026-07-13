import datetime

import pandas as pd

from src.segmentation.feature_engineering import build_customer_features

ROWS = [
    {
        "customer_id": "C1",
        "account_id": "A1",
        "account_open_date": datetime.date(2020, 1, 1),
        "loan_amount": 1000.0,
        "product_type": "P1",
        "account_balance": 100.0,
        "transaction_date": datetime.date(2021, 1, 1),
        "transaction_amount": 50.0,
        "transaction_frequency": 2,
    },
    {
        "customer_id": "C1",
        "account_id": "A1",
        "account_open_date": datetime.date(2020, 1, 1),
        "loan_amount": 1000.0,
        "product_type": "P1",
        "account_balance": 150.0,
        "transaction_date": datetime.date(2021, 6, 1),
        "transaction_amount": 100.0,
        "transaction_frequency": 2,
    },
    {
        "customer_id": "C2",
        "account_id": "A2",
        "account_open_date": datetime.date(2019, 1, 1),
        "loan_amount": None,
        "product_type": "P2",
        "account_balance": 500.0,
        "transaction_date": datetime.date(2021, 3, 1),
        "transaction_amount": 20.0,
        "transaction_frequency": 1,
    },
]

REFERENCE_DATE = pd.Timestamp(2021, 6, 1)


def test_build_customer_features_respects_grain():
    df = pd.DataFrame(ROWS)
    features = build_customer_features(df).set_index("customer_id")

    c1 = features.loc["C1"]
    assert c1["avg_account_balance"] == 150.0
    assert c1["nb_products"] == 1
    assert c1["account_age_days"] == (REFERENCE_DATE - pd.Timestamp(2020, 1, 1)).days
    assert c1["total_loan_amount"] == 1000.0
    assert c1["avg_transaction_amount"] == 75.0
    assert c1["transaction_frequency"] == 2

    c2 = features.loc["C2"]
    assert c2["avg_account_balance"] == 500.0
    assert c2["total_loan_amount"] == 0.0
    assert c2["account_age_days"] == (REFERENCE_DATE - pd.Timestamp(2019, 1, 1)).days
