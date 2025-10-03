"""
Purge DB and load 4-hour OHLC candles (past 30 days) from CoinGecko OHLC API.

Endpoint: /coins/{id}/ohlc?vs_currency=usd&days=30
Response: [timestamp_ms, open, high, low, close]
Note: timestamp is the end (close) time of the candle.
Volume is not provided; we will store 0.0.
"""

import sys
from pathlib import Path
import logging
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import Config
from database.connection import DatabaseConnection
from ingestion.coingecko_client import CoinGeckoClient

logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("load_ohlc_30d")


def load_coin_ohlc_30d(db: DatabaseConnection, client: CoinGeckoClient, coin: str) -> None:
    logger.info("Loading 30d 4H candles for %s", coin)
    raw = client.get_ohlcv_data(coin_id=coin, days=30)
    if not raw:
        logger.warning("No OHLC data for %s", coin)
        return
    # raw rows: [timestamp_ms, open, high, low, close]
    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["volume"] = 0.0
    df["coin"] = coin
    # purge existing rows for this coin completely (we only want 30d 4H)
    deleted = db.execute_update("DELETE FROM ohlcv WHERE coin = ?", (coin,))
    inserted = db.insert_ohlcv_data(df[["coin","timestamp","open","high","low","close","volume"]].to_dict("records"))
    db.insert_etl_log(coin=coin, status="success", message=f"load_ohlc_30d: deleted {deleted}, inserted {inserted}", records_processed=inserted)
    logger.info("%s: deleted=%s inserted=%s", coin, deleted, inserted)


def main():
    db = DatabaseConnection()
    client = CoinGeckoClient()
    if not client.health_check():
        logger.error("CoinGecko API is not accessible")
        sys.exit(1)
    for coin in Config.SUPPORTED_COINS:
        try:
            load_coin_ohlc_30d(db, client, coin)
        except Exception as e:
            logger.exception("Failed to load %s: %s", coin, e)
    logger.info("Load complete")


if __name__ == "__main__":
    main()


