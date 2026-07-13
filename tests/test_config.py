from src.common.config import CONFIG_DIR, get_mapping, get_schema, load_yaml


def test_schema_defines_canonical_columns():
    schema = get_schema()
    column_names = {c["name"] for c in schema["columns"]}
    assert "customer_id" in column_names
    assert "transaction_id" in column_names
    assert "account_id" in column_names


def test_berka_mapping_covers_all_staging_entities():
    mapping = get_mapping("berka")
    expected_entities = {
        "customers",
        "districts",
        "dispositions",
        "accounts",
        "transactions",
        "loans",
        "cards",
        "products",
    }
    assert expected_entities.issubset(mapping["entities"].keys())


def test_berka_mapping_transforms_reference_known_columns():
    mapping = get_mapping("berka")
    for entity_name, entity_cfg in mapping["entities"].items():
        for transform in entity_cfg.get("transforms", []):
            assert "function" in transform
            assert "input" in transform
            assert "output" in transform or "outputs" in transform


def test_stb_mapping_template_has_same_entities_as_berka():
    berka = load_yaml(CONFIG_DIR / "mapping_berka.yaml")
    stb = load_yaml(CONFIG_DIR / "mapping_stb.yaml")
    assert set(stb["entities"].keys()) == set(berka["entities"].keys())
