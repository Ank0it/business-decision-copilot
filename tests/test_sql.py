"""
Unit tests for SQL Generator, SQL Validator and SQL Executor.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.models.sql import SQLGeneration, SQLRefusal
from app.services.sql_executor import (
    SQLExecutionError,
    SQLExecutor,
)
from app.services.sql_generator import (
    SQLGenerationError,
    SQLGenerator,
)
from app.services.sql_validator import sql_validator


# ==========================================================
# Fixtures
# ==========================================================

@pytest.fixture
def generator():
    return SQLGenerator()


@pytest.fixture
def executor():
    return SQLExecutor()


# ==========================================================
# SQL Validator
# ==========================================================

def test_validator_accepts_select():

    result = sql_validator.validate(
        "SELECT * FROM customers"
    )

    assert result.valid is True


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO customers VALUES (1)",
        "UPDATE customers SET customer_city='Delhi'",
        "DELETE FROM customers",
        "DROP TABLE customers",
        "ALTER TABLE customers ADD COLUMN x INT",
        "CREATE TABLE test(id INTEGER)",
        "TRUNCATE TABLE customers",
    ],
)
def test_validator_blocks_destructive_queries(sql):

    result = sql_validator.validate(sql)

    assert result.valid is False


def test_validator_blocks_multiple_statements():

    result = sql_validator.validate(
        "SELECT * FROM customers; DELETE FROM customers;"
    )

    assert result.valid is False


def test_validator_unknown_table():

    result = sql_validator.validate(
        "SELECT * FROM hackers"
    )

    assert result.valid is False

    assert "Unknown table" in result.reason


def test_validator_empty_sql():

    result = sql_validator.validate("")

    assert result.valid is False


# ==========================================================
# SQL Generator
# ==========================================================

def test_sql_generation_success(
    generator,
    monkeypatch,
):

    monkeypatch.setattr(
        "app.services.sql_generator.llm.generate",
        lambda prompt: """
        {
            "sql":"SELECT * FROM customers"
        }
        """,
    )

    monkeypatch.setattr(
        "app.services.sql_generator.parser.parse_json",
        lambda response: {
            "sql": "SELECT * FROM customers"
        },
    )

    result = generator.generate(
        "Show customers"
    )

    assert isinstance(result, SQLGeneration)

    assert result.sql.startswith("SELECT")


def test_sql_generation_refusal(
    generator,
    monkeypatch,
):

    monkeypatch.setattr(
        "app.services.sql_generator.llm.generate",
        lambda prompt: """
        {
            "refuse":true,
            "reason":"Unsafe request"
        }
        """,
    )

    monkeypatch.setattr(
        "app.services.sql_generator.parser.parse_json",
        lambda response: {
            "refuse": True,
            "reason": "Unsafe request",
        },
    )

    result = generator.generate(
        "Delete everything"
    )

    assert isinstance(result, SQLRefusal)

    assert result.reason == "Unsafe request"


def test_sql_generation_empty_sql(
    generator,
    monkeypatch,
):

    monkeypatch.setattr(
        "app.services.sql_generator.llm.generate",
        lambda prompt: '{"sql":""}',
    )

    monkeypatch.setattr(
        "app.services.sql_generator.parser.parse_json",
        lambda response: {
            "sql": ""
        },
    )

    with pytest.raises(SQLGenerationError):
        generator.generate("Test")


# ==========================================================
# SQL Executor
# ==========================================================

def test_executor_database_missing(
    executor,
    monkeypatch,
):

    monkeypatch.setattr(
        executor,
        "database_path",
        Path("missing.db"),
    )

    with pytest.raises(SQLExecutionError):
        executor.execute(
            "SELECT * FROM customers"
        )


def test_executor_validation_failure(
    executor,
):

    with pytest.raises(SQLExecutionError):

        executor.execute(
            "DELETE FROM customers"
        )


def test_executor_database_error(
    executor,
    monkeypatch,
):

    monkeypatch.setattr(
        executor,
        "database_path",
        Path(__file__),
    )

    def fake_connect(*args, **kwargs):
        raise sqlite3.Error(
            "Connection failed"
        )

    monkeypatch.setattr(
        "sqlite3.connect",
        fake_connect,
    )

    with pytest.raises(SQLExecutionError):
        executor.execute(
            "SELECT * FROM customers"
        )


# ==========================================================
# Integration Validation
# ==========================================================

@pytest.mark.parametrize(
    "query",
    [
        "SELECT * FROM customers",
        "SELECT * FROM orders",
        "SELECT * FROM products",
        "SELECT * FROM payments",
        "SELECT * FROM reviews",
    ],
)
def test_all_supported_tables(query):

    result = sql_validator.validate(query)

    assert result.valid


@pytest.mark.parametrize(
    "query",
    [
        "DELETE FROM orders",
        "UPDATE payments SET payment_value=0",
        "DROP TABLE products",
        "ALTER TABLE customers ADD age INTEGER",
    ],
)
def test_all_blocked_queries(query):

    result = sql_validator.validate(query)

    assert result.valid is False


# ==========================================================
# Schema Validation
# ==========================================================

def test_schema_contains_correct_product_columns():

    schema_path = Path(__file__).parent.parent / "app" / "database" / "schema.sql"
    text = schema_path.read_text(encoding="utf-8")

    assert "product_name_lenght" in text
    assert "product_description_lenght" in text
    assert "product_name_length" not in text
    assert "product_description_length" not in text


def test_schema_reviews_surrogate_pk():

    schema_path = Path(__file__).parent.parent / "app" / "database" / "schema.sql"
    text = schema_path.read_text(encoding="utf-8")

    assert "review_pk INTEGER PRIMARY KEY AUTOINCREMENT" in text
    assert "review_id TEXT NOT NULL" in text
    assert "review_id TEXT PRIMARY KEY" not in text


def test_validator_allows_order_summary_view():

    result = sql_validator.validate(
        "SELECT * FROM order_summary"
    )

    assert result.valid is True


def test_validator_rejects_nonexistent_tables():

    result = sql_validator.validate(
        "SELECT * FROM nonexistent_table"
    )

    assert result.valid is False
    assert "Unknown table" in result.reason


def test_validator_rejects_nonexistent_tables_in_join():

    result = sql_validator.validate(
        "SELECT * FROM customers JOIN nonexistent_table ON customers.customer_id = nonexistent_table.id"
    )

    assert result.valid is False
    assert "Unknown table" in result.reason


# ==========================================================
# Real Dataset Integration Tests
# ==========================================================

@pytest.fixture
def real_executor():
    """
    Executor backed by the real ecommerce.db.
    Skipped if the database has not been seeded.
    """

    db_path = Path(__file__).parent.parent / "app" / "database" / "ecommerce.db"

    if not db_path.exists():
        pytest.skip("Database not seeded")

    executor = SQLExecutor()
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(executor, "database_path", db_path)
    yield executor
    monkeypatch.undo()


def test_executor_real_customer_count(real_executor):

    result = real_executor.execute("SELECT COUNT(*) AS cnt FROM customers")

    assert result.row_count == 1
    assert result.rows[0]["cnt"] > 0


def test_executor_real_order_count(real_executor):

    result = real_executor.execute("SELECT COUNT(*) AS cnt FROM orders")

    assert result.row_count == 1
    assert result.rows[0]["cnt"] > 0


def test_executor_real_order_items_count(real_executor):

    result = real_executor.execute("SELECT COUNT(*) AS cnt FROM order_items")

    assert result.row_count == 1
    assert result.rows[0]["cnt"] > 0


def test_executor_real_products_count(real_executor):

    result = real_executor.execute("SELECT COUNT(*) AS cnt FROM products")

    assert result.row_count == 1
    assert result.rows[0]["cnt"] > 0


def test_executor_real_payments_count(real_executor):

    result = real_executor.execute("SELECT COUNT(*) AS cnt FROM payments")

    assert result.row_count == 1
    assert result.rows[0]["cnt"] > 0


def test_executor_real_reviews_count(real_executor):

    result = real_executor.execute("SELECT COUNT(*) AS cnt FROM reviews")

    assert result.row_count == 1
    assert result.rows[0]["cnt"] > 0


def test_executor_real_order_summary_row_count(real_executor):

    orders_result = real_executor.execute(
        "SELECT COUNT(*) AS cnt FROM orders"
    )
    summary_result = real_executor.execute(
        "SELECT COUNT(*) AS cnt FROM order_summary"
    )

    assert summary_result.rows[0]["cnt"] >= orders_result.rows[0]["cnt"]


def test_executor_real_null_categories(real_executor):

    result = real_executor.execute(
        "SELECT COUNT(*) AS cnt FROM products WHERE product_category_name IS NULL"
    )

    assert result.rows[0]["cnt"] > 0


def test_executor_real_null_delivery_dates(real_executor):

    result = real_executor.execute(
        "SELECT COUNT(*) AS cnt FROM orders WHERE order_delivered_customer_date IS NULL"
    )

    assert result.rows[0]["cnt"] > 0


def test_executor_real_review_pk_exists(real_executor):

    result = real_executor.execute(
        "SELECT COUNT(*) AS cnt FROM reviews WHERE review_pk IS NOT NULL"
    )

    assert result.rows[0]["cnt"] > 0


def test_executor_real_duplicate_review_ids(real_executor):

    result = real_executor.execute(
        "SELECT review_id, COUNT(*) AS cnt FROM reviews GROUP BY review_id HAVING cnt > 1"
    )

    assert result.row_count > 0


def test_executor_real_foreign_key_check(real_executor):

    connection = sqlite3.connect(real_executor.database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    cursor = connection.execute("PRAGMA foreign_key_check")
    violations = cursor.fetchall()
    connection.close()

    assert len(violations) == 0