# Business Decision Copilot

AI-powered assistant that combines **Retrieval-Augmented Generation (RAG)** and **Text-to-SQL** to answer business questions using real company documents and an Olist e-commerce database.

## What It Does

The Business Decision Copilot accepts a natural-language business question and routes it through one of four execution paths:

- **RAG** — answers questions grounded in business policy and operational documents
- **Text2SQL** — answers quantitative business analytics questions using a real Olist Brazilian E-Commerce dataset
- **Hybrid** — combines policy evidence from RAG with quantitative evidence from SQL to produce a business recommendation
- **Refusal** — safely refuses unsupported, unsafe, ambiguous, or out-of-scope questions

## Problem Statement

Business users need to ask questions in natural language and receive answers backed by both company policy documents and live operational data. Traditional approaches force users to either search documents manually or write SQL queries. This project demonstrates a production-style architecture that routes questions automatically, validates generated SQL for safety, and returns structured, cited responses.

## Key Capabilities

- Automatic query routing (RAG / SQL / Hybrid / Refusal)
- Read-only SQL generation with strict safety validation
- Document retrieval with citation tracking
- Hybrid reasoning combining policy and data
- Structured JSON responses via Pydantic models
- FastAPI REST interface with debug endpoints
- Real Olist dataset seeded in SQLite
- ChromaDB vector store for semantic document retrieval

## Architecture

```
User Question
    │
    ▼
QueryRouter (Gemini LLM)
    │
    ▼
BusinessService
    │
    ├── RAG ──► ChromaDB Retrieval ──► Gemini ──► JSON Parser ──► BusinessResponse
    │
    ├── SQL ──► Gemini ──► SQLGeneration/SQLRefusal
    │             │
    │             ▼
    │         SQLValidator (SELECT-only, schema-aware)
    │             │
    │             ▼
    │         SQLExecutor (SQLite)
    │             │
    │             ▼
    │         BusinessResponse
    │
    ├── HYBRID ──► RAG Retrieval + SQL Generation/Execution
    │                │
    │                ▼
    │            Gemini (policy + data synthesis)
    │                │
    │                ▼
    │            BusinessResponse with BusinessInsight
    │
    └── REFUSAL ──► BusinessResponse
```

## End-to-End Request Flow

1. Client sends `POST /ask-business` with `{"question": "..."}`
2. FastAPI validates the request body
3. `BusinessService.ask()` receives the question
4. `QueryRouter.classify()` sends the question to Gemini with the router prompt
5. Gemini returns a JSON routing decision (`route` + `reason`)
6. `BusinessService` dispatches to the appropriate pipeline
7. The pipeline executes (RAG retrieval, SQL generation + validation + execution, or Hybrid)
8. The result is normalized into a `BusinessResponse` Pydantic model
9. FastAPI returns the structured JSON response

## RAG Pipeline

1. **Chunking** — Markdown business documents are split into deterministic chunks using a sliding-window chunker with configurable overlap
2. **Embedding** — Each chunk is embedded using `sentence-transformers/all-MiniLM-L6-v2`
3. **Storage** — Embeddings and metadata are stored in a persistent ChromaDB collection under `data/chroma/`
4. **Retrieval** — User questions are embedded and matched against the vector store; top-K chunks are returned with similarity scores
5. **Generation** — Retrieved chunks are injected into the RAG prompt; Gemini generates a grounded answer with citations
6. **Parsing** — The LLM response is parsed as JSON and validated against the expected schema

## Text-to-SQL Pipeline

1. **Generation** — Gemini receives the SQL prompt with the actual database schema and generates a SQLite SELECT query
2. **Validation** — The generated SQL is validated before execution:
   - Only SELECT statements are allowed
   - Destructive keywords are blocked (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, etc.)
   - Multi-statement SQL is rejected
   - UNION / INTERSECT / EXCEPT are blocked
   - Only tables present in `schema.sql` are permitted
   - LOAD_EXTENSION is blocked
3. **Execution** — Validated SQL is executed against the SQLite database
4. **Normalization** — Results are packaged into a `BusinessResponse` with columns, rows, and row count

## Hybrid Pipeline

1. Retrieves policy evidence via RAG
2. Generates and executes SQL via the Text-to-SQL pipeline
3. Combines both sources in a Gemini prompt
4. Returns a structured recommendation with:
   - `policy_summary` — what the documents state
   - `data_summary` — what the SQL results show
   - `recommendation` — grounded business recommendation
   - `confidence_notes` — explanation of trustworthiness

## Refusal / Safety Pipeline

Unsupported or unsafe questions are refused without executing RAG or SQL. The router classifies these questions directly as `refusal` and returns a `BusinessResponse` with:
- `query_type: "refusal"`
- `refusal_reason` explaining why the request cannot be processed
- `confidence: "low"`

## Database Schema

The SQLite database is built from the **real Olist Brazilian E-Commerce Public Dataset**.

### Tables

