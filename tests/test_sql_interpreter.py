"""
Unit tests for SQLInterpreter.

Tests:
- COUNT result = 0
- COUNT result > 0
- SUM result
- single-row result
- multi-row result
- empty SQL result
- LLM synthesis failure / fallback behavior
"""

from __future__ import annotations

import pytest

from app.models.sql import SQLExecutionResult
from app.services.sql_interpreter import SQLInterpretationError, sql_interpreter


# ==========================================================
# Fixtures
# ==========================================================

@pytest.fixture
def interpreter():
    return sql_interpreter


# ==========================================================
# Empty Results
# ==========================================================

def test_empty_result(interpreter):
    result = SQLExecutionResult(
        row_count=0,
        columns=[],
        rows=[],
    )

    answer = interpreter.interpret(
        question="How many orders?",
        sql="SELECT COUNT(*) FROM orders",
        result=result,
    )

    assert answer == "The query returned no results."


# ==========================================================
# Single-Row Single-Column: COUNT = 0
# ==========================================================

def test_count_zero(interpreter):
    result = SQLExecutionResult(
        row_count=1,
        columns=["order_count"],
        rows=[{"order_count": 0}],
    )

    answer = interpreter.interpret(
        question="How many orders were placed last month?",
        sql="SELECT COUNT(*) AS order_count FROM orders",
        result=result,
    )

    assert answer == "No orders found."


# ==========================================================
# Single-Row Single-Column: COUNT > 0
# ==========================================================

def test_count_positive(interpreter):
    result = SQLExecutionResult(
        row_count=1,
        columns=["order_count"],
        rows=[{"order_count": 125}],
    )

    answer = interpreter.interpret(
        question="How many orders were placed last month?",
        sql="SELECT COUNT(*) AS order_count FROM orders",
        result=result,
    )

    assert answer == "125 orders."


# ==========================================================
# Single-Row Single-Column: SUM
# ==========================================================

def test_sum_result(interpreter):
    result = SQLExecutionResult(
        row_count=1,
        columns=["total_revenue"],
        rows=[{"total_revenue": 125000}],
    )

    answer = interpreter.interpret(
        question="What is the total revenue?",
        sql="SELECT SUM(payment_value) AS total_revenue FROM payments",
        result=result,
    )

    assert answer == "Total revenue is 125,000."


# ==========================================================
# Single-Row Single-Column: AVG
# ==========================================================

def test_avg_result(interpreter):
    result = SQLExecutionResult(
        row_count=1,
        columns=["average_order_value"],
        rows=[{"average_order_value": 150.50}],
    )

    answer = interpreter.interpret(
        question="What is the average order value?",
        sql="SELECT AVG(oi.price) AS average_order_value FROM order_items oi",
        result=result,
    )

    assert answer == "Average order value is 150.50."


# ==========================================================
# Single-Row Single-Column: MIN
# ==========================================================

def test_min_result(interpreter):
    result = SQLExecutionResult(
        row_count=1,
        columns=["lowest_price"],
        rows=[{"lowest_price": 10}],
    )

    answer = interpreter.interpret(
        question="What is the lowest product price?",
        sql="SELECT MIN(price) AS lowest_price FROM products",
        result=result,
    )

    assert answer == "Lowest price is 10."


# ==========================================================
# Single-Row Single-Column: MAX
# ==========================================================

def test_max_result(interpreter):
    result = SQLExecutionResult(
        row_count=1,
        columns=["highest_payment"],
        rows=[{"highest_payment": 5000}],
    )

    answer = interpreter.interpret(
        question="What is the highest payment value?",
        sql="SELECT MAX(payment_value) AS highest_payment FROM payments",
        result=result,
    )

    assert answer == "Highest payment is 5,000."


# ==========================================================
# Single-Row Multi-Column: LLM Synthesis
# ==========================================================

def test_single_row_multi_column(interpreter, monkeypatch):
    result = SQLExecutionResult(
        row_count=1,
        columns=["product_category_name", "revenue"],
        rows=[{"product_category_name": "Electronics", "revenue": 250000}],
    )

    monkeypatch.setattr(
        "app.services.sql_interpreter.llm.generate",
        lambda prompt: "Electronics generated the highest revenue at 250,000.",
    )

    answer = interpreter.interpret(
        question="Which product category generated the most revenue?",
        sql="SELECT p.product_category_name, SUM(oi.price) AS revenue FROM order_items oi JOIN products p ON oi.product_id = p.product_id GROUP BY p.product_category_name ORDER BY revenue DESC LIMIT 1",
        result=result,
    )

    assert answer == "Electronics generated the highest revenue at 250,000."


