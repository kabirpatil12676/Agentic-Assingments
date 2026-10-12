"""
Data validation module.

Validates products, customers, and purchases datasets for:
- Missing required columns
- Null or empty IDs
- Duplicate primary keys
- Negative numeric values (prices, costs, revenue, inventory, etc.)
- Inconsistent line-item totals (quantity * unit_price == total_amount)
- Invalid foreign keys (purchases referencing nonexistent customers or products)
- Cross-dataset aggregated total consistency
"""

from __future__ import annotations

import logging
from typing import Sequence
import pandas as pd

logger = logging.getLogger(__name__)


class DataValidationError(ValueError):
    """Raised when dataset validation fails."""


PRODUCT_REQUIRED_COLUMNS: list[str] = [
    "product_id",
    "product_name",
    "category",
    "price",
    "cost",
    "units_sold",
    "revenue",
    "average_rating",
    "review_count",
    "conversion_rate",
    "inventory",
]

CUSTOMER_REQUIRED_COLUMNS: list[str] = [
    "customer_id",
    "name",
    "email",
    "age",
    "occupation",
    "city",
    "customer_type",
    "total_spend",
    "total_orders",
    "last_purchase_date",
]

PURCHASE_REQUIRED_COLUMNS: list[str] = [
    "purchase_id",
    "customer_id",
    "product_id",
    "purchase_date",
    "quantity",
    "unit_price",
    "total_amount",
]


def _check_missing_columns(df: pd.DataFrame, required_columns: Sequence[str], dataset_name: str) -> None:
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise DataValidationError(
            f"Validation failed for {dataset_name}: missing required column(s): {missing}"
        )


def validate_products(df: pd.DataFrame) -> None:
    """Validate products DataFrame."""
    _check_missing_columns(df, PRODUCT_REQUIRED_COLUMNS, "products")

    # Null / empty primary keys
    if df["product_id"].isna().any() or (df["product_id"].astype(str).str.strip() == "").any():
        raise DataValidationError("Validation failed for products: null or empty product_id found.")

    # Duplicate IDs
    duplicates = df[df["product_id"].duplicated()]["product_id"].tolist()
    if duplicates:
        raise DataValidationError(f"Validation failed for products: duplicate product_id(s): {duplicates[:5]}")

    # Non-negative checks
    numeric_cols = ["price", "cost", "units_sold", "revenue", "average_rating", "review_count", "conversion_rate", "inventory"]
    for col in numeric_cols:
        invalid = df[df[col] < 0]
        if not invalid.empty:
            raise DataValidationError(
                f"Validation failed for products: column '{col}' contains negative values in rows: {invalid['product_id'].tolist()[:5]}"
            )

    # Cost vs price check
    over_cost = df[df["cost"] > df["price"]]
    if not over_cost.empty:
        raise DataValidationError(
            f"Validation failed for products: cost exceeds price for product_id(s): {over_cost['product_id'].tolist()[:5]}"
        )

    # Rating bounds [0, 5]
    invalid_ratings = df[(df["average_rating"] < 0) | (df["average_rating"] > 5.0)]
    if not invalid_ratings.empty:
        raise DataValidationError(
            f"Validation failed for products: average_rating must be between 0 and 5, found invalid for: {invalid_ratings['product_id'].tolist()[:5]}"
        )

    # Conversion rate bounds [0, 1]
    invalid_conv = df[(df["conversion_rate"] < 0) | (df["conversion_rate"] > 1.0)]
    if not invalid_conv.empty:
        raise DataValidationError(
            f"Validation failed for products: conversion_rate must be between 0 and 1, found invalid for: {invalid_conv['product_id'].tolist()[:5]}"
        )


def validate_customers(df: pd.DataFrame) -> None:
    """Validate customers DataFrame."""
    _check_missing_columns(df, CUSTOMER_REQUIRED_COLUMNS, "customers")

    # Null / empty primary keys
    if df["customer_id"].isna().any() or (df["customer_id"].astype(str).str.strip() == "").any():
        raise DataValidationError("Validation failed for customers: null or empty customer_id found.")

    # Duplicate IDs
    duplicates = df[df["customer_id"].duplicated()]["customer_id"].tolist()
    if duplicates:
        raise DataValidationError(f"Validation failed for customers: duplicate customer_id(s): {duplicates[:5]}")

    # Age check
    invalid_age = df[df["age"] <= 0]
    if not invalid_age.empty:
        raise DataValidationError(
            f"Validation failed for customers: age must be positive, found invalid in: {invalid_age['customer_id'].tolist()[:5]}"
        )

    # Spend and orders checks
    for col in ["total_spend", "total_orders"]:
        invalid = df[df[col] < 0]
        if not invalid.empty:
            raise DataValidationError(
                f"Validation failed for customers: '{col}' contains negative values in: {invalid['customer_id'].tolist()[:5]}"
            )


