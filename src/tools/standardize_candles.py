"""
Standardize all stored OHLCV data to 30-minute candles with real volumes.

For each coin in Config.SUPPORTED_COINS:
  - Determine the time range to rebuild (from earliest stored timestamp, or last 7d if none) to now
  - Fetch CoinGecko market_chart/range for that window
  - Resample to 30-minute candles using proper OHLC aggregation and volume sum
  - Delete all existing rows for the coin in the rebuilt window
  - Insert standardized 30-minute rows
"""

import sys
from pathlib import Path
import time
import logging
import math
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import Config
from database.connection import DatabaseConnection
from ingestion.coingecko_client import CoinGeckoClient
from ingestion.data_processor import DataProcessor

logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("standardize_candles")


def _fetch_range_prices(client: CoinGeckoClient, coin: str, start_ts: int, end_ts: int) -> pd.DataFrame:
    """Fetch price+volume for range and return a DataFrame with timestamp, close, volume"""
    data = client.get_coin_price_history_range(coin, vs_currency="usd", from_ts=start_ts, to_ts=end_ts)
    if not data or "prices" not in data:
        return pd.DataFrame()
    prices = data.get("prices", [])
    volumes = data.get("total_volumes", [])
    price_df = pd.DataFrame(prices, columns=["timestamp", "close"]) if prices else pd.DataFrame(columns=["timestamp","close"])
    if price_df.empty:
        return pd.DataFrame()
    price_df["timestamp"] = pd.to_datetime(price_df["timestamp"], unit="ms")
    vol_df = pd.DataFrame(volumes, columns=["timestamp", "volume"]) if volumes else pd.DataFrame(columns=["timestamp","volume"])
    if not vol_df.empty:
        vol_df["timestamp"] = pd.to_datetime(vol_df["timestamp"], unit="ms")
        df = price_df.merge(vol_df, on="timestamp", how="left")
    else:
        df = price_df
        df["volume"] = 0.0
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def _resample_to_30min(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    # Construct OHLC columns from close (best-effort) before resampling
    df["open"] = df["close"]
    df["high"] = df["close"]
    df["low"] = df["close"]
    df = df[["timestamp","open","high","low","close","volume"]]
    df = df.set_index("timestamp")
    ohlc = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    # Use '30min' instead of '30T' to avoid FutureWarning
    out = df.resample("30min").agg(ohlc).dropna().reset_index()
    return out


def standardize_coin(db: DatabaseConnection, client: CoinGeckoClient, coin: str) -> None:
    logger.info("Standardizing coin to 30-min: %s", coin)
    # Determine range from DB
    stats = db.get_database_stats()
    # Query min/max for this coin directly
    rows = db.execute_query("SELECT MIN(timestamp) AS earliest, MAX(timestamp) AS latest FROM ohlcv WHERE coin = ?", (coin,))
    if rows and rows[0].get("earliest"):
        earliest_iso = rows[0]["earliest"]
        earliest_ts = int(pd.to_datetime(earliest_iso).timestamp())
    else:
        # fallback: last 7d only
        earliest_ts = int((pd.Timestamp.utcnow() - pd.Timedelta(days=7)).timestamp())
    latest_ts = int(pd.Timestamp.utcnow().timestamp())

    # CoinGecko range can handle large windows, but to be safe, split into chunks (e.g., 7d chunks)
    chunk_seconds = 7 * 24 * 3600
    chunks = math.ceil((latest_ts - earliest_ts) / chunk_seconds) or 1
    all_parts: list[pd.DataFrame] = []
    for i in range(chunks):
        start = earliest_ts + i * chunk_seconds
        end = min(earliest_ts + (i + 1) * chunk_seconds, latest_ts)
        if start >= end:
            continue
        part = _fetch_range_prices(client, coin, start, end)
        if not part.empty:
            all_parts.append(part)
        time.sleep(0.2)  # be nice to the API

    if not all_parts:
        logger.warning("No data returned for %s; skipping", coin)
        return

    df = pd.concat(all_parts, ignore_index=True).drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
    # Build OHLC properly from ticks
    price_df = df[["timestamp","close"]].rename(columns={"close":"price"})
    vol_df = df[["timestamp","volume"]]
    df_30 = DataProcessor.build_ohlcv_from_ticks(price_df=price_df, volume_df=vol_df, freq="30min")
    df_30["coin"] = coin

    # Delete existing coin rows entirely, then insert standardized
    deleted = db.execute_update("DELETE FROM ohlcv WHERE coin = ?", (coin,))
    inserted = db.insert_ohlcv_data(df_30.to_dict("records"))
    db.insert_etl_log(coin=coin, status="success", message=f"standardize_30m: deleted {deleted}, inserted {inserted}", records_processed=inserted)
    logger.info("%s standardized: deleted=%s, inserted=%s", coin, deleted, inserted)


def main():
    db = DatabaseConnection()
    client = CoinGeckoClient()
    if not client.health_check():
        logger.error("CoinGecko API is not accessible")
        sys.exit(1)
    for coin in Config.SUPPORTED_COINS:
        try:
            standardize_coin(db, client, coin)
        except Exception as e:
            logger.exception("Failed to standardize %s: %s", coin, e)
    logger.info("Standardization complete")


if __name__ == "__main__":
    main()


