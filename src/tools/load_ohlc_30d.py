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
import time

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
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_convert(None)

    # Fetch coin volumes over the same 30d window using market_chart/range
    try:
        end_ts = int(pd.Timestamp.utcnow().timestamp())
        start_ts = end_ts - 30 * 24 * 3600
        range_payload = client.get_coin_price_history_range(coin, vs_currency="usd", from_ts=start_ts, to_ts=end_ts)
        vol_points = range_payload.get("total_volumes", []) if range_payload else []
        if vol_points:
            vdf = pd.DataFrame(vol_points, columns=["timestamp", "volume_usd"])  # volume in quote currency
            vdf["timestamp"] = pd.to_datetime(vdf["timestamp"], unit="ms", utc=True).dt.tz_convert(None)
            vdf = vdf.set_index("timestamp").sort_index()
            # Resample to 4H sums aligned to candle close (right-closed/right-labeled)
            vdf_4h = (
                vdf.resample("4h", label="right", closed="right").sum().rename(columns={"volume_usd": "volume"})
            )
            vdf_4h = vdf_4h.reset_index()
        else:
            vdf_4h = pd.DataFrame(columns=["timestamp","volume"])  # fallback
    except Exception as e:
        logger.warning("Volume range fetch failed for %s: %s", coin, e)
        vdf_4h = pd.DataFrame(columns=["timestamp","volume"])  # fallback

    # Join 4H volume onto 4H OHLC by candle close timestamp
    df = df.sort_values("timestamp")
    if not vdf_4h.empty:
        df = df.merge(vdf_4h, on="timestamp", how="left")
    if "volume" not in df.columns:
        df["volume"] = 0.0
    df["volume"] = df["volume"].fillna(0.0)
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
            attempts = 0
            delay = 4
            while attempts < 3:
                try:
                    load_coin_ohlc_30d(db, client, coin)
                    break
                except Exception as e:
                    attempts += 1
                    if attempts >= 3:
                        logger.exception("Failed to load %s after retries: %s", coin, e)
                        break
                    logger.warning("Load failed for %s (attempt %s). Backing off %ss...", coin, attempts, delay)
                    time.sleep(delay)
                    delay *= 2
        finally:
            time.sleep(2)
    logger.info("Load complete")


if __name__ == "__main__":
    main()


