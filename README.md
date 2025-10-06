# HyperFlow: AI-Powered Crypto Market Data ETL & 4H OHLC Dashboard 🚀

**Automated Market Data Pipeline with LLM-powered Insights**

A lightweight, flexible, and cost-effective ETL pipeline that ingests crypto market data, stores it locally, and provides conversational insights via GPT APIs.

## Overview

HyperFlow demonstrates how to build an internal market data pipeline that balances the tradeoffs between buying expensive third-party tools and building resource-intensive custom solutions. It's designed for trading teams, risk management, and business operations.

## Features

- 📊 **Real-time Data Ingestion**: Fetches OHLCV data from CoinGecko API
- 💾 **Local Storage**: SQLite database for fast prototyping
- 🔍 **Anomaly Detection**: Z-score based volume and price spike detection
- 📈 **Interactive Dashboard**: Streamlit-based visualization with charts and alerts
- 🤖 **AI-Powered Insights**: GPT API integration for natural language queries
- ⚡ **Lightweight & Fast**: Optimized for <5s ingestion times

## Quick Start

### Prerequisites

- Python 3.10+
- OpenAI API key
- CoinGecko API access (free tier)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/bendiagi/hyperflow-keyrock.git
cd hyperflow-keyrock
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. Run the pipeline:
```bash
python src/ingestion/main.py
```

5. Launch the dashboard:
```bash
streamlit run src/visualization/dashboard.py
```

## Project Structure

```
hyperflow/
├── docs/                    # Documentation
│   ├── prd.md              # Product Requirements
│   ├── technical-specs.md  # Technical Specifications
│   └── implementation-plan.md # Implementation Plan
├── src/                    # Source code
│   ├── ingestion/          # Data ingestion pipeline
│   ├── database/           # Database models and connections
│   ├── analysis/           # Anomaly detection and metrics
│   ├── visualization/      # Streamlit dashboard
│   └── llm/               # GPT API integration
├── tests/                  # Test suite
├── data/                   # Data storage
└── requirements.txt        # Python dependencies
```

## Usage

### Data Ingestion

The pipeline automatically fetches OHLCV data for configured crypto pairs:

```python
from src.ingestion.coingecko_client import CoinGeckoClient

client = CoinGeckoClient()
data = client.fetch_ohlcv('bitcoin', days=7)
```

### Anomaly Detection

Detect unusual market activity:

```python
from src.analysis.anomaly_detection import AnomalyDetector

detector = AnomalyDetector()
anomalies = detector.detect_volume_spikes('bitcoin', threshold=3.0)
```

### Conversational Queries

Ask questions about your data:

- "Show me BTC's volatility spikes in the past 24 hours"
- "What coins had >20% volume jump this week?"
- "Summarize ETH's last 7 days in plain English"

## Configuration

Edit `src/config.py` to customize:

- Crypto pairs to track
- Timeframes (1h, 1d)
- Anomaly detection thresholds
- API rate limits

## API Reference

### CoinGecko Client
- `fetch_ohlcv(coin_id, days)`: Get OHLCV data
- `get_coin_list()`: List available coins
- `get_market_data(coin_ids)`: Get market data

### Anomaly Detection
- `detect_volume_spikes(coin, threshold)`: Detect volume anomalies
- `calculate_volatility(coin, window)`: Calculate rolling volatility
- `get_moving_averages(coin, windows)`: Calculate moving averages

### GPT Integration
- `ask_question(question, context)`: Query data with natural language
- `summarize_data(coin, timeframe)`: Get AI summary of market data

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Code Quality

```bash
black src/
flake8 src/
mypy src/
```

### Docker

```bash
docker build -t hyperflow .
docker run -p 8501:8501 hyperflow
```

## Roadmap

### Phase 1 (MVP) ✅
- [x] Basic data ingestion
- [x] SQLite storage
- [x] Anomaly detection
- [x] Streamlit dashboard
- [x] GPT integration

### Phase 2 (Scale) 🚧
- [ ] Multi-exchange support (Binance, Coinbase)
- [ ] PostgreSQL migration
- [ ] Real-time streaming
- [ ] Slack/Telegram alerts

### Phase 3 (Advanced) 📋
- [ ] ML forecasting models
- [ ] Role-based access
- [ ] Advanced analytics
- [ ] Cloud deployment

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- CoinGecko for market data API
- OpenAI for GPT API
- Streamlit for dashboard framework
- Keyrock for inspiration and requirements

---

**Built with ❤️ for the crypto trading community**
