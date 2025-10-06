### HyperFlow Architecture — Whiteboard Outline (Left ➜ Right)

Use this 15-section outline to draw the system left-to-right on a whiteboard. Each section maps to concrete modules in this repo and includes suggested arrow labels.

1. Data Sources (APIs)
- Sources: CoinGecko (prices, OHLC, market ranges), OpenAI (LLM)
- Repo: `src/ingestion/coingecko_client.py`, `src/llm/gpt_client.py`
- Arrow labels: “GET /coins/{id}/ohlc”, “GET /market_chart(/range)”, “chat.completions.create”

2. Scheduler / Orchestrator
- Trigger the pipeline periodically or on demand
- Today: manual CLI `python -m src.main` or UI refresh button; future: cron/Airflow
- Repo: `src/main.py` (acts as simple orchestrator)
- Arrow labels: “for coin in SUPPORTED_COINS → fetch/process/store/log”

3. Ingestion Service (Fetcher)
- Concern: resilient HTTP, rate limits, retries, backoff
- Repo: `src/ingestion/coingecko_client.py` (`_make_request`, `_rate_limit`)
- Arrow labels: “health_check → ping”, “get_ohlcv_data(days=7|30)”

4. Raw Staging / Cache (Optional)
- Current: no raw staging persisted; data flows directly to transforms
- Option: add `data/raw/` parquet or Redis for caching
- Arrow labels: “(optional) write raw → raw_store”, “read raw → transformer”

5. Transformer / Normalizer
- Normalize, resample, add indicators; combine volumes for 30d refresh
- Repo: `src/ingestion/data_processor.py`, `src/analysis/metrics.py`
- Key funcs: `normalize_ohlcv_data`, `build_ohlcv_from_ticks`, `calculate_all_metrics`
- Arrow labels: “normalize OHLCV”, “resample 4h”, “compute SMA/RSI/MACD/BB/volatility”

6. Primary Storage (SQLite / Database)
- Tables: `ohlcv`, `etl_logs`, `anomalies` with `(coin, timestamp)` indexes
- Repo: `src/database/connection.py` (DDL + CRUD)
- Arrow labels: “UPSERT ohlcv”, “INSERT etl_logs”, “INSERT anomalies”, “SELECT latest”

7. Processing & Anomaly Detection Engine
- Detect volume, price, volatility anomalies; persist events
- Repo: `src/analysis/anomaly_detection.py`
- Arrow labels: “calc z-scores”, “flag anomalies”, “write anomalies → DB”

8. Alerting & Workflow Integrations
- Current: none configured; anomalies are stored and surfaced in UI
- Future: email/webhook/Slack for anomaly notifications
- Arrow labels: “on anomaly → notify(channel)”

9. Internal API / Query Layer
- Current: in-process DB access via `DatabaseConnection`
- Future: REST/GraphQL service for external consumers
- Repo: `src/database/connection.py`
- Arrow labels: “get_latest_data(coin, limit)”, “get_etl_logs”, “get_anomalies”

10. Dashboard & Research UI
- Streamlit app with tabs: Charts, Anomalies, Metrics, AI Insights
- Repo: `app.py` → `src/visualization/dashboard.py`
- Arrow labels: “render OHLCV + indicators”, “refresh 30d/4h”, “summaries/trends table”

11. LLM Adapter / Conversational Layer
- Summarization and Q&A over computed summaries
- Repo: `src/llm/gpt_client.py`
- Arrow labels: “build prompt → OpenAI”, “return analysis → UI”

12. Monitoring, Logs & Metrics
- Python logging; ETL outcomes in `etl_logs`; DB stats surfaced in UI
- Repo: `src/main.py` (logging), `src/database/connection.py` (`get_database_stats`)
- Arrow labels: “log info/warn/error”, “SELECT counts/date_range”

13. CI/CD & Secrets Management
- Current: local execution; .env support (see `env.example`), `requirements.txt`
- Future: Render deployment (frontend/backend), GitHub Actions, secret managers
- Arrow labels: “build → test → deploy”, “inject OPENAI_API_KEY, DB path, thresholds”

14. Optional / Future Components
- Caching layer (Redis), feature store, vector DB for embeddings
- External alerting pipelines, REST API, multi-chain data sources
- Arrow labels: “cache hit/miss”, “publish → queue”, “serve features → models”

15. Sequence Flow (End-to-End Process Overview)
- Left ➜ Right path to draw:
  - Data Sources → Scheduler → Ingestion → (Raw Staging?) → Transformer → Primary Storage → Processing/Anomalies → Internal Query → Dashboard → LLM
- Concrete path in this repo:
  1) Orchestrator: `src/main.py`
     - “validate config → health_check(CoinGecko)”
     - “for each coin → get_ohlcv_data(days=7)”
  2) Transform: `DataProcessor.normalize_ohlcv_data`
     - “clean/parse timestamps → numeric → sort”
  3) Store: `DatabaseConnection.insert_ohlcv_data`
     - “UPSERT into ohlcv (coin,timestamp unique)”
  4) Process: `AnomalyDetector.detect_all_anomalies`
     - “zscore(volume/returns/volatility) → INSERT anomalies”
  5) Log: `insert_etl_log`
     - “status, message, records_processed → etl_logs”
  6) UI Read: `dashboard.py`
     - “get_latest_data → calculate_all_metrics → detect_all_anomalies (view)”
     - Tabs render charts, tables
  7) Manual Refresh (30d/4h): `dashboard._refresh_ohlc_30d`
     - “GET ohlc + market_chart/range → merge 4h volume → DELETE coin rows → INSERT new → INSERT etl_log”
  8) LLM: `GPTClient`
     - “build summary payload → OpenAI → render response”

Whiteboard tips
- Keep 3 swimlanes: External (APIs), Core Services, Storage/UI.
- Label arrows with the verbs above; keep Storage at far right; UI at mid-right; LLM on the far right after UI.



