### HyperFlow Architecture (Used Components Only) — Left ➜ Right

Scope: This reflects what exists in this repo today. It removes unused placeholders and adds the UI-driven refresh path that’s unique here.

Included components
- External APIs: CoinGecko, OpenAI
- Orchestrator: Simple CLI runner (`src/main.py`) and UI-triggered refresh
- Ingestion: `CoinGeckoClient`
- Transform: `DataProcessor` (+ indicators computed at view-time by `MetricsCalculator`)
- Storage: SQLite (`ohlcv`, `etl_logs`, `anomalies`)
- Processing: `AnomalyDetector` (persists anomaly events)
- Internal Query: `DatabaseConnection` (in-process)
- UI: Streamlit Dashboard (`app.py` → `src/visualization/dashboard.py`)
- LLM: `GPTClient`
- Monitoring & Logs: Python logging + `etl_logs` + DB stats

Excluded (not present today)
- Dedicated scheduler (Airflow/Cron), alerting pipelines, REST/GraphQL service, CI/CD pipeline, secret manager

```mermaid
flowchart LR

  %% External
  CG[CoinGecko API]
  OA[OpenAI API]

  %% Orchestrators
  CLI[Orchestrator: src/main.py]
  UIREF[UI Refresh: dashboard._refresh_ohlc_30d]

  %% Ingestion & Transform
  CLC[CoinGeckoClient]
  DP[DataProcessor]

  %% Storage / Query
  DC[DatabaseConnection]
  subgraph DB[(SQLite)]
    T1[(ohlcv)]
    T2[(etl_logs)]
    T3[(anomalies)]
  end

  %% Processing
  AD[AnomalyDetector]
  MC[MetricsCalculator]

  %% UI & LLM
  UI[Streamlit Dashboard]
  GPT[GPTClient]

  %% CLI ETL path
  CLI -->|health_check / fetch| CLC
  CLC -->|ohlc / market_chart| DP
  DP -->|normalized OHLCV| DC
  DC -->|UPSERT| T1
  CLI -->|insert_etl_log| DC
  DC -->|INSERT| T2
  CLI -->|detect_all_anomalies| AD
  AD -->|INSERT anomalies| DC
  DC -->|INSERT| T3

  %% UI read path
  UI -->|get_latest_data(coin, limit)| DC
  DC -->|SELECT| T1
  UI -->|calculate_all_metrics| MC
  UI -->|detect_all_anomalies(view)| AD

  %% UI refresh path (30d / 4H)
  UIREF -->|ohlc + market_chart/range| CLC
  CLC --> DP
  DP --> DC
  DC -->|DELETE coin rows + UPSERT| T1
  DC -->|INSERT| T2

  %% LLM
  UI -->|summary/Q&A| GPT
  GPT -.->|chat| OA
```

Left ➜ Right sequence (concrete, minimal)
1) CLI ETL: `src/main.py`
   - Validate config → health_check(CoinGecko)
   - For each coin: fetch OHLC → normalize → upsert `ohlcv`
   - Detect anomalies → insert into `anomalies`
   - Insert ETL log → `etl_logs`

2) UI (read): `src/visualization/dashboard.py`
   - `get_latest_data` → `ohlcv` → `calculate_all_metrics` → `detect_all_anomalies` (in-view flags)
   - Render Charts, Anomalies, Metrics

3) UI Refresh (write): `dashboard._refresh_ohlc_30d`
   - Fetch `ohlc` + `market_chart/range` → merge 4H volume
   - `DELETE` coin rows → `UPSERT` new OHLCV → `INSERT` ETL log

4) LLM: `GPTClient`
   - Build compact summary → OpenAI → render response

Notes
- Rate limiting, retries, exponential backoff handled in `CoinGeckoClient._make_request`.
- DB schema created at runtime in `DatabaseConnection._create_tables`.
- Anomalies are both persisted (ETL) and recomputed for UI highlighting.

