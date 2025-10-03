"""
Data processing utilities for market data
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class DataProcessor:
    """Process and normalize market data"""
    
    @staticmethod
    def normalize_ohlcv_data(ohlcv_data: List[List[float]], coin_id: str) -> pd.DataFrame:
        """
        Convert raw OHLCV data to normalized DataFrame
        
        Args:
            ohlcv_data: Raw OHLCV data from CoinGecko API
            coin_id: Coin identifier
            
        Returns:
            Normalized DataFrame with columns: timestamp, open, high, low, close, volume
        """
        if not ohlcv_data:
            logger.warning(f"No OHLCV data for {coin_id}")
            return pd.DataFrame()
        
        # CoinGecko OHLC endpoint returns: [timestamp, open, high, low, close]
        # Some sources may include volume as a 6th element. Support both.
        first_row_len = len(ohlcv_data[0]) if ohlcv_data and isinstance(ohlcv_data[0], (list, tuple)) else 0
        if first_row_len == 5:
            df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close'])
            # Add volume as NaN when not provided
            df['volume'] = np.nan
        elif first_row_len == 6:
            df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        else:
            logger.error(f"Unexpected OHLCV row length: {first_row_len}")
            return pd.DataFrame()
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Add coin identifier
        df['coin'] = coin_id
        
        # Ensure numeric columns are float
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns + ['volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Remove rows with NaN in price fields, but allow missing volume
        df = df.dropna(subset=price_columns)
        
        # Sort by timestamp
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        logger.info(f"Normalized {len(df)} OHLCV records for {coin_id}")
        return df
    
    @staticmethod
    def normalize_price_history(price_data: Dict[str, Any], coin_id: str) -> pd.DataFrame:
        """
        Convert price history data to normalized DataFrame
        
        Args:
            price_data: Price history data from CoinGecko API
            coin_id: Coin identifier
            
        Returns:
            Normalized DataFrame with price and volume data
        """
        if not price_data or 'prices' not in price_data:
            logger.warning(f"No price history data for {coin_id}")
            return pd.DataFrame()
        
        # Extract prices and volumes
        prices = price_data.get('prices', [])
        volumes = price_data.get('total_volumes', [])
        
        if not prices:
            return pd.DataFrame()
        
        # Create DataFrame
        df = pd.DataFrame(prices, columns=['timestamp', 'price'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Add volume data if available
        if volumes and len(volumes) == len(prices):
            volume_df = pd.DataFrame(volumes, columns=['timestamp', 'volume'])
            volume_df['timestamp'] = pd.to_datetime(volume_df['timestamp'], unit='ms')
            df = df.merge(volume_df, on='timestamp', how='left')
        else:
            df['volume'] = np.nan
        
        # Add coin identifier
        df['coin'] = coin_id
        
        # Ensure numeric columns
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        
        # Remove NaN values
        df = df.dropna()
        
        # Sort by timestamp
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        logger.info(f"Normalized {len(df)} price history records for {coin_id}")
        return df
    
    @staticmethod
    def calculate_returns(df: pd.DataFrame, price_column: str = 'close') -> pd.DataFrame:
        """
        Calculate returns for price data
        
        Args:
            df: DataFrame with price data
            price_column: Column name for price data
            
        Returns:
            DataFrame with returns column added
        """
        if price_column not in df.columns:
            logger.error(f"Price column '{price_column}' not found in DataFrame")
            return df
        
        df = df.copy()
        df['returns'] = df[price_column].pct_change()
        df['log_returns'] = np.log(df[price_column] / df[price_column].shift(1))
        
        return df
    
    @staticmethod
    def calculate_volatility(df: pd.DataFrame, window: int = 24, price_column: str = 'close') -> pd.DataFrame:
        """
        Calculate rolling volatility
        
        Args:
            df: DataFrame with price data
            window: Rolling window size
            price_column: Column name for price data
            
        Returns:
            DataFrame with volatility column added
        """
        df = df.copy()
        
        if 'returns' not in df.columns:
            df = DataProcessor.calculate_returns(df, price_column)
        
        df['volatility'] = df['returns'].rolling(window=window).std()
        df['volatility_annualized'] = df['volatility'] * np.sqrt(365)  # Annualized
        
        return df
    
    @staticmethod
    def calculate_moving_averages(df: pd.DataFrame, price_column: str = 'close', 
                                windows: List[int] = [7, 30]) -> pd.DataFrame:
        """
        Calculate moving averages
        
        Args:
            df: DataFrame with price data
            price_column: Column name for price data
            windows: List of window sizes for moving averages
            
        Returns:
            DataFrame with moving average columns added
        """
        df = df.copy()
        
        for window in windows:
            col_name = f'sma_{window}'
            df[col_name] = df[price_column].rolling(window=window).mean()
        
        return df
    
    @staticmethod
    def detect_outliers_zscore(df: pd.DataFrame, column: str, threshold: float = 3.0) -> pd.DataFrame:
        """
        Detect outliers using Z-score method
        
        Args:
            df: DataFrame with data
            column: Column to analyze
            threshold: Z-score threshold for outlier detection
            
        Returns:
            DataFrame with outlier flags
        """
        df = df.copy()
        
        if column not in df.columns:
            logger.error(f"Column '{column}' not found in DataFrame")
            return df
        
        # Calculate Z-scores
        mean = df[column].mean()
        std = df[column].std()
        
        if std == 0:
            logger.warning(f"Standard deviation is 0 for column '{column}'")
            df[f'{column}_zscore'] = 0
            df[f'{column}_outlier'] = False
        else:
            df[f'{column}_zscore'] = (df[column] - mean) / std
            df[f'{column}_outlier'] = abs(df[f'{column}_zscore']) > threshold
        
        return df
    
    @staticmethod
    def resample_data(df: pd.DataFrame, freq: str = '1H', price_column: str = 'close') -> pd.DataFrame:
        """
        Resample data to different frequency
        
        Args:
            df: DataFrame with timestamp index
            freq: Resampling frequency
            price_column: Column name for price data
            
        Returns:
            Resampled DataFrame
        """
        if 'timestamp' not in df.columns:
            logger.error("Timestamp column not found in DataFrame")
            return df
        
        df = df.copy()
        df = df.set_index('timestamp')
        
        # Resample OHLCV data
        ohlc_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        
        resampled = df.resample(freq).agg(ohlc_dict)
        resampled = resampled.dropna()
        
        # Reset index to get timestamp back as column
        resampled = resampled.reset_index()
        
        logger.info(f"Resampled data to {freq} frequency: {len(resampled)} records")
        return resampled