def validate_purchases(df: pd.DataFrame) -> None:
    """Validate purchases DataFrame."""
    _check_missing_columns(df, PURCHASE_REQUIRED_COLUMNS, "purchases")

    # Null / empty IDs
    for id_col in ["purchase_id", "customer_id", "product_id"]:
        if df[id_col].isna().any() or (df[id_col].astype(str).str.strip() == "").any():
            raise DataValidationError(f"Validation failed for purchases: null or empty '{id_col}' found.")

    # Duplicate purchase_id
    duplicates = df[df["purchase_id"].duplicated()]["purchase_id"].tolist()
    if duplicates:
        raise DataValidationError(f"Validation failed for purchases: duplicate purchase_id(s): {duplicates[:5]}")

    # Quantity, unit_price, total_amount bounds
    invalid_qty = df[df["quantity"] <= 0]
    if not invalid_qty.empty:
        raise DataValidationError(
            f"Validation failed for purchases: quantity must be > 0 in: {invalid_qty['purchase_id'].tolist()[:5]}"
        )

    invalid_price = df[df["unit_price"] < 0]
    if not invalid_price.empty:
        raise DataValidationError(
            f"Validation failed for purchases: unit_price cannot be negative in: {invalid_price['purchase_id'].tolist()[:5]}"
        )

    invalid_total = df[df["total_amount"] < 0]
    if not invalid_total.empty:
        raise DataValidationError(
            f"Validation failed for purchases: total_amount cannot be negative in: {invalid_total['purchase_id'].tolist()[:5]}"
        )

    # Arithmetic consistency: total_amount == round(quantity * unit_price, 2)
    expected_totals = (df["quantity"] * df["unit_price"]).round(2)
    diff = (df["total_amount"] - expected_totals).abs()
    inconsistent = df[diff > 0.01]
    if not inconsistent.empty:
        bad_ids = inconsistent["purchase_id"].tolist()[:5]
        raise DataValidationError(
            f"Validation failed for purchases: total_amount does not match quantity * unit_price for: {bad_ids}"
        )


def validate_foreign_keys(
    products_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    purchases_df: pd.DataFrame,
) -> None:
    """Ensure all purchases reference valid customer_ids and product_ids."""
    valid_customers = set(customers_df["customer_id"])
    valid_products = set(products_df["product_id"])

    missing_customers = set(purchases_df["customer_id"]) - valid_customers
    if missing_customers:
        raise DataValidationError(
            f"Validation failed: purchases reference nonexistent customer_id(s): {list(missing_customers)[:5]}"
        )

    missing_products = set(purchases_df["product_id"]) - valid_products
    if missing_products:
        raise DataValidationError(
            f"Validation failed: purchases reference nonexistent product_id(s): {list(missing_products)[:5]}"
        )


def validate_aggregated_totals(
    products_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    purchases_df: pd.DataFrame,
    tolerance: float = 0.05,
) -> None:
    """
    Ensure customer and product rollups match purchases aggregate calculations.
    """
    # 1. Customer total_orders and total_spend
    cust_agg = (
        purchases_df.groupby("customer_id")
        .agg(calc_orders=("purchase_id", "count"), calc_spend=("total_amount", "sum"))
        .reset_index()
    )
    cust_merged = customers_df.merge(cust_agg, on="customer_id", how="left")
    cust_merged["calc_orders"] = cust_merged["calc_orders"].fillna(0).astype(int)
    cust_merged["calc_spend"] = cust_merged["calc_spend"].fillna(0.0).round(2)

    mismatched_orders = cust_merged[cust_merged["total_orders"] != cust_merged["calc_orders"]]
    if not mismatched_orders.empty:
        raise DataValidationError(
            f"Validation failed: customer total_orders mismatch for: {mismatched_orders['customer_id'].tolist()[:5]}"
        )

    spend_diff = (cust_merged["total_spend"] - cust_merged["calc_spend"]).abs()
    mismatched_spend = cust_merged[spend_diff > tolerance]
    if not mismatched_spend.empty:
        raise DataValidationError(
            f"Validation failed: customer total_spend mismatch for: {mismatched_spend['customer_id'].tolist()[:5]}"
        )

    # 2. Product units_sold and revenue
    prod_agg = (
        purchases_df.groupby("product_id")
        .agg(calc_units=("quantity", "sum"), calc_rev=("total_amount", "sum"))
        .reset_index()
    )
    prod_merged = products_df.merge(prod_agg, on="product_id", how="left")
    prod_merged["calc_units"] = prod_merged["calc_units"].fillna(0).astype(int)
    prod_merged["calc_rev"] = prod_merged["calc_rev"].fillna(0.0).round(2)

    mismatched_units = prod_merged[prod_merged["units_sold"] != prod_merged["calc_units"]]
    if not mismatched_units.empty:
        raise DataValidationError(
            f"Validation failed: product units_sold mismatch for: {mismatched_units['product_id'].tolist()[:5]}"
        )

    rev_diff = (prod_merged["revenue"] - prod_merged["calc_rev"]).abs()
    mismatched_rev = prod_merged[rev_diff > tolerance]
    if not mismatched_rev.empty:
        raise DataValidationError(
            f"Validation failed: product revenue mismatch for: {mismatched_rev['product_id'].tolist()[:5]}"
        )


def validate_all(
    products_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    purchases_df: pd.DataFrame,
) -> None:
    """Run full validation across all datasets and their cross-relationships."""
    validate_products(products_df)
    validate_customers(customers_df)
    validate_purchases(purchases_df)
    validate_foreign_keys(products_df, customers_df, purchases_df)
    validate_aggregated_totals(products_df, customers_df, purchases_df)
    logger.info("All dataset validation checks passed successfully.")