# ==========================================================
# Multi-Row Result: LLM Synthesis
# ==========================================================

def test_multi_row_result(interpreter, monkeypatch):
    result = SQLExecutionResult(
        row_count=3,
        columns=["customer_state", "customer_count"],
        rows=[
            {"customer_state": "SP", "customer_count": 5000},
            {"customer_state": "RJ", "customer_count": 3000},
            {"customer_state": "MG", "customer_count": 2000},
        ],
    )

    monkeypatch.setattr(
        "app.services.sql_interpreter.llm.generate",
        lambda prompt: "SP has the most customers with 5,000, followed by RJ with 3,000 and MG with 2,000.",
    )

    answer = interpreter.interpret(
        question="How many customers are there in each state?",
        sql="SELECT customer_state, COUNT(*) AS customer_count FROM customers GROUP BY customer_state ORDER BY customer_count DESC",
        result=result,
    )

    assert answer == "SP has the most customers with 5,000, followed by RJ with 3,000 and MG with 2,000."


# ==========================================================
# LLM Failure: Fallback Behavior
# ==========================================================

def test_llm_failure_fallback(interpreter, monkeypatch):
    result = SQLExecutionResult(
        row_count=2,
        columns=["category", "revenue"],
        rows=[
            {"category": "Electronics", "revenue": 250000},
            {"category": "Clothing", "revenue": 150000},
        ],
    )

    monkeypatch.setattr(
        "app.services.sql_interpreter.llm.generate",
        lambda prompt: (_ for _ in ()).throw(RuntimeError("API down")),
    )

    answer = interpreter.interpret(
        question="Which categories have the highest revenue?",
        sql="SELECT category, SUM(revenue) AS revenue FROM sales GROUP BY category ORDER BY revenue DESC LIMIT 2",
        result=result,
    )

    assert "2 rows" in answer


# ==========================================================
# LLM Empty Response: Fallback Behavior
# ==========================================================

def test_llm_empty_response_fallback(interpreter, monkeypatch):
    result = SQLExecutionResult(
        row_count=2,
        columns=["category", "revenue"],
        rows=[
            {"category": "Electronics", "revenue": 250000},
            {"category": "Clothing", "revenue": 150000},
        ],
    )

    monkeypatch.setattr(
        "app.services.sql_interpreter.llm.generate",
        lambda prompt: "",
    )

    answer = interpreter.interpret(
        question="Which categories have the highest revenue?",
        sql="SELECT category, SUM(revenue) AS revenue FROM sales GROUP BY category ORDER BY revenue DESC LIMIT 2",
        result=result,
    )

    assert "could not be generated" in answer


# ==========================================================
# Single-Row Single-Column: NULL Value
# ==========================================================

def test_null_value(interpreter):
    result = SQLExecutionResult(
        row_count=1,
        columns=["total_revenue"],
        rows=[{"total_revenue": None}],
    )

    answer = interpreter.interpret(
        question="What is the total revenue?",
        sql="SELECT SUM(payment_value) AS total_revenue FROM payments",
        result=result,
    )

    assert answer == "The query returned no results."


# ==========================================================
# Single-Row Single-Column: Generic Column Name
# ==========================================================

def test_generic_column_name(interpreter):
    result = SQLExecutionResult(
        row_count=1,
        columns=["some_metric"],
        rows=[{"some_metric": 42}],
    )

    answer = interpreter.interpret(
        question="What is the value?",
        sql="SELECT some_metric FROM table",
        result=result,
    )

    assert answer == "42 some metric."


# ==========================================================
# Single-Row Single-Column: Float Value
# ==========================================================

def test_float_value(interpreter):
    result = SQLExecutionResult(
        row_count=1,
        columns=["average_score"],
        rows=[{"average_score": 4.5}],
    )

    answer = interpreter.interpret(
        question="What is the average score?",
        sql="SELECT AVG(score) AS average_score FROM reviews",
        result=result,
    )

    assert answer == "Average score is 4.50."


# ==========================================================
# Single-Row Single-Column: Zero with Custom Column
# ==========================================================

def test_zero_custom_column(interpreter):
    result = SQLExecutionResult(
        row_count=1,
        columns=["refund_count"],
        rows=[{"refund_count": 0}],
    )

    answer = interpreter.interpret(
        question="How many refunds were processed?",
        sql="SELECT COUNT(*) AS refund_count FROM refunds",
        result=result,
    )

    assert answer == "No refunds found."
