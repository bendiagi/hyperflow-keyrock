"""
Anomaly detection algorithms for market data
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple
import logging

try:
    from ..config import Config
except ImportError:
    from config import Config
try:
    from ..database.connection import DatabaseConnection
except ImportError:
    from database.connection import DatabaseConnection

logger = logging.getLogger(__name__)

class AnomalyDetector:
    """Detect anomalies in market data using various methods"""
    
    def __init__(self, db_connection: DatabaseConnection = None):
        self.db_connection = db_connection or DatabaseConnection()
        self.volume_threshold = Config.VOLUME_ZSCORE_THRESHOLD
        self.price_threshold = Config.PRICE_ZSCORE_THRESHOLD
    
    def detect_volume_anomalies(self, df: pd.DataFrame, coin: str) -> pd.DataFrame:
        """
        Detect volume anomalies using Z-score method
        
        Args:
            df: DataFrame with OHLCV data
            coin: Coin identifier
            
        Returns:
            DataFrame with anomaly flags
        """
        if df.empty or 'volume' not in df.columns:
            logger.warning(f"No volume data for {coin}")
            return df
        
        df = df.copy()
        
        # Calculate Z-scores for volume
        volume_mean = df['volume'].mean()
        volume_std = df['volume'].std()
        
        if volume_std == 0:
            logger.warning(f"Volume standard deviation is 0 for {coin}")
            df['volume_zscore'] = 0
            df['volume_anomaly'] = False
        else:
            df['volume_zscore'] = (df['volume'] - volume_mean) / volume_std
            df['volume_anomaly'] = abs(df['volume_zscore']) > self.volume_threshold
        
        # Log anomalies to database
        anomalies = df[df['volume_anomaly']]
        for _, row in anomalies.iterrows():
            self.db_connection.insert_anomaly(
                coin=coin,
                timestamp=row['timestamp'],
                anomaly_type='volume',
                value=row['volume'],
                zscore=row['volume_zscore'],
                threshold=self.volume_threshold
            )
        
        logger.info(f"Detected {len(anomalies)} volume anomalies for {coin}")
        return df
    
    def detect_price_anomalies(self, df: pd.DataFrame, coin: str) -> pd.DataFrame:
        """
        Detect price anomalies using Z-score method
        
        Args:
            df: DataFrame with OHLCV data
            coin: Coin identifier
            
        Returns:
            DataFrame with anomaly flags
        """
        if df.empty or 'close' not in df.columns:
            logger.warning(f"No price data for {coin}")
            return df
        
        df = df.copy()
        
        # Calculate returns first
        df['returns'] = df['close'].pct_change()
        
        # Calculate Z-scores for returns
        returns_mean = df['returns'].mean()
        returns_std = df['returns'].std()
        
        if returns_std == 0:
            logger.warning(f"Returns standard deviation is 0 for {coin}")
            df['price_zscore'] = 0
            df['price_anomaly'] = False
        else:
            df['price_zscore'] = (df['returns'] - returns_mean) / returns_std
            df['price_anomaly'] = abs(df['price_zscore']) > self.price_threshold
        
        # Log anomalies to database
        anomalies = df[df['price_anomaly']]
        for _, row in anomalies.iterrows():
            self.db_connection.insert_anomaly(
                coin=coin,
                timestamp=row['timestamp'],
                anomaly_type='price',
                value=row['close'],
                zscore=row['price_zscore'],
                threshold=self.price_threshold
            )
        
        logger.info(f"Detected {len(anomalies)} price anomalies for {coin}")
        return df
    
    def detect_volatility_spikes(self, df: pd.DataFrame, coin: str, window: int = 24) -> pd.DataFrame:
        """
        Detect volatility spikes
        
        Args:
            df: DataFrame with OHLCV data
            coin: Coin identifier
            window: Rolling window for volatility calculation
            
        Returns:
            DataFrame with volatility anomaly flags
        """
        if df.empty or 'close' not in df.columns:
            logger.warning(f"No price data for {coin}")
            return df
        
        df = df.copy()
        
        # Calculate returns
        df['returns'] = df['close'].pct_change()
        
        # Calculate rolling volatility
        df['volatility'] = df['returns'].rolling(window=window).std()
        
        # Calculate Z-scores for volatility
        vol_mean = df['volatility'].mean()
        vol_std = df['volatility'].std()
        
        if vol_std == 0:
            logger.warning(f"Volatility standard deviation is 0 for {coin}")
            df['volatility_zscore'] = 0
            df['volatility_anomaly'] = False
        else:
            df['volatility_zscore'] = (df['volatility'] - vol_mean) / vol_std
            df['volatility_anomaly'] = abs(df['volatility_zscore']) > self.price_threshold
        
        # Log anomalies to database
        anomalies = df[df['volatility_anomaly']]
        for _, row in anomalies.iterrows():
            self.db_connection.insert_anomaly(
                coin=coin,
                timestamp=row['timestamp'],
                anomaly_type='volatility',
                value=row['volatility'],
                zscore=row['volatility_zscore'],
                threshold=self.price_threshold
            )
        
        logger.info(f"Detected {len(anomalies)} volatility anomalies for {coin}")
        return df
    
    def detect_all_anomalies(self, df: pd.DataFrame, coin: str) -> pd.DataFrame:
        """
        Run all anomaly detection methods
        
        Args:
            df: DataFrame with OHLCV data
            coin: Coin identifier
            
        Returns:
            DataFrame with all anomaly flags
        """
        logger.info(f"Running all anomaly detection for {coin}")
        
        # Detect volume anomalies
        df = self.detect_volume_anomalies(df, coin)
        
        # Detect price anomalies
        df = self.detect_price_anomalies(df, coin)
        
        # Detect volatility spikes
        df = self.detect_volatility_spikes(df, coin)
        
        # Create combined anomaly flag
        df['any_anomaly'] = (
            df.get('volume_anomaly', False) |
            df.get('price_anomaly', False) |
            df.get('volatility_anomaly', False)
        )
        
        total_anomalies = df['any_anomaly'].sum()
        logger.info(f"Total anomalies detected for {coin}: {total_anomalies}")
        
        return df
    
    def get_anomaly_summary(self, coin: str = None, limit: int = 100) -> Dict[str, Any]:
        """
        Get summary of detected anomalies
        
        Args:
            coin: Coin identifier (optional)
            limit: Maximum number of records to return
            
        Returns:
            Dictionary with anomaly summary
        """
        anomalies = self.db_connection.get_anomalies(coin, limit)
        
        if not anomalies:
            return {
                'total_anomalies': 0,
                'by_type': {},
                'by_coin': {},
                'recent_anomalies': []
            }
        
        # Count by type
        by_type = {}
        by_coin = {}
        
        for anomaly in anomalies:
            anomaly_type = anomaly['anomaly_type']
            coin_name = anomaly['coin']
            
            by_type[anomaly_type] = by_type.get(anomaly_type, 0) + 1
            by_coin[coin_name] = by_coin.get(coin_name, 0) + 1
        
        return {
            'total_anomalies': len(anomalies),
            'by_type': by_type,
            'by_coin': by_coin,
            'recent_anomalies': anomalies[:10]  # Most recent 10
        }
    
    def get_anomaly_trends(self, coin: str, days: int = 7) -> Dict[str, Any]:
        """
        Get anomaly trends over time
        
        Args:
            coin: Coin identifier
            days: Number of days to analyze
            
        Returns:
            Dictionary with trend analysis
        """
        # Get recent data
        recent_data = self.db_connection.get_latest_data(coin, days * 24)  # Assuming hourly data
        
        if not recent_data:
            return {'error': 'No data available'}
        
        # Convert to DataFrame
        df = pd.DataFrame(recent_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Get anomalies for this period
        anomalies = self.db_connection.get_anomalies(coin, days * 24)
        anomaly_df = pd.DataFrame(anomalies)
        
        if not anomaly_df.empty:
            anomaly_df['timestamp'] = pd.to_datetime(anomaly_df['timestamp'])
            
            # Group by day
            daily_anomalies = anomaly_df.groupby(anomaly_df['timestamp'].dt.date).size()
            
            return {
                'daily_anomaly_counts': daily_anomalies.to_dict(),
                'total_anomalies': len(anomaly_df),
                'most_common_type': anomaly_df['anomaly_type'].mode().iloc[0] if not anomaly_df.empty else None,
                'average_zscore': anomaly_df['zscore'].mean() if not anomaly_df.empty else 0
            }
        
        return {'total_anomalies': 0, 'daily_anomaly_counts': {}}
