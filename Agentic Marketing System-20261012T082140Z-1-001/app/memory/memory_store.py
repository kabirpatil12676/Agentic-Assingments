"""
Long-term memory store backed by SQLite.

Stores:
  - Past campaign results and what worked
  - Customer segment performance history
  - Optimisation decisions and outcomes

This gives agents access to historical context for better decisions.

Implementation pending.
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, TYPE_CHECKING

if TYPE_CHECKING:
    from app.config import Config

logger = logging.getLogger(__name__)


class MemoryStore:
    """SQLite-backed long-term memory for agents."""

    def __init__(self, config: "Config") -> None:
        self.db_path: Path = config.db_path
        logger.info("MemoryStore initialised  db=%s", self.db_path)
        self.init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield a properly closed SQLite connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        """Create memory tables if they don't exist."""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS kv_memory (
                    namespace TEXT,
                    key TEXT,
                    value TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (namespace, key)
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS campaign_memory (
                    campaign_id TEXT PRIMARY KEY,
                    product_category TEXT,
                    outcome_json TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

    def store(self, namespace: str, key: str, value: Any) -> None:
        """Store a key-value record."""
        value_str = json.dumps(value)
        with self._get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO kv_memory (namespace, key, value)
                VALUES (?, ?, ?)
            ''', (namespace, key, value_str))

    def recall(self, namespace: str, key: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        """Recall stored records."""
        with self._get_connection() as conn:
            if key:
                cursor = conn.execute('''
                    SELECT key, value, timestamp FROM kv_memory
                    WHERE namespace = ? AND key = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (namespace, key, limit))
            else:
                cursor = conn.execute('''
                    SELECT key, value, timestamp FROM kv_memory
                    WHERE namespace = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (namespace, limit))

            results = []
            for row in cursor.fetchall():
                try:
                    val = json.loads(row['value'])
                except json.JSONDecodeError:
                    val = row['value']
                results.append({
                    "key": row['key'],
                    "value": val,
                    "timestamp": row['timestamp']
                })
            return results

    def store_campaign_outcome(self, campaign_id: str, outcome: dict[str, Any]) -> None:
        """Persist a campaign outcome for future reference.
        
        Called on EVERY completed campaign iteration (including OPTIMIZE loops)
        so that the next run or next iteration has historical context.
        """
        product_category = outcome.get("product_category", "unknown")
        outcome_str = json.dumps(outcome)
        with self._get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO campaign_memory (campaign_id, product_category, outcome_json)
                VALUES (?, ?, ?)
            ''', (campaign_id, product_category, outcome_str))
        logger.info("MemoryStore: persisted outcome for campaign=%s category=%s", campaign_id, product_category)

    def get_similar_campaigns(self, product_category: str, limit: int = 5) -> list[dict[str, Any]]:
        """Retrieve past campaigns for similar products."""
        with self._get_connection() as conn:
            cursor = conn.execute('''
                SELECT campaign_id, outcome_json, timestamp FROM campaign_memory
                WHERE product_category = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (product_category, limit))

            results = []
            for row in cursor.fetchall():
                try:
                    outcome = json.loads(row['outcome_json'])
                except json.JSONDecodeError:
                    outcome = {}
                results.append({
                    "campaign_id": row['campaign_id'],
                    "outcome": outcome,
                    "timestamp": row['timestamp']
                })
            return results
