"""
Tests for dataset generation and validation.
"""

from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.seed_data import generate_dataset, RAW_DIR
from app.services.validator import (
    DataValidationError,
    validate_all,
    validate_customers,
    validate_foreign_keys,
    validate_products,
    validate_purchases,
    validate_aggregated_totals,
)


@pytest.fixture(scope="module")
def sample_data():
    """Generate datasets once for testing."""
    products_df, customers_df, purchases_df = generate_dataset(
        num_products=100,
        num_customers=1000,
        min_purchases=5000,
        seed=42,
    )
    return products_df, customers_df, purchases_df


def test_dataset_generation_record_counts(sample_data):
    products_df, customers_df, purchases_df = sample_data

    assert len(products_df) >= 100, f"Expected >= 100 products, got {len(products_df)}"
    assert len(customers_df) >= 1000, f"Expected >= 1000 customers, got {len(customers_df)}"
    assert len(purchases_df) >= 5000, f"Expected >= 5000 purchases, got {len(purchases_df)}"


def test_dataset_columns(sample_data):
    products_df, customers_df, purchases_df = sample_data

    expected_prod_cols = {
        "product_id", "product_name", "category", "price", "cost",
        "units_sold", "revenue", "average_rating", "review_count",
        "conversion_rate", "inventory",
    }
    assert expected_prod_cols.issubset(set(products_df.columns))

    expected_cust_cols = {
        "customer_id", "name", "email", "age", "occupation",
        "city", "customer_type", "total_spend", "total_orders",
        "last_purchase_date",
    }
    assert expected_cust_cols.issubset(set(customers_df.columns))

    expected_pur_cols = {
        "purchase_id", "customer_id", "product_id", "purchase_date",
        "quantity", "unit_price", "total_amount",
    }
    assert expected_pur_cols.issubset(set(purchases_df.columns))


def test_dataset_mathematical_consistency(sample_data):
    products_df, customers_df, purchases_df = sample_data

    # 1. Purchase line items: total_amount == round(quantity * unit_price, 2)
    expected_totals = (purchases_df["quantity"] * purchases_df["unit_price"]).round(2)
    diff = (purchases_df["total_amount"] - expected_totals).abs()
    assert (diff <= 0.01).all(), "Purchase line item total mismatch"

    # 2. Customer spend and orders
    cust_spend = purchases_df.groupby("customer_id")["total_amount"].sum().to_dict()
    cust_orders = purchases_df.groupby("customer_id")["purchase_id"].count().to_dict()

    for _, row in customers_df.iterrows():
        c_id = row["customer_id"]
        expected_spend = round(cust_spend.get(c_id, 0.0), 2)
        expected_orders = int(cust_orders.get(c_id, 0))
        assert abs(row["total_spend"] - expected_spend) <= 0.02
        assert row["total_orders"] == expected_orders

    # 3. Product units sold and revenue
    prod_units = purchases_df.groupby("product_id")["quantity"].sum().to_dict()
    prod_rev = purchases_df.groupby("product_id")["total_amount"].sum().to_dict()

    for _, row in products_df.iterrows():
        p_id = row["product_id"]
        expected_units = int(prod_units.get(p_id, 0))
        expected_rev = round(prod_rev.get(p_id, 0.0), 2)
        assert row["units_sold"] == expected_units
        assert abs(row["revenue"] - expected_rev) <= 0.02


def test_validation_passes_on_valid_data(sample_data):
    products_df, customers_df, purchases_df = sample_data
    # Should complete with no exception
    validate_all(products_df, customers_df, purchases_df)


def test_validation_fails_on_missing_column(sample_data):
    products_df, _, _ = sample_data
    bad_products = products_df.drop(columns=["price"])
    with pytest.raises(DataValidationError, match="missing required column"):
        validate_products(bad_products)


def test_validation_fails_on_null_id(sample_data):
    products_df, _, _ = sample_data
    bad_products = products_df.copy()
    bad_products.loc[0, "product_id"] = None
    with pytest.raises(DataValidationError, match="null or empty"):
        validate_products(bad_products)


def test_validation_fails_on_duplicate_id(sample_data):
    _, customers_df, _ = sample_data
    bad_customers = customers_df.copy()
    bad_customers.loc[1, "customer_id"] = bad_customers.loc[0, "customer_id"]
    with pytest.raises(DataValidationError, match="duplicate customer_id"):
        validate_customers(bad_customers)


def test_validation_fails_on_negative_price(sample_data):
    products_df, _, _ = sample_data
    bad_products = products_df.copy()
    bad_products.loc[0, "price"] = -10.0
    with pytest.raises(DataValidationError, match="negative values"):
        validate_products(bad_products)


def test_validation_fails_on_inconsistent_purchase_total(sample_data):
    _, _, purchases_df = sample_data
    bad_purchases = purchases_df.copy()
    bad_purchases.loc[0, "total_amount"] = 9999.99  # deliberate mismatch
    with pytest.raises(DataValidationError, match="total_amount does not match"):
        validate_purchases(bad_purchases)


def test_validation_fails_on_invalid_foreign_key(sample_data):
    products_df, customers_df, purchases_df = sample_data
    bad_purchases = purchases_df.copy()
    bad_purchases.loc[0, "customer_id"] = "cust_nonexistent_99999"
    with pytest.raises(DataValidationError, match="nonexistent customer_id"):
        validate_foreign_keys(products_df, customers_df, bad_purchases)


def test_validation_fails_on_mismatched_aggregate_spend(sample_data):
    products_df, customers_df, purchases_df = sample_data
    bad_customers = customers_df.copy()
    bad_customers.loc[0, "total_spend"] = bad_customers.loc[0, "total_spend"] + 500.0
    with pytest.raises(DataValidationError, match="customer total_spend mismatch"):
        validate_aggregated_totals(products_df, bad_customers, purchases_df)
