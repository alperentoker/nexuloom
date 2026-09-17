<p align="center">
  <img src="frontend/img/banner.png" alt="Nexuloom Platform Banner" width="100%" style="border-radius: 8px;">
</p>

<p align="center">
  <img src="frontend/img/logo.png" alt="Nexuloom Brandmark" width="72" height="72" style="border-radius: 8px;">
</p>

# Nexuloom | Universal Data Intelligence & Reporting Platform

**Nexuloom** is a production-grade, modular Data Intelligence and Reporting platform built in Python for Linux environments. It connects to heterogeneous databases (SQLite, PostgreSQL, MySQL, MSSQL), discovers schemas and relationships, profiles data, evaluates quality scores, computes deterministic KPIs and time-series trends, detects statistical anomalies, executes business rules, discovers root-cause insights with strict attribution, and compiles executive-ready reports in **PDF, Excel, HTML, CSV, and JSON**, accompanied by an interactive modern bilingual web dashboard (Turkish/English), CLI tool (`nexuloom` / `udi`), and optional local LLM integration.

---

## 1. System Architecture & End-to-End Pipeline

The platform is designed around a strictly deterministic 12-stage intelligence pipeline:

```
DATABASE (SQLite / PostgreSQL / MySQL / MSSQL)
   │
   ▼
1. Connection Manager (Encrypted Credentials, Secret Masking, Engine Pooling)
   │
   ▼
2. Schema Discovery (Catalogs, Tables, Columns, Types, PKs, FKs, Row Counts)
   │
   ▼
3. Relationship Discovery (Explicit FKs & Heuristic ER Graph Inference)
   │
   ▼
4. Data Profiling Engine (Quantiles, Skewness, Lengths, Temporal Frequencies)
   │
   ▼
5. Data Quality Engine (Null, Duplicate, Negative, Outlier, Date Checks -> 0-100 Score)
   │
   ▼
6. Metric & KPI Engine (Formulas, MoM / YoY Slicing, Actual vs Target)
   │
   ▼
7. Trend Analysis (Linear Regression Slope, CAGR, Moving Averages, Sudden Shifts)
   │
   ▼
8. Anomaly Detection (Z-score, IQR Fences, Rolling Statistics, Isolation Forest)
   │
   ▼
9. Business Rule Engine (User-Defined Conditions, CRUD, Audit Log)
   │
   ▼
10. Insight & Root-Cause Engine (Variance Attribution %, Causality-Safe Attribution)
   │
   ▼
11. Report Builder (Executive Sections, Lineage Provenance)
   │
   ▼
12. Multi-Format Output (PDF, Multi-Sheet Excel, Responsive HTML, CSV, JSON)
   │
   ▼
Optional Local LLM (Ollama / Offline Deterministic Fallback)
```

### Deterministic Analytics vs. LLM Separation
All arithmetic calculations, statistical metrics, aggregations, anomaly detection thresholds, and data quality scores are computed deterministically using standard libraries (SQLAlchemy, Pandas, NumPy, SciPy, Scikit-Learn). An optional local LLM (such as Ollama) is used solely for natural language summarization and semantic query formulation. When the LLM is offline or disabled, the platform executes with 100% deterministic template fallback.

---

## 2. Directory Structure

