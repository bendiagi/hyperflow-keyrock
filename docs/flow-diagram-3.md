### HyperFlow — Final Architecture Flow (Used + Missing, Left ➜ Right)

This version keeps only what the app actually uses today, corrects inaccuracies, and adds missing steps. Style matches the existing numbered flow.

1. Data Sources (APIs)
- CoinGecko: OHLC (`/coins/{id}/ohlc`), market ranges (`/market_chart` + `/market_chart/range`)
- OpenAI: chat completions for summaries/Q&A
- Repo: `src/ingestion/coingecko_client.py`, `src/llm/gpt_client.py`

2. Orchestrator (Manual / Ad-hoc)
- Manual CLI: `python -m src.main` runs the ETL for all `Config.SUPPORTED_COINS`
- UI-triggered refresh path: `dashboard._refresh_ohlc_30d(coin)` (manual per-coin)
- Repo: `src/main.py`, `src/visualization/dashboard.py`

3. Ingestion (Fetcher)
- Handles rate limiting, retries, timeouts
- Methods: `health_check()`, `get_ohlcv_data(coin, days)`, `get_coin_price_history_range(...)`
- Repo: `src/ingestion/coingecko_client.py`

4. Transform / Normalize
- `DataProcessor.normalize_ohlcv_data`: parse timestamps (ms → datetime), numeric coercion, sort
- UI refresh: merges 30d 4H volume from `market_chart/range` into OHLC
- Repo: `src/ingestion/data_processor.py`, refresh logic in `dashboard._refresh_ohlc_30d`

5. Primary Storage (SQLite)
- Tables created on startup: `ohlcv`, `etl_logs`, `anomalies`; unique `(coin, timestamp)` on `ohlcv`
- Indexes: `(coin, timestamp)` across tables
- Repo: `src/database/connection.py`

6. Processing & Anomaly Detection
- Volume/price/volatility z-score detection; writes to `anomalies`
- Used both in ETL (`src/main.py`) and at view-time for highlighting
- Repo: `src/analysis/anomaly_detection.py`

7. Logging & Run Records
- ETL outcomes recorded in `etl_logs` (status, message, records_processed)
- App logging via Python logging configuration
- Repo: `src/database/connection.py` (insert_etl_log), `src/main.py`

8. Internal Query Layer (In-Process)
- Read/write via `DatabaseConnection`: `get_latest_data`, `get_anomalies`, `get_etl_logs`, `get_database_stats`
- No external REST/GraphQL layer today
- Repo: `src/database/connection.py`

9. Dashboard & Research UI (Streamlit)
- Entry: `app.py` → `src/visualization/dashboard.py`
- Tabs: Charts, Anomalies, Metrics, AI Insights
- Reads latest OHLCV → computes metrics → flags anomalies for display
- Can trigger per-coin 30d/4H refresh (write path)

10. Metrics / Indicators (View-Time)
- `MetricsCalculator.calculate_all_metrics`: returns, volatility, SMA/EMA, Bollinger Bands, RSI, MACD, volume metrics
- Applied when rendering charts; not persisted
- Repo: `src/analysis/metrics.py`

11. LLM Adapter (Conversational Layer)
- Summaries and Q&A using compact data snapshot (recent OHLC, last price/indicators)
- Provider: OpenAI via `GPTClient`
- Repo: `src/llm/gpt_client.py`

12. End-to-End Sequence (Concrete, Left ➜ Right)
- CLI ETL: `src/main.py`
  - validate config → `CoinGeckoClient.health_check()`
  - for coin in `SUPPORTED_COINS`: `get_ohlcv_data` → `normalize_ohlcv_data` → `insert_ohlcv_data`
  - `detect_all_anomalies` → `insert_anomaly`
  - `insert_etl_log`
- UI Read: `dashboard.py`
  - `get_latest_data` → `calculate_all_metrics` → `detect_all_anomalies`(view) → render Tabs
- UI Refresh: `dashboard._refresh_ohlc_30d`
  - fetch OHLC + market ranges → build 4H volume → `DELETE` coin rows → `UPSERT` new → `INSERT etl_log`
- LLM: `GPTClient`
  - build summary → OpenAI → render response

Notes / Removals
- Removed: dedicated scheduler, alerting/workflows, external API layer, CI/CD & secret manager (not present here today)
- Added explicitly: UI-triggered 30d/4H refresh write-path; view-time indicator computation


