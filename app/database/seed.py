"""
Database Seeder

Loads the Olist Brazilian E-Commerce dataset into the SQLite
database defined by schema.sql.

Run:

    python -m app.database.seed
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from app.core.config import BASE_DIR, settings


class DatabaseSeeder:
    """
    Populate the SQLite database from CSV files.
    """

    DATASET_FILES = {
        "customers": "olist_customers_dataset.csv",
        "sellers": "olist_sellers_dataset.csv",
        "products": "olist_products_dataset.csv",
        "product_categories": "product_category_name_translation.csv",
        "orders": "olist_orders_dataset.csv",
        "order_items": "olist_order_items_dataset.csv",
        "payments": "olist_order_payments_dataset.csv",
        "reviews": "olist_order_reviews_dataset.csv",
    }

    def __init__(self) -> None:
        self.dataset_path = Path(settings.DATASET_PATH)
        self.database_path = Path(settings.DATABASE_PATH)
        self.schema_path = BASE_DIR / "app" / "database" / "schema.sql"

    # ---------------------------------------------------------

    def seed(self) -> None:
        """
        Import all CSV files into SQLite.
        """

        if not self.dataset_path.exists():
            raise FileNotFoundError(
                f"Dataset directory not found: {self.dataset_path}"
            )

        if not self.schema_path.exists():
            raise FileNotFoundError(
                f"Schema file not found: {self.schema_path}"
            )

        schema_sql = self.schema_path.read_text(encoding="utf-8")

        connection = sqlite3.connect(self.database_path)
        connection.execute("PRAGMA foreign_keys = ON;")

        try:
            # Drop all existing tables and views so repeated seeding
            # produces deterministic results.
            cursor = connection.execute(
                "SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view')"
            )
            objects = cursor.fetchall()

            for name, obj_type in objects:
                if name.startswith("sqlite_"):
                    continue
                if obj_type == "table":
                    connection.execute(f"DROP TABLE IF EXISTS {name}")
                else:
                    connection.execute(f"DROP VIEW IF EXISTS {name}")

            connection.commit()

            print("Executing schema.sql...")
            connection.executescript(schema_sql)
            connection.commit()
            print("  [OK] Schema created\n")

            for table_name, filename in self.DATASET_FILES.items():

                csv_path = self.dataset_path / filename

                if not csv_path.exists():
                    raise FileNotFoundError(
                        f"Missing dataset file: {csv_path}"
                    )

                print(f"Loading {filename}...")

                dataframe = pd.read_csv(csv_path)

                # Align CSV column names with schema where they differ.
                if table_name == "product_categories":
                    dataframe = dataframe.rename(
                        columns={
                            "product_category_name": "category_name",
                            "product_category_name_english": "category_name_english",
                        }
                    )

                # reviews table has a surrogate PK (review_pk)
                # that does not exist in the CSV.
                if table_name == "reviews":
                    dataframe = dataframe.drop(
                        columns=["review_pk"],
                        errors="ignore",
                    )

                dataframe.to_sql(
                    table_name,
                    connection,
                    if_exists="append",
                    index=False,
                )

                row_count = len(dataframe)
                cursor = connection.execute(
                    f"SELECT COUNT(*) FROM {table_name}"
                )
                final_count = cursor.fetchone()[0]

                print(
                    f"  [OK] Inserted {row_count:,} rows "
                    f"into '{table_name}' "
                    f"(final count: {final_count:,})"
                )

            # Verify foreign-key integrity
            print("\nVerifying foreign-key integrity...")
            cursor = connection.execute("PRAGMA foreign_key_check")
            violations = cursor.fetchall()

            if violations:
                violation_list = "\n".join(
                    f"  {row}" for row in violations
                )
                raise RuntimeError(
                    "Foreign-key constraint violations detected:\n"
                    f"{violation_list}"
                )

            print("  [OK] No foreign-key violations\n")

            # Summary
            print("=" * 60)
            print("Database seeding completed successfully")
            print("=" * 60)
            print(f"Database path : {self.database_path}")
            print("=" * 60)

        except Exception as exc:
            connection.rollback()
            raise RuntimeError(
                f"Database seeding failed: {exc}"
            ) from exc

        finally:
            connection.close()


# ==========================================================
# CLI
# ==========================================================

if __name__ == "__main__":
    DatabaseSeeder().seed()
