import pandas as pd


def yymmdd_to_date(
    df: pd.DataFrame, input_col: str, output_cols: list[str]
) -> pd.DataFrame:
    output_col = output_cols[0]
    digits = df[input_col].astype(str).str.slice(0, 6)
    df[output_col] = pd.to_datetime(
        "19" + digits, format="%Y%m%d", errors="coerce"
    ).dt.date
    return df


def berka_split_birth_number(
    df: pd.DataFrame, input_col: str, output_cols: list[str]
) -> pd.DataFrame:
    birth_date_col, gender_col = output_cols
    raw = df[input_col].astype(str).str.zfill(6)
    year = raw.str.slice(0, 2)
    month_raw = raw.str.slice(2, 4).astype(int)
    day = raw.str.slice(4, 6)

    is_female = month_raw > 50
    month_real = month_raw.where(~is_female, month_raw - 50)
    month_str = month_real.astype(str).str.zfill(2)
    date_str = "19" + year + month_str + day

    df[birth_date_col] = pd.to_datetime(
        date_str, format="%Y%m%d", errors="coerce"
    ).dt.date
    df[gender_col] = is_female.map({True: "F", False: "M"})
    return df


TRANSFORMS = {
    "yymmdd_to_date": yymmdd_to_date,
    "berka_split_birth_number": berka_split_birth_number,
}


def apply_transform(df: pd.DataFrame, transform_cfg: dict) -> pd.DataFrame:
    function_name = transform_cfg["function"]
    if function_name not in TRANSFORMS:
        raise KeyError(f"Transform '{function_name}' inconnue: {sorted(TRANSFORMS)}")
    input_col = transform_cfg["input"]
    output_cols = transform_cfg.get("outputs") or [transform_cfg["output"]]
    return TRANSFORMS[function_name](df, input_col, output_cols)
