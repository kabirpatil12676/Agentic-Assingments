"""
Tests for DataService and SQLite persistence.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Config, LLMConfig
from app.services.data_service import DataService
from scripts.seed_data import generate_dataset, save_to_csv


@pytest.fixture
def temp_service():
    """Create a temporary DataService with an isolated SQLite database and CSVs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        raw_dir = tmp_path / "raw"
        gen_dir = tmp_path / "generated"
        raw_dir.mkdir(parents=True)
        gen_dir.mkdir(parents=True)

        db_path = gen_dir / "marketing.db"
        cfg = Config(
            db_path=db_path,
            llm=LLMConfig(),
        )

        p_df, c_df, pur_df = generate_dataset(
            num_products=100,
            num_customers=1000,
            min_purchases=5000,
            seed=42,
        )
        save_to_csv(p_df, c_df, pur_df, target_dir=raw_dir)

        ds = DataService(config=cfg)
        ds.populate_from_csv(
            products_csv=raw_dir / "products.csv",
            customers_csv=raw_dir / "customers.csv",
            purchases_csv=raw_dir / "purchases.csv",
        )
        yield ds


def test_sqlite_table_counts(temp_service):
    ds = temp_service

    products = ds.load_products()
    customers = ds.load_customers()
    purchases = ds.load_purchases()

    assert len(products) >= 100
    assert len(customers) >= 1000
    assert len(purchases) >= 5000


def test_sqlite_get_product(temp_service):
    ds = temp_service
    products = ds.load_products()
    sample_id = products.iloc[0]["product_id"]

    prod = ds.get_product(sample_id)
    assert prod is not None
    assert prod["product_id"] == sample_id
    assert prod["price"] > 0

    assert ds.get_product("nonexistent_prod_id") is None


def test_sqlite_get_customer(temp_service):
    ds = temp_service
    customers = ds.load_customers()
    sample_id = customers.iloc[0]["customer_id"]

    cust = ds.get_customer(sample_id)
    assert cust is not None
    assert cust["customer_id"] == sample_id
    assert "@" in cust["email"]

    assert ds.get_customer("nonexistent_cust_id") is None


def test_sqlite_campaign_crud(temp_service):
    ds = temp_service

    campaign_data = {
        "campaign_id": "cmp_test_001",
        "name": "Spring Headphones Launch",
        "product_id": "prod_0001",
        "segment_id": "seg_young_pros",
        "channel": "email",
        "status": "planned",
        "budget": 1500.0,
        "target_audience": "Students and Tech workers",
        "variant": "A",
        "created_at": "2026-03-01T10:00:00Z",
        "subject_line": "Exclusive 20% Off",
        "headline": "Upgrade your sound",
        "body": "Check out our latest wireless tech.",
        "cta": "Shop Now",
    }

    ds.save_campaign(campaign_data)

    retrieved = ds.get_campaign("cmp_test_001")
    assert retrieved is not None
    assert retrieved["name"] == "Spring Headphones Launch"
    assert retrieved["budget"] == 1500.0
    assert retrieved["channel"] == "email"

    all_campaigns = ds.list_campaigns()
    assert any(c["campaign_id"] == "cmp_test_001" for c in all_campaigns)


def test_sqlite_campaign_events(temp_service):
    ds = temp_service

    # First insert a campaign so foreign keys pass
    ds.save_campaign({
        "campaign_id": "cmp_ev_001",
        "name": "Event Test Campaign",
        "channel": "email",
        "created_at": "2026-03-01T10:00:00Z",
    })

    customers = ds.load_customers()
    c1 = customers.iloc[0]["customer_id"]
    c2 = customers.iloc[1]["customer_id"]

    events = [
        {
            "event_id": "evt_001",
            "campaign_id": "cmp_ev_001",
            "customer_id": c1,
            "variant": "control",
            "channel": "email",
            "sent": 1,
            "opened": 1,
            "clicked": 1,
            "converted": 1,
            "revenue": 149.99,
            "timestamp": "2026-03-01 12:00:00",
        },
        {
            "event_id": "evt_002",
            "campaign_id": "cmp_ev_001",
            "customer_id": c2,
            "variant": "variant_A",
            "channel": "email",
            "sent": 1,
            "opened": 1,
            "clicked": 0,
            "converted": 0,
            "revenue": 0.0,
            "timestamp": "2026-03-01 12:05:00",
        },
    ]

    ds.save_campaign_events(events)
    events_df = ds.get_campaign_events("cmp_ev_001")

    assert len(events_df) == 2
    assert set(events_df["event_id"]) == {"evt_001", "evt_002"}
    assert events_df["revenue"].sum() == 149.99
