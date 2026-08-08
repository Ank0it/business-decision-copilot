# Finance Guidelines

## Purpose
This document provides guidance for financial analysis and transaction-related decisions.

## Transaction Metrics
Use transaction-level records when calculating financial metrics.

For product sales analysis, item-level prices should be aggregated carefully because one order may contain multiple items.

Payment records may contain multiple payment entries for a single order. Therefore, payment totals should be aggregated at the order level before comparing them with order-level metrics.

## Revenue Analysis
When calculating sales revenue from order items, use the recorded item price and clearly state whether freight charges are included.

Do not treat payment value and product price as interchangeable measures.

## Refund Analysis
Refund-related analytics should clearly define the metric being measured. The current dataset does not contain a dedicated refunds table, so refund-related business questions must not invent a refund table or refund columns.

## Data Quality
Financial analysis should account for:
- Multiple items per order
- Multiple payments per order
- Missing values
- Cancelled or unavailable orders
- Differences between transaction-level and order-level metrics

## Business Guidance
When presenting financial recommendations, state the calculation basis and avoid unsupported conclusions from incomplete data.

High-value anomalies, repeated payment issues, and material discrepancies should be escalated.
