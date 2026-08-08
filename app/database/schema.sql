-- ============================================================
-- Business Decision Copilot
-- SQLite Database Schema
--
-- Dataset Source:
-- Brazilian E-Commerce Public Dataset by Olist
--
-- This schema exposes a business-friendly relational model
-- derived from the original Olist dataset.
-- ============================================================

PRAGMA foreign_keys = ON;

-- ============================================================
-- CUSTOMERS
-- ============================================================

CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    customer_unique_id TEXT NOT NULL,
    customer_zip_code_prefix INTEGER,
    customer_city TEXT,
    customer_state TEXT
);

CREATE INDEX idx_customers_state
ON customers(customer_state);

CREATE INDEX idx_customers_city
ON customers(customer_city);

-- ============================================================
-- SELLERS
-- ============================================================

CREATE TABLE sellers (
    seller_id TEXT PRIMARY KEY,
    seller_zip_code_prefix INTEGER,
    seller_city TEXT,
    seller_state TEXT
);

CREATE INDEX idx_sellers_state
ON sellers(seller_state);

-- ============================================================
-- PRODUCTS
-- ============================================================

CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    product_category_name TEXT,
    product_name_lenght INTEGER,
    product_description_lenght INTEGER,
    product_photos_qty INTEGER,
    product_weight_g REAL,
    product_length_cm REAL,
    product_height_cm REAL,
    product_width_cm REAL
);

CREATE INDEX idx_products_category
ON products(product_category_name);

-- ============================================================
-- ORDERS
-- ============================================================

CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,

    customer_id TEXT NOT NULL,

    order_status TEXT,

    order_purchase_timestamp TEXT,

    order_approved_at TEXT,

    order_delivered_carrier_date TEXT,

    order_delivered_customer_date TEXT,

    order_estimated_delivery_date TEXT,

    FOREIGN KEY(customer_id)
        REFERENCES customers(customer_id)
);

CREATE INDEX idx_orders_customer
ON orders(customer_id);

CREATE INDEX idx_orders_status
ON orders(order_status);

CREATE INDEX idx_orders_purchase
ON orders(order_purchase_timestamp);

-- ============================================================
-- ORDER ITEMS
-- ============================================================

CREATE TABLE order_items (

    order_id TEXT,

    order_item_id INTEGER,

    product_id TEXT,

    seller_id TEXT,

    shipping_limit_date TEXT,

    price REAL,

    freight_value REAL,

    PRIMARY KEY(order_id, order_item_id),

    FOREIGN KEY(order_id)
        REFERENCES orders(order_id),

    FOREIGN KEY(product_id)
        REFERENCES products(product_id),

    FOREIGN KEY(seller_id)
        REFERENCES sellers(seller_id)
);

CREATE INDEX idx_order_items_product
ON order_items(product_id);

CREATE INDEX idx_order_items_seller
ON order_items(seller_id);

-- ============================================================
-- PAYMENTS
-- ============================================================

CREATE TABLE payments (

    order_id TEXT,

    payment_sequential INTEGER,

    payment_type TEXT,

    payment_installments INTEGER,

    payment_value REAL,

    PRIMARY KEY(order_id, payment_sequential),

    FOREIGN KEY(order_id)
        REFERENCES orders(order_id)
);

CREATE INDEX idx_payments_type
ON payments(payment_type);

-- ============================================================
-- REVIEWS
-- ============================================================
--
-- NOTE: The source Olist dataset contains duplicate review_id
-- values (814 duplicates observed). To preserve every source
-- record without discarding or deduplicating data, this table
-- uses a surrogate primary key (review_pk). The review_id
-- column is retained as the original Olist identifier.

CREATE TABLE reviews (

    review_pk INTEGER PRIMARY KEY AUTOINCREMENT,

    review_id TEXT NOT NULL,

    order_id TEXT NOT NULL,

    review_score INTEGER,

    review_comment_title TEXT,

    review_comment_message TEXT,

    review_creation_date TEXT,

    review_answer_timestamp TEXT,

    FOREIGN KEY(order_id)
        REFERENCES orders(order_id)
);

CREATE INDEX idx_reviews_score
ON reviews(review_score);

-- ============================================================
-- PRODUCT CATEGORY TRANSLATION
-- ============================================================

CREATE TABLE product_categories (

    category_name TEXT PRIMARY KEY,

    category_name_english TEXT
);

-- ============================================================
-- BUSINESS VIEW
-- ============================================================

CREATE VIEW order_summary AS

SELECT

    o.order_id,

    o.order_status,

    o.order_purchase_timestamp,

    c.customer_city,

    c.customer_state,

    oi.product_id,

    p.product_category_name,

    oi.price,

    oi.freight_value,

    pay.payment_type,

    pay.payment_value,

    r.review_score

FROM orders o

JOIN customers c
ON o.customer_id = c.customer_id

JOIN order_items oi
ON o.order_id = oi.order_id

JOIN products p
ON oi.product_id = p.product_id

LEFT JOIN payments pay
ON o.order_id = pay.order_id

LEFT JOIN reviews r
ON o.order_id = r.order_id;

-- ============================================================
-- END OF SCHEMA
-- ============================================================