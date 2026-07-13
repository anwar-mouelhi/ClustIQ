import datetime

import pandas as pd

from src.ingestion.column_transforms import berka_split_birth_number, yymmdd_to_date


def test_yymmdd_to_date_parses_plain_date():
    df = pd.DataFrame({"date": ["930101"]})
    result = yymmdd_to_date(df, "date", ["parsed_date"])
    assert result.loc[0, "parsed_date"] == datetime.date(1993, 1, 1)


def test_yymmdd_to_date_parses_datetime_string():
    df = pd.DataFrame({"issued": ["940119 00:00:00"]})
    result = yymmdd_to_date(df, "issued", ["card_issue_date"])
    assert result.loc[0, "card_issue_date"] == datetime.date(1994, 1, 19)


def test_berka_split_birth_number_male():
    df = pd.DataFrame({"birth_number": ["450204"]})
    result = berka_split_birth_number(df, "birth_number", ["birth_date", "gender"])
    assert result.loc[0, "gender"] == "M"
    assert result.loc[0, "birth_date"] == datetime.date(1945, 2, 4)


def test_berka_split_birth_number_female():
    df = pd.DataFrame({"birth_number": ["706213"]})
    result = berka_split_birth_number(df, "birth_number", ["birth_date", "gender"])
    assert result.loc[0, "gender"] == "F"
    assert result.loc[0, "birth_date"] == datetime.date(1970, 12, 13)
