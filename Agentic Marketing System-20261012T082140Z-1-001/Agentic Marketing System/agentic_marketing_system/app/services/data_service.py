"""
Data service – manages SQLite persistence and CSV ingestion.

Handles initialization, population, and querying for:
- products
- customers
- purchases
- campaigns
- campaign_events

All operations use parameterized SQL queries and enforce foreign keys.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Optional, Sequence

import pandas as pd

from app.config import Config, load_config
from app.services.validator import validate_all

logger = logging.getLogger(__name__)


class DataService:
    """Centralised data access service for CSV and SQLite."""

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or load_config()
        self.db_path: Path = Path(self.config.db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("DataService initialised  db=%s", self.db_path)

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield an open SQLite connection with foreign keys enabled."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        """Create database tables and indexes if they do not already exist."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            cost REAL NOT NULL,
            units_sold INTEGER NOT NULL DEFAULT 0,
            revenue REAL NOT NULL DEFAULT 0.0,
            average_rating REAL NOT NULL DEFAULT 0.0,
            review_count INTEGER NOT NULL DEFAULT 0,
            conversion_rate REAL NOT NULL DEFAULT 0.0,
            inventory INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            age INTEGER NOT NULL,
            occupation TEXT NOT NULL,
            city TEXT NOT NULL,
            customer_type TEXT NOT NULL,
            total_spend REAL NOT NULL DEFAULT 0.0,
            total_orders INTEGER NOT NULL DEFAULT 0,
            last_purchase_date TEXT
        );

        CREATE TABLE IF NOT EXISTS purchases (
            purchase_id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            purchase_date TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_amount REAL NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );

        CREATE TABLE IF NOT EXISTS campaigns (
            campaign_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            product_id TEXT,
            segment_id TEXT,
            channel TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            budget REAL NOT NULL DEFAULT 0.0,
            target_audience TEXT,
            variant TEXT,
            created_at TEXT NOT NULL,
            scheduled_at TEXT,
            subject_line TEXT,
            headline TEXT,
            body TEXT,
            cta TEXT,
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );

        CREATE TABLE IF NOT EXISTS campaign_events (
            event_id TEXT PRIMARY KEY,
            campaign_id TEXT NOT NULL,
            customer_id TEXT NOT NULL,
            variant TEXT NOT NULL DEFAULT 'control',
            channel TEXT NOT NULL DEFAULT 'email',
            sent INTEGER NOT NULL DEFAULT 1,
            opened INTEGER NOT NULL DEFAULT 0,
            clicked INTEGER NOT NULL DEFAULT 0,
            converted INTEGER NOT NULL DEFAULT 0,
            revenue REAL NOT NULL DEFAULT 0.0,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id),
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );

        CREATE INDEX IF NOT EXISTS idx_purchases_customer ON purchases(customer_id);
        CREATE INDEX IF NOT EXISTS idx_purchases_product ON purchases(product_id);
        CREATE INDEX IF NOT EXISTS idx_campaign_events_campaign ON campaign_events(campaign_id);
        CREATE INDEX IF NOT EXISTS idx_campaign_events_customer ON campaign_events(customer_id);
        CREATE INDEX IF NOT EXISTS idx_customers_type ON customers(customer_type);
        CREATE INDEX IF NOT EXISTS idx_customers_occupation ON customers(occupation);
        CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
        """
        with self.get_connection() as conn:
            conn.executescript(schema_sql)
        logger.info("Database schema initialized at %s", self.db_path)

    def populate_from_csv(
        self,
        products_csv: Optional[Path | str] = None,
        customers_csv: Optional[Path | str] = None,
        purchases_csv: Optional[Path | str] = None,
        validate: bool = True,
    ) -> dict[str, int]:
        """
        Load CSVs, validate data integrity, and populate SQLite tables.

        Returns:
            Dictionary containing record counts inserted per table.
        """
        raw_dir = Path(self.config.db_path).resolve().parent.parent / "raw"
        p_path = Path(products_csv) if products_csv else raw_dir / "products.csv"
        c_path = Path(customers_csv) if customers_csv else raw_dir / "customers.csv"
        pur_path = Path(purchases_csv) if purchases_csv else raw_dir / "purchases.csv"

        if not p_path.exists() or not c_path.exists() or not pur_path.exists():
            raise FileNotFoundError(
                f"Missing dataset CSVs. Ensure raw data exists at:\n"
                f"  {p_path}\n  {c_path}\n  {pur_path}"
            )

        products_df = pd.read_csv(p_path)
        customers_df = pd.read_csv(c_path)
        purchases_df = pd.read_csv(pur_path)

        if validate:
            validate_all(products_df, customers_df, purchases_df)

        self.init_db()

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Insert products
            prod_rows = [
                (
                    row["product_id"],
                    row["product_name"],
                    row["category"],
                    float(row["price"]),
                    float(row["cost"]),
                    int(row["units_sold"]),
                    float(row["revenue"]),
                    float(row["average_rating"]),
                    int(row["review_count"]),
                    float(row["conversion_rate"]),
                    int(row["inventory"]),
                )
                for _, row in products_df.iterrows()
            ]
            cursor.executemany(
                """
                INSERT OR REPLACE INTO products (
                    product_id, product_name, category, price, cost,
                    units_sold, revenue, average_rating, review_count,
                    conversion_rate, inventory
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                prod_rows,
            )

            # Insert customers
            cust_rows = [
                (
                    row["customer_id"],
                    row["name"],
                    row["email"],
                    int(row["age"]),
                    row["occupation"],
                    row["city"],
                    row["customer_type"],
                    float(row["total_spend"]),
                    int(row["total_orders"]),
                    str(row["last_purchase_date"]) if pd.notna(row["last_purchase_date"]) else "",
                )
                for _, row in customers_df.iterrows()
            ]
            cursor.executemany(
                """
                INSERT OR REPLACE INTO customers (
                    customer_id, name, email, age, occupation, city,
                    customer_type, total_spend, total_orders, last_purchase_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                cust_rows,
            )

            # Insert purchases
            pur_rows = [
                (
                    row["purchase_id"],
                    row["customer_id"],
                    row["product_id"],
                    str(row["purchase_date"]),
                    int(row["quantity"]),
                    float(row["unit_price"]),
                    float(row["total_amount"]),
                )
                for _, row in purchases_df.iterrows()
            ]
            cursor.executemany(
                """
                INSERT OR REPLACE INTO purchases (
                    purchase_id, customer_id, product_id, purchase_date,
                    quantity, unit_price, total_amount
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                pur_rows,
            )

        counts = {
            "products": len(products_df),
            "customers": len(customers_df),
            "purchases": len(purchases_df),
        }
        logger.info("Successfully populated SQLite database: %s", counts)
        return counts

    def load_products(self) -> pd.DataFrame:
        """Load product catalogue from SQLite as DataFrame."""
        with self.get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM products ORDER BY product_id", conn)

    def load_customers(self) -> pd.DataFrame:
        """Load customer dataset from SQLite as DataFrame."""
        with self.get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM customers ORDER BY customer_id", conn)

    def load_purchases(self) -> pd.DataFrame:
        """Load purchases from SQLite as DataFrame."""
        with self.get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM purchases ORDER BY purchase_id", conn)

    def get_product(self, product_id: str) -> Optional[dict[str, Any]]:
        """Retrieve single product by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_customer(self, customer_id: str) -> Optional[dict[str, Any]]:
        """Retrieve single customer by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def save_campaign(self, campaign_data: dict[str, Any]) -> None:
        """Persist a campaign record using parameterized SQL."""
        self.init_db()
        sql = """
        INSERT OR REPLACE INTO campaigns (
            campaign_id, name, product_id, segment_id, channel,
            status, budget, target_audience, variant, created_at,
            scheduled_at, subject_line, headline, body, cta
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            campaign_data["campaign_id"],
            campaign_data["name"],
            campaign_data.get("product_id"),
            campaign_data.get("segment_id"),
            campaign_data["channel"],
            campaign_data.get("status", "draft"),
            float(campaign_data.get("budget", 0.0)),
            campaign_data.get("target_audience"),
            campaign_data.get("variant"),
            campaign_data["created_at"],
            campaign_data.get("scheduled_at"),
            campaign_data.get("subject_line"),
            campaign_data.get("headline"),
            campaign_data.get("body"),
            campaign_data.get("cta"),
        )
        with self.get_connection() as conn:
            conn.execute(sql, params)

    def get_campaign(self, campaign_id: str) -> Optional[dict[str, Any]]:
        """Retrieve campaign by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_campaigns(self) -> list[dict[str, Any]]:
        """List all campaigns ordered by creation date."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM campaigns ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def save_campaign_events(self, events: Sequence[dict[str, Any]]) -> None:
        """Persist campaign interaction events using parameterized executemany."""
        self.init_db()
        sql = """
        INSERT OR REPLACE INTO campaign_events (
            event_id, campaign_id, customer_id, variant, channel,
            sent, opened, clicked, converted, revenue, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        rows = [
            (
                ev["event_id"],
                ev["campaign_id"],
                ev["customer_id"],
                ev.get("variant", "control"),
                ev.get("channel", "email"),
                int(ev.get("sent", 1)),
                int(ev.get("opened", 0)),
                int(ev.get("clicked", 0)),
                int(ev.get("converted", 0)),
                float(ev.get("revenue", 0.0)),
                ev["timestamp"],
            )
            for ev in events
        ]
        with self.get_connection() as conn:
            conn.executemany(sql, rows)

    def get_campaign_events(self, campaign_id: str) -> pd.DataFrame:
        """Retrieve all events recorded for a campaign."""
        with self.get_connection() as conn:
            return pd.read_sql_query(
                "SELECT * FROM campaign_events WHERE campaign_id = ? ORDER BY timestamp",
                conn,
                params=(campaign_id,),
            )

    def save_campaign_results(self, data: dict[str, Any]) -> None:
        """
        Preserve existing method signature.
        Saves campaign or campaign execution summary.
        """
        if "campaign_id" in data and "events" in data:
            self.save_campaign_events(data["events"])
        elif "campaign_id" in data and "name" in data:
            self.save_campaign(data)