| Table | Description | Key Columns |
|-------|-------------|-------------|
| `customers` | Customer master data | `customer_id` (PK), `customer_unique_id`, `customer_city`, `customer_state` |
| `sellers` | Seller master data | `seller_id` (PK), `seller_city`, `seller_state` |
| `products` | Product catalog | `product_id` (PK), `product_category_name`, `product_name_lenght`, `product_description_lenght` |
| `orders` | Order headers | `order_id` (PK), `customer_id` (FK), `order_status`, timestamps |
| `order_items` | Line items per order | Composite PK (`order_id`, `order_item_id`), FKs to `orders`, `products`, `sellers` |
| `payments` | Payment transactions | Composite PK (`order_id`, `payment_sequential`), FK to `orders` |
| `reviews` | Customer reviews | `review_pk` (surrogate PK), `review_id` (original Olist identifier), `order_id` (FK) |
| `product_categories` | Category translation | `category_name` (PK), `category_name_english` |

### View

| View | Description |
|------|-------------|
| `order_summary` | Denormalized join across `orders`, `customers`, `order_items`, `products`, `payments`, `reviews` |

**Note:** The `reviews` table uses a surrogate primary key (`review_pk`) because the source Olist dataset contains duplicate `review_id` values. All 99,224 source records are preserved.

## SQL Safety Controls

- **SELECT-only:** Only `SELECT` statements are permitted
- **Destructive keyword blocking:** INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, REPLACE, MERGE, EXEC, EXECUTE, ATTACH, DETACH, PRAGMA, VACUUM, GRANT, REVOKE, LOAD_EXTENSION
- **Clause blocking:** UNION, INTERSECT, EXCEPT
- **Multi-statement blocking:** Semicolons mid-query are rejected
- **Schema-aware table validation:** Only tables defined in `schema.sql` are allowed
- **Pre-execution validation:** SQL is validated before any execution occurs

## LLM Integration

- **Provider:** Google Gemini
- **Model:** `gemini-flash-latest`
- **Configuration:** Temperature and max output tokens are configurable via environment variables
- **Lazy initialization:** The Gemini client is created on first use
- **Error handling:** Empty responses, invalid JSON, API errors, and quota exhaustion are surfaced with clear error messages
- **Prompt/JSON/Pydantic contract:** Every prompt requests JSON that matches the corresponding Pydantic model; the parser validates required fields before services construct response objects

## RAG Document Ingestion

Eight business-policy Markdown documents are ingested into ChromaDB:

- `refund_policy.md`
- `pricing_policy.md`
- `subscription_terms.md`
- `shipping_returns.md`
- `finance_guidelines.md`
- `support_sop.md`
- `warranty_policy.md`
- `escalation_matrix.md`

**Ingestion command:**
```bash
python -m app.retrieval.ingest
```

The operation is idempotent: running it multiple times does not create duplicate chunks.

## Chroma Vector Store

- **Collection name:** `business_documents`
- **Persistence:** `data/chroma/`
- **Chunk count:** 47
- **Metadata:** Each chunk stores `source`, `chunk_id`, and embedding vector
- **Retrieval:** Top-K semantic search with configurable distance threshold

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/health` | Extended health with vector store status |
| `POST` | `/ask-business` | Main endpoint — accepts a business question and returns a routed response |
| `GET` | `/debug/retrieval` | Returns retrieved document chunks without invoking the LLM |
| `GET` | `/debug/sql` | Returns generated SQL and validation result without executing it |

### Example: `POST /ask-business`

**Request:**
```json
{
  "question": "What is the refund policy?"
}
```

**Response:**
```json
{
  "query_type": "rag",
  "answer": "Under the refund policy, customers may request a refund if the order was cancelled before fulfillment...",
  "citations": [
    {
      "source": "refund_policy.md",
      "chunk_id": "refund_policy.md_0000",
      "score": null
    }
  ],
  "generated_sql": null,
  "sql_validation": null,
  "sql_result": null,
  "business_insight": null,
  "confidence": "medium",
  "confidence_notes": null,
  "refusal_reason": null
}
```

## Project Structure

```
business-decision-copilot/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── core/
│   │   ├── config.py
│   │   ├── constants.py
│   │   ├── logging.py
│   │   └── prompts.py
│   ├── database/
│   │   ├── connection.py
│   │   ├── ecommerce.db
│   │   ├── schema.sql
│   │   └── seed.py
│   ├── main.py
│   ├── models/
│   │   ├── request.py
│   │   ├── response.py
│   │   └── sql.py
│   ├── retrieval/
│   │   ├── chunker.py
│   │   ├── embeddings.py
│   │   ├── ingest.py
│   │   └── vector_store.py
│   ├── services/
│   │   ├── business_service.py
│   │   ├── confidence.py
│   │   ├── hybrid.py
│   │   ├── rag.py
│   │   ├── refusal.py
│   │   ├── router.py
│   │   ├── sql_executor.py
│   │   ├── sql_generator.py
│   │   └── sql_validator.py
│   └── utils/
│       ├── helpers.py
│       ├── llm.py
│       └── parser.py
├── benchmark/
│   ├── evaluate.py
│   ├── hybrid.json
│   ├── rag.json
│   ├── refusal.json
│   └── sql.json
├── data/
│   ├── chroma/
│   ├── dataset/
│   │   ├── olist_customers_dataset.csv
│   │   ├── olist_orders_dataset.csv
│   │   ├── olist_order_items_dataset.csv
│   │   ├── olist_products_dataset.csv
│   │   ├── olist_order_payments_dataset.csv
│   │   ├── olist_order_reviews_dataset.csv
│   │   ├── olist_sellers_dataset.csv
│   │   └── product_category_name_translation.csv
│   └── documents/
│       ├── escalation_matrix.md
│       ├── finance_guidelines.md
│       ├── pricing_policy.md
│       ├── refund_policy.md
│       ├── shipping_returns.md
│       ├── subscription_terms.md
│       ├── support_sop.md
│       └── warranty_policy.md
├── prompts/
│   ├── hybrid.txt
│   ├── rag.txt
│   ├── router.txt
│   └── sql.txt
├── tests/
│   ├── test_api.py
│   ├── test_business_service.py
│   ├── test_hybrid.py
│   ├── test_rag.py
│   ├── test_router.py
│   └── test_sql.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Installation / Setup

