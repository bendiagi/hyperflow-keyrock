"""
Financial metrics calculations for market data
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class MetricsCalculator:
    """Calculate various financial metrics for market data"""
    
    @staticmethod
    def calculate_returns(df: pd.DataFrame, price_column: str = 'close') -> pd.DataFrame:
        """
        Calculate returns for price data
        
        Args:
            df: DataFrame with price data
            price_column: Column name for price data
            
        Returns:
            DataFrame with returns columns added
        """
        if price_column not in df.columns:
            logger.error(f"Price column '{price_column}' not found")
            return df
        
        df = df.copy()
        
        # Simple returns
        df['returns'] = df[price_column].pct_change()
        
        # Log returns
        df['log_returns'] = np.log(df[price_column] / df[price_column].shift(1))
        
        # Cumulative returns
        df['cumulative_returns'] = (1 + df['returns']).cumprod() - 1
        
        return df
    
    @staticmethod
    def calculate_volatility(df: pd.DataFrame, price_column: str = 'close', 
                           window: int = 24, annualize: bool = True) -> pd.DataFrame:
        """
        Calculate rolling volatility
        
        Args:
            df: DataFrame with price data
            price_column: Column name for price data
            window: Rolling window size
            annualize: Whether to annualize volatility
            
        Returns:
            DataFrame with volatility columns added
        """
        if price_column not in df.columns:
            logger.error(f"Price column '{price_column}' not found")
            return df
        
        df = df.copy()
        
        # Calculate returns first
        if 'returns' not in df.columns:
            df = MetricsCalculator.calculate_returns(df, price_column)
        
        # Rolling volatility
        df['volatility'] = df['returns'].rolling(window=window).std()
        
        if annualize:
            # Annualize volatility (assuming daily data)
            df['volatility_annualized'] = df['volatility'] * np.sqrt(365)
        
        return df
    
    @staticmethod
    def calculate_moving_averages(df: pd.DataFrame, price_column: str = 'close',
                                windows: List[int] = [7, 30, 90]) -> pd.DataFrame:
        """
        Calculate simple and exponential moving averages
        
        Args:
            df: DataFrame with price data
            price_column: Column name for price data
            windows: List of window sizes
            
        Returns:
            DataFrame with moving average columns added
        """
        if price_column not in df.columns:
            logger.error(f"Price column '{price_column}' not found")
            return df
        
        df = df.copy()
        
        for window in windows:
            # Simple Moving Average
            df[f'sma_{window}'] = df[price_column].rolling(window=window).mean()
            
            # Exponential Moving Average
            df[f'ema_{window}'] = df[price_column].ewm(span=window).mean()
        
        return df
    
    @staticmethod
    def calculate_bollinger_bands(df: pd.DataFrame, price_column: str = 'close',
                                window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
        """
        Calculate Bollinger Bands
        
        Args:
            df: DataFrame with price data
            price_column: Column name for price data
            window: Rolling window size
            num_std: Number of standard deviations
            
        Returns:
            DataFrame with Bollinger Bands added
        """
        if price_column not in df.columns:
            logger.error(f"Price column '{price_column}' not found")
            return df
        
        df = df.copy()
        
        # Calculate moving average
        df['bb_middle'] = df[price_column].rolling(window=window).mean()
        
        # Calculate standard deviation
        df['bb_std'] = df[price_column].rolling(window=window).std()
        
        # Calculate upper and lower bands
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * num_std)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * num_std)
        
        # Calculate Bollinger Band position
        df['bb_position'] = (df[price_column] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        return df
    
    @staticmethod
    def calculate_rsi(df: pd.DataFrame, price_column: str = 'close', window: int = 14) -> pd.DataFrame:
        """
        Calculate Relative Strength Index (RSI)
        
        Args:
            df: DataFrame with price data
            price_column: Column name for price data
            window: RSI window size
            
        Returns:
            DataFrame with RSI column added
        """
        if price_column not in df.columns:
            logger.error(f"Price column '{price_column}' not found")
            return df
        
        df = df.copy()
        
        # Calculate price changes
        df['price_change'] = df[price_column].diff()
        
        # Separate gains and losses
        df['gains'] = df['price_change'].where(df['price_change'] > 0, 0)
        df['losses'] = -df['price_change'].where(df['price_change'] < 0, 0)
        
        # Calculate average gains and losses
        df['avg_gains'] = df['gains'].rolling(window=window).mean()
        df['avg_losses'] = df['losses'].rolling(window=window).mean()
        
        # Calculate RSI
        rs = df['avg_gains'] / df['avg_losses']
        df['rsi'] = 100 - (100 / (1 + rs))
        
        return df
    
    @staticmethod
    def calculate_macd(df: pd.DataFrame, price_column: str = 'close',
                      fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        Args:
            df: DataFrame with price data
            price_column: Column name for price data
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period
            
        Returns:
            DataFrame with MACD columns added
        """
        if price_column not in df.columns:
            logger.error(f"Price column '{price_column}' not found")
            return df
        
        df = df.copy()
        
        # Calculate EMAs
        df['ema_fast'] = df[price_column].ewm(span=fast).mean()
        df['ema_slow'] = df[price_column].ewm(span=slow).mean()
        
        # Calculate MACD line
        df['macd'] = df['ema_fast'] - df['ema_slow']
        
        # Calculate signal line
        df['macd_signal'] = df['macd'].ewm(span=signal).mean()
        
        # Calculate histogram
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        return df
    
    @staticmethod
    def calculate_volume_metrics(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate volume-based metrics
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with volume metrics added
        """
        if 'volume' not in df.columns:
            logger.error("Volume column not found")
            return df
        
        df = df.copy()
        
        # Volume moving averages
        df['volume_sma_7'] = df['volume'].rolling(window=7).mean()
        df['volume_sma_30'] = df['volume'].rolling(window=30).mean()
        
        # Volume ratio (current volume vs average)
        df['volume_ratio'] = df['volume'] / df['volume_sma_30']
        
        # Volume-weighted average price (VWAP)
        df['vwap'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
        
        return df
    
    @staticmethod
    def calculate_all_metrics(df: pd.DataFrame, price_column: str = 'close') -> pd.DataFrame:
        """
        Calculate all available metrics
        
        Args:
            df: DataFrame with OHLCV data
            price_column: Column name for price data
            
        Returns:
            DataFrame with all metrics added
        """
        logger.info("Calculating all financial metrics")
        
        # Calculate returns
        df = MetricsCalculator.calculate_returns(df, price_column)
        
        # Calculate volatility
        df = MetricsCalculator.calculate_volatility(df, price_column)
        
        # Calculate moving averages
        df = MetricsCalculator.calculate_moving_averages(df, price_column)
        
        # Calculate Bollinger Bands
        df = MetricsCalculator.calculate_bollinger_bands(df, price_column)
        
        # Calculate RSI
        df = MetricsCalculator.calculate_rsi(df, price_column)
        
        # Calculate MACD
        df = MetricsCalculator.calculate_macd(df, price_column)
        
        # Calculate volume metrics
        df = MetricsCalculator.calculate_volume_metrics(df)
        
        logger.info("All metrics calculated successfully")
        return df
    
    @staticmethod
    def get_summary_statistics(df: pd.DataFrame, price_column: str = 'close') -> Dict[str, Any]:
        """
        Get summary statistics for the data
        
        Args:
            df: DataFrame with market data
            price_column: Column name for price data
            
        Returns:
            Dictionary with summary statistics
        """
        if df.empty:
            return {'error': 'No data available'}
        
        stats = {}
        
        # Basic price statistics
        if price_column in df.columns:
            stats['price'] = {
                'min': df[price_column].min(),
                'max': df[price_column].max(),
                'mean': df[price_column].mean(),
                'std': df[price_column].std(),
                'current': df[price_column].iloc[-1] if not df.empty else None
            }
        
        # Volume statistics
        if 'volume' in df.columns:
            stats['volume'] = {
                'min': df['volume'].min(),
                'max': df['volume'].max(),
                'mean': df['volume'].mean(),
                'std': df['volume'].std(),
                'current': df['volume'].iloc[-1] if not df.empty else None
            }
        
        # Returns statistics
        if 'returns' in df.columns:
            stats['returns'] = {
                'min': df['returns'].min(),
                'max': df['returns'].max(),
                'mean': df['returns'].mean(),
                'std': df['returns'].std()
            }
        
        # Volatility statistics
        if 'volatility' in df.columns:
            stats['volatility'] = {
                'current': df['volatility'].iloc[-1] if not df.empty else None,
                'mean': df['volatility'].mean(),
                'max': df['volatility'].max()
            }
        
        # Data quality
        stats['data_quality'] = {
            'total_records': len(df),
            'missing_values': df.isnull().sum().to_dict(),
            'date_range': {
                'start': df['timestamp'].min() if 'timestamp' in df.columns else None,
                'end': df['timestamp'].max() if 'timestamp' in df.columns else None
            }
        }
        
        return stats
