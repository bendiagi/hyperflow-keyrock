"""
Database connection and management
"""

import sqlite3
import math
import logging
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import os

try:
    from ..config import Config
except ImportError:
    from config import Config

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """SQLite database connection manager"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self._ensure_data_directory()
        self._create_tables()
    
    def _ensure_data_directory(self):
        """Ensure data directory exists"""
        data_dir = os.path.dirname(self.db_path)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
            logger.info(f"Created data directory: {data_dir}")
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create OHLCV table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ohlcv (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coin TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(coin, timestamp)
                )
            """)
            
            # Create ETL logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS etl_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coin TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT,
                    records_processed INTEGER DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create anomalies table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS anomalies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coin TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    anomaly_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    zscore REAL NOT NULL,
                    threshold REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ohlcv_coin_timestamp ON ohlcv(coin, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_etl_logs_coin_timestamp ON etl_logs(coin, timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_coin_timestamp ON anomalies(coin, timestamp)")
            
            conn.commit()
            logger.info("Database tables created successfully")
    
    @contextmanager
    def get_connection(self):
        """Get database connection with context manager"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute SELECT query and return results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE query and return affected rows"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
    
    def insert_ohlcv_data(self, data: List[Dict[str, Any]]) -> int:
        """Insert OHLCV data into database"""
        if not data:
            return 0
        
        query = """
            INSERT OR REPLACE INTO ohlcv 
            (coin, timestamp, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        records = []
        for record in data:
            # Ensure timestamp is a string acceptable by SQLite
            ts_value = record['timestamp']
            try:
                # pandas.Timestamp -> ISO 8601 string
                if hasattr(ts_value, 'isoformat'):
                    ts_str = ts_value.isoformat()
                else:
                    ts_str = str(ts_value)
            except Exception:
                ts_str = str(ts_value)
            
            records.append((
                record['coin'],
                ts_str,
                record['open'],
                record['high'],
                record['low'],
                record['close'],
                (0.0 if (record.get('volume') is None or (isinstance(record.get('volume'), float) and math.isnan(record.get('volume')))) else record.get('volume'))
            ))
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, records)
            conn.commit()
            return cursor.rowcount
    
    def insert_etl_log(self, coin: str, status: str, message: str = "", records_processed: int = 0):
        """Insert ETL log entry"""
        query = """
            INSERT INTO etl_logs (coin, status, message, records_processed)
            VALUES (?, ?, ?, ?)
        """
        self.execute_update(query, (coin, status, message, records_processed))
    
    def insert_anomaly(self, coin: str, timestamp: str, anomaly_type: str, 
                      value: float, zscore: float, threshold: float):
        """Insert anomaly record"""
        # Ensure timestamp is string for SQLite
        ts_value = timestamp
        try:
            if hasattr(ts_value, 'isoformat'):
                ts_str = ts_value.isoformat()
            else:
                ts_str = str(ts_value)
        except Exception:
            ts_str = str(ts_value)
        query = """
            INSERT INTO anomalies 
            (coin, timestamp, anomaly_type, value, zscore, threshold)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        self.execute_update(query, (coin, ts_str, anomaly_type, value, zscore, threshold))
    
    def get_latest_data(self, coin: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get latest OHLCV data for a coin"""
        query = """
            SELECT * FROM ohlcv 
            WHERE coin = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """
        return self.execute_query(query, (coin, limit))
    
    def get_data_by_date_range(self, coin: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get OHLCV data for a date range"""
        query = """
            SELECT * FROM ohlcv 
            WHERE coin = ? AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp ASC
        """
        return self.execute_query(query, (coin, start_date, end_date))

    def delete_data_since(self, coin: str, since_timestamp: str) -> int:
        """Delete OHLCV rows for coin since given ISO timestamp (inclusive)"""
        query = """
            DELETE FROM ohlcv
            WHERE coin = ? AND timestamp >= ?
        """
        return self.execute_update(query, (coin, since_timestamp))
    
    def get_anomalies(self, coin: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get anomaly records"""
        if coin:
            query = """
                SELECT * FROM anomalies 
                WHERE coin = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """
            return self.execute_query(query, (coin, limit))
        else:
            query = """
                SELECT * FROM anomalies 
                ORDER BY timestamp DESC 
                LIMIT ?
            """
            return self.execute_query(query, (limit,))
    
    def get_etl_logs(self, coin: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get ETL log entries"""
        if coin:
            query = """
                SELECT * FROM etl_logs 
                WHERE coin = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """
            return self.execute_query(query, (coin, limit))
        else:
            query = """
                SELECT * FROM etl_logs 
                ORDER BY timestamp DESC 
                LIMIT ?
            """
            return self.execute_query(query, (limit,))
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {}
        
        # Get table counts
        tables = ['ohlcv', 'etl_logs', 'anomalies']
        for table in tables:
            query = f"SELECT COUNT(*) as count FROM {table}"
            result = self.execute_query(query)
            stats[f'{table}_count'] = result[0]['count'] if result else 0
        
        # Get unique coins
        query = "SELECT COUNT(DISTINCT coin) as count FROM ohlcv"
        result = self.execute_query(query)
        stats['unique_coins'] = result[0]['count'] if result else 0
        
        # Get date range
        query = """
            SELECT 
                MIN(timestamp) as earliest,
                MAX(timestamp) as latest
            FROM ohlcv
        """
        result = self.execute_query(query)
        if result:
            stats['date_range'] = {
                'earliest': result[0]['earliest'],
                'latest': result[0]['latest']
            }
        
        return stats