### Prerequisites

- Python 3.11+
- Git
- Virtual environment (recommended)

### Steps

```bash
# Clone the repository
git clone https://github.com/Ank0it/business-decision-copilot
cd business-decision-copilot

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | (empty) |
| `GEMINI_MODEL` | Gemini model identifier | `gemini-flash-latest` |
| `TEMPERATURE` | LLM generation temperature | `0.1` |
| `MAX_OUTPUT_TOKENS` | Maximum tokens per LLM response | `2048` |

**Important:** Never commit `.env` to version control. It is gitignored.

## Database Seeding

The application uses a SQLite database seeded from the real Olist Brazilian E-Commerce dataset.

```bash
python -m app.database.seed
```

This command:
1. Drops existing tables and views
2. Executes `schema.sql`
3. Loads all 8 CSV files from `data/dataset/`
4. Enables foreign-key constraints
5. Verifies referential integrity
6. Reports row counts for each table

## RAG Ingestion

Ingest the 8 business-policy Markdown documents into ChromaDB:

```bash
python -m app.retrieval.ingest
```

This command:
1. Discovers all `.md` files in `data/documents/`
2. Chunks them into 47 deterministic chunks
3. Generates embeddings using `sentence-transformers/all-MiniLM-L6-v2`
4. Stores them in a persistent ChromaDB collection at `data/chroma/`

## Running the API

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

### Interactive Docs

FastAPI automatic documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Running Tests

```bash
python -m pytest tests/ -v
```

Current test status: **97 passed, 0 failed.**

## Benchmark Commands

The benchmark suite evaluates RAG, SQL, Hybrid, and Refusal pipelines against labeled test sets.

```bash
python -m benchmark.evaluate
```

Benchmark result files are stored locally and are not committed to version control.

**Note:** Live benchmark results require an active Gemini API quota. Current status: pending quota reset.

## Current Verification Results

| Component | Status |
|-----------|--------|
| Automated tests | 97 passed |
| Database seeded | Yes — 8 tables + 1 view |
| Foreign-key integrity | Pass — 0 violations |
| RAG chunks | 47 chunks from 8 documents |
| Chroma retrieval | Verified — relevant results returned |
| SQL validator | Schema-aware, dynamic table detection |
| API endpoints | All 5 endpoints responding |
| Live LLM integration | Previously verified; currently blocked by Gemini free-tier quota exhaustion |

## Known Limitations

- **Gemini free-tier quota:** The Google Gemini free tier allows 20 requests per day. Live LLM-dependent endpoints may return `429 RESOURCE_EXHAUSTED` during heavy testing. Wait for quota reset or upgrade to a paid tier.
- **Benchmark scores:** Live benchmark results have not yet been generated due to quota limits. The benchmark infrastructure is in place and ready to run.
- **RAG scope:** RAG answers are limited to the 8 ingested business-policy documents. Questions outside this corpus are refused.
- **SQL scope:** Text-to-SQL is limited to the Olist schema defined in `schema.sql`. Questions requiring data not present in the dataset are refused.
- **Review duplicates:** The source Olist dataset contains 814 duplicate `review_id` values. The schema uses a surrogate `review_pk` to preserve all records.

## Future Improvements

- Add retry/backoff logic for transient Gemini API errors (503/429)
- Expand business-policy document corpus
- Add user authentication and rate limiting
- Add request logging and observability
- Support for additional LLM providers
- Query result caching for repeated questions
- Advanced SQL features (CTEs, window functions) if required by benchmark

## License

This project is intended for educational and portfolio demonstration purposes.
