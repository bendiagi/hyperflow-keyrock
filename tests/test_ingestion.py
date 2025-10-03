"""
Tests for data ingestion module
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from ingestion.coingecko_client import CoinGeckoClient
from ingestion.data_processor import DataProcessor

class TestCoinGeckoClient:
    """Test CoinGecko API client"""
    
    def test_init(self):
        """Test client initialization"""
        client = CoinGeckoClient()
        assert client.base_url is not None
        assert client.session is not None
    
    @patch('ingestion.coingecko_client.requests.Session.get')
    def test_health_check_success(self, mock_get):
        """Test successful health check"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"gecko_says": "pong"}
        mock_get.return_value = mock_response
        
        client = CoinGeckoClient()
        assert client.health_check() is True
    
    @patch('ingestion.coingecko_client.requests.Session.get')
    def test_health_check_failure(self, mock_get):
        """Test failed health check"""
        mock_get.side_effect = Exception("API Error")
        
        client = CoinGeckoClient()
        assert client.health_check() is False

class TestDataProcessor:
    """Test data processing utilities"""
    
    def test_normalize_ohlcv_data(self):
        """Test OHLCV data normalization"""
        # Sample OHLCV data from CoinGecko API
        ohlcv_data = [
            [1640995200000, 47000, 48000, 46000, 47500, 1000000],
            [1640998800000, 47500, 48500, 47000, 48000, 1200000]
        ]
        
        processor = DataProcessor()
        df = processor.normalize_ohlcv_data(ohlcv_data, "bitcoin")
        
        assert not df.empty
        assert len(df) == 2
        assert 'coin' in df.columns
        assert 'timestamp' in df.columns
        assert 'open' in df.columns
        assert 'high' in df.columns
        assert 'low' in df.columns
        assert 'close' in df.columns
        assert 'volume' in df.columns
        assert df['coin'].iloc[0] == "bitcoin"
    
    def test_normalize_empty_data(self):
        """Test handling of empty data"""
        processor = DataProcessor()
        df = processor.normalize_ohlcv_data([], "bitcoin")
        
        assert df.empty
    
    def test_calculate_returns(self):
        """Test returns calculation"""
        data = {
            'close': [100, 105, 110, 108, 112]
        }
        df = pd.DataFrame(data)
        
        processor = DataProcessor()
        result_df = processor.calculate_returns(df)
        
        assert 'returns' in result_df.columns
        assert 'log_returns' in result_df.columns
        assert pd.isna(result_df['returns'].iloc[0])  # First value should be NaN
    
    def test_calculate_volatility(self):
        """Test volatility calculation"""
        data = {
            'close': [100, 105, 110, 108, 112, 115, 120, 118, 125, 130]
        }
        df = pd.DataFrame(data)
        
        processor = DataProcessor()
        result_df = processor.calculate_volatility(df, window=5)
        
        assert 'volatility' in result_df.columns
        assert 'volatility_annualized' in result_df.columns
    
    def test_calculate_moving_averages(self):
        """Test moving average calculation"""
        data = {
            'close': [100, 105, 110, 108, 112, 115, 120, 118, 125, 130]
        }
        df = pd.DataFrame(data)
        
        processor = DataProcessor()
        result_df = processor.calculate_moving_averages(df, windows=[3, 5])
        
        assert 'sma_3' in result_df.columns
        assert 'sma_5' in result_df.columns
        assert 'ema_3' in result_df.columns
        assert 'ema_5' in result_df.columns
    
    def test_detect_outliers_zscore(self):
        """Test outlier detection using Z-score"""
        data = {
            'values': [1, 2, 3, 4, 5, 100]  # 100 is an outlier
        }
        df = pd.DataFrame(data)
        
        processor = DataProcessor()
        result_df = processor.detect_outliers_zscore(df, 'values', threshold=2.0)
        
        assert 'values_zscore' in result_df.columns
        assert 'values_outlier' in result_df.columns
        assert result_df['values_outlier'].iloc[-1] is True  # Last value should be outlier