```
nexuloom/
├── app/
│   ├── api/                     # FastAPI REST Endpoints
│   │   ├── routes_databases.py  # Connection management & test
│   │   ├── routes_discovery.py  # Schema & ER relationship endpoints
│   │   ├── routes_profiling.py  # Column & table profiling
│   │   ├── routes_quality.py    # Data quality scoring & violation checks
│   │   ├── routes_kpi.py        # KPI calculation & formula management
│   │   ├── routes_analytics.py  # Trend analysis & seasonality
│   │   ├── routes_anomaly.py    # Anomaly detection (Z-score, IQR, Forest)
│   │   ├── routes_rules.py      # Business rule engine CRUD & execution
│   │   ├── routes_insights.py   # Root-cause analysis & insight discovery
│   │   ├── routes_reports.py    # Multi-format report generation & download
│   │   ├── routes_query.py      # Safe read-only NL & SQL analysis engine
│   │   └── routes_audit.py      # Audit logs & data lineage inspector
│   ├── core/                    # Core Infrastructure
│   │   ├── config.py            # Environment, paths, security keys, limits
│   │   ├── security.py          # Fernet secret encryption & credential masking
│   │   ├── audit.py             # SQLite-backed audit logger
│   │   ├── cache.py             # Memory & SQLite cache with TTL & invalidation
│   │   └── lineage.py           # Data lineage tracking graph
│   ├── database/                # Database Abstraction
│   │   ├── connection.py        # Universal SQLAlchemy connection manager
│   │   ├── registry.py          # Connection metadata registry (system.db)
│   │   └── safety.py            # Strict read-only SQL validator (AST/Regex)
│   ├── discovery/               # Discovery Engines
│   │   ├── schema.py            # Schema inspection (tables, columns, types, nulls)
│   │   └── relationship.py      # Foreign key & heuristic ER relationship extraction
│   ├── profiling/
│   │   └── profiler.py          # Numeric, string, date profiling engine
│   ├── quality/
│   │   ├── engine.py            # Quality score (0-100) & rule execution
│   │   └── rules.py             # Null, duplicate, negative, outlier, date rules
│   ├── metrics/
│   │   └── kpi_engine.py        # Custom KPI formulas, period comparisons (MoM, YoY)
│   ├── analytics/
│   │   └── trends.py            # Time series trends, CAGR, regression slope
│   ├── anomaly/
│   │   └── detector.py          # Z-Score, IQR, Rolling statistics, Isolation Forest
│   ├── rules/
│   │   └── rule_engine.py       # Business rule evaluator & violation tracker
│   ├── insights/
│   │   ├── insight_engine.py    # Correlative attribution & contribution % engine
│   │   └── root_cause.py        # Hierarchical analytical drill-down tree
│   ├── reports/
│   │   ├── builder.py           # Modular report orchestrator
│   │   ├── html_exporter.py     # Responsive, printable HTML reports
│   │   ├── pdf_exporter.py      # Corporate PDF generation via ReportLab
│   │   ├── excel_exporter.py    # 6-sheet styled Excel generation (openpyxl)
│   │   └── data_exporter.py     # CSV and JSON exports
│   ├── llm/
│   │   ├── client.py            # Local LLM client (Ollama / OpenAI compatible)
│   │   └── fallback.py          # Deterministic rule-based template generator
│   ├── scheduler/
│   │   └── runner.py            # Automated periodic report runner
│   └── main.py                  # FastAPI application entrypoint
│
├── frontend/                    # Web Dashboard
│   ├── index.html               # Single-page application interface
│   ├── css/styles.css           # Modern dark glassmorphism design system
│   └── js/
│       ├── api.js               # API communication client
│       ├── charts.js            # Chart.js renderers (Line, Bar, Donut, Scatter)
│       └── app.js               # Tab views, filters, and interactivity
│
├── scripts/
│   └── seed_demo_db.py          # Deterministic enterprise demo generator (11 tables)
├── tests/                       # Automated Pytest Suite (29 unit & integration tests)
├── nexuloom.py                  # Primary Command Line Interface
├── udi.py                       # Backward-compatible CLI alias
├── requirements.txt             # Dependencies
├── pyproject.toml               # Package configuration
└── .env                         # Environment settings
```

---

## 3. Quick Start & Installation

### Method 1: Automatic Setup (Recommended)

After cloning the repository, you can set up the virtual environment, install dependencies, seed the enterprise demo database, and run verification tests with a single command:

```bash
git clone https://github.com/alperentoker/nexuloom.git
cd nexuloom
chmod +x setup.sh
./setup.sh
```

### Method 2: Manual Setup

```bash
# 1. Clone repository
git clone https://github.com/alperentoker/nexuloom.git
cd nexuloom

# 2. Create and activate virtual environment (Python 3.11+)
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Generate demo enterprise database (11 relational tables, 105,000+ records)
python scripts/seed_demo_db.py

# 5. Run automated test suite
pytest -v tests/

# 6. Start the web dashboard and API server
python main.py
```

Open your browser at **`http://localhost:8000`** to view the interactive dashboard.

---

## 4. CLI Usage (`nexuloom` / `udi`)

The platform includes a CLI tool (`nexuloom` or `udi`):

```bash
# Platform health & directories
nexuloom health

# List registered database connections
udi databases

# Inspect schema tables and columns
udi inspect --database demo_enterprise
udi inspect --database demo_enterprise --table orders

# Run deep statistical profiling
udi profile --database demo_enterprise --table orders --samples 10000

# Evaluate data quality score and rule violations
udi quality --database demo_enterprise
udi quality --database demo_enterprise --table customers

# List and evaluate business KPIs
udi kpi list --database demo_enterprise
udi kpi evaluate --name "Total Revenue"
udi kpi evaluate --name "Average Order Value"

# Detect statistical anomalies (Z-Score, IQR, Isolation Forest)
udi anomalies --database demo_enterprise --table production --metric operating_temp_c

# Run user-defined business rules
udi rules list --database demo_enterprise
udi rules run --database demo_enterprise

# Natural language and safe read-only SQL queries
udi query --database demo_enterprise --nl "top 5 products by price"
udi query --database demo_enterprise --sql "SELECT id, region, total_amount FROM orders LIMIT 10"

# Generate Executive Reports (PDF, Excel, HTML, CSV, JSON)
udi report monthly --database demo_enterprise --format ALL

# Launch the Web Dashboard
udi dashboard --port 8000
```

---

## 5. Demonstration Enterprise Database

The deterministic synthetic generator (`scripts/seed_demo_db.py`) creates `data/demo_enterprise.db` with 11 relational tables:

1. **`companies`**: Enterprise parent entities, industries, currencies.
2. **`employees`**: Staff records across 6 departments with salaries and performance ratings.
3. **`customers`**: Customer database with regional tiers and 3.5% intentional NULL emails for data quality auditing.
4. **`products`**: Product catalog across 6 categories with intentional extreme price outlier (SKU-00142: ₺48,500.00).
5. **`orders`**: 25,000 orders across 2025-2026 exhibiting seasonal trends, with an intentional Region B sales decline in August-September 2026.
6. **`order_items`**: 62,000+ line items with unit prices and subtotals.
7. **`machines`**: Factory equipment and production lines.
8. **`production`**: 15,000 manufacturing batches with defect rates and operating temperatures (Machine M-102 exhibits extreme temperature spikes up to 96.5°C).
9. **`maintenance`**: 400 service and emergency maintenance logs with downtime hours.
10. **`inventory`**: Warehouse stock levels with 7 items deliberately below safety minimum stock to trigger business rule alerts.
11. **`expenses`**: Operating expenses across R&D, IT, Marketing, Utilities, and Logistics.

---

## 6. Security & Query Safety Engine

- **Strict Read-Only Execution**: The `SQLSafetyValidator` parses queries via AST and regex to disallow destructive SQL keywords (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `REPLACE`, `GRANT`, `EXEC`).
- **Limit Enforcement**: Unbounded queries automatically have a safe `LIMIT` appended to protect laptop memory.
- **Secret Encryption**: Connection passwords are encrypted at rest using Fernet symmetric encryption and never stored in plain text.
- **Masking**: Passwords and connection secrets are masked (`****`) in UI endpoints, CLI outputs, and audit logs.
- **Audit Logging**: Every connection attempt, query execution, rule run, and report generation is recorded in SQLite table `audit_logs`.

---

## 7. Strategic Expansion Roadmap

```
Phase 1 → Database + Profiling (Complete)
          Universal SQLAlchemy abstraction, SQLite/Postgres/MySQL/MSSQL, schema discovery, deep profiling.

Phase 2 → KPI + Analytics (Complete)
          Custom formulas, period-over-period slicing (MoM, YoY), regression slope, moving averages.

Phase 3 → Anomaly + Rules (Complete)
          Z-Score, IQR, rolling windows, Isolation Forest, conditional business rule evaluator.

Phase 4 → Reporting (Complete)
          Executive PDF (ReportLab), multi-sheet Excel (OpenPyXL), responsive HTML, CSV, JSON.

Phase 5 → Dashboard (Complete)
          FastAPI + SPA dark glassmorphism dashboard, Chart.js interactive visualizations.

Phase 6 → Local LLM (Complete & Extensible)
          Ollama / OpenAI-compatible endpoint integration with strict offline deterministic fallback.

Phase 7 → Advanced Data Lineage (Next Phase)
          Graph visualization with interactive node-by-node drillback from report cell to source column.

Phase 8 → Enterprise Features (Roadmap)
          Role-Based Access Control (RBAC), multi-tenant workspaces, automated email/Slack webhooks,
          S3 / Cloud storage export sinks, and distributed query pushdown for Snowflake/BigQuery.
```
