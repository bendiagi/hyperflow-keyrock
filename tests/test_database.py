"""
Tests for database module
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from database.connection import DatabaseConnection
from database.models import OHLCVModel, ETLLogModel, AnomalyModel

class TestDatabaseConnection:
    """Test database connection and operations"""
    
    def setup_method(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_connection = DatabaseConnection(self.temp_db.name)
    
    def teardown_method(self):
        """Clean up test database"""
        os.unlink(self.temp_db.name)
    
    def test_database_creation(self):
        """Test database and tables are created"""
        # Check if tables exist
        tables_query = "SELECT name FROM sqlite_master WHERE type='table'"
        tables = self.db_connection.execute_query(tables_query)
        table_names = [table['name'] for table in tables]
        
        assert 'ohlcv' in table_names
        assert 'etl_logs' in table_names
        assert 'anomalies' in table_names
    
    def test_insert_ohlcv_data(self):
        """Test OHLCV data insertion"""
        test_data = [
            {
                'coin': 'bitcoin',
                'timestamp': '2024-01-01T00:00:00Z',
                'open': 47000.0,
                'high': 48000.0,
                'low': 46000.0,
                'close': 47500.0,
                'volume': 1000000.0
            },
            {
                'coin': 'bitcoin',
                'timestamp': '2024-01-01T01:00:00Z',
                'open': 47500.0,
                'high': 48500.0,
                'low': 47000.0,
                'close': 48000.0,
                'volume': 1200000.0
            }
        ]
        
        rows_inserted = self.db_connection.insert_ohlcv_data(test_data)
        assert rows_inserted == 2
        
        # Verify data was inserted
        data = self.db_connection.get_latest_data('bitcoin', 10)
        assert len(data) == 2
        assert data[0]['coin'] == 'bitcoin'
        assert data[0]['close'] == 48000.0
    
    def test_insert_etl_log(self):
        """Test ETL log insertion"""
        self.db_connection.insert_etl_log(
            coin='bitcoin',
            status='success',
            message='Test message',
            records_processed=10
        )
        
        logs = self.db_connection.get_etl_logs('bitcoin', 10)
        assert len(logs) == 1
        assert logs[0]['coin'] == 'bitcoin'
        assert logs[0]['status'] == 'success'
        assert logs[0]['records_processed'] == 10
    
    def test_insert_anomaly(self):
        """Test anomaly insertion"""
        self.db_connection.insert_anomaly(
            coin='bitcoin',
            timestamp='2024-01-01T00:00:00Z',
            anomaly_type='volume',
            value=1000000.0,
            zscore=3.5,
            threshold=3.0
        )
        
        anomalies = self.db_connection.get_anomalies('bitcoin', 10)
        assert len(anomalies) == 1
        assert anomalies[0]['coin'] == 'bitcoin'
        assert anomalies[0]['anomaly_type'] == 'volume'
        assert anomalies[0]['zscore'] == 3.5
    
    def test_get_database_stats(self):
        """Test database statistics"""
        # Insert some test data
        test_data = [
            {
                'coin': 'bitcoin',
                'timestamp': '2024-01-01T00:00:00Z',
                'open': 47000.0,
                'high': 48000.0,
                'low': 46000.0,
                'close': 47500.0,
                'volume': 1000000.0
            }
        ]
        self.db_connection.insert_ohlcv_data(test_data)
        
        stats = self.db_connection.get_database_stats()
        assert 'ohlcv_count' in stats
        assert 'unique_coins' in stats
        assert stats['ohlcv_count'] == 1
        assert stats['unique_coins'] == 1

class TestModels:
    """Test data models"""
    
    def test_ohlcv_model(self):
        """Test OHLCV model"""
        model = OHLCVModel(
            coin='bitcoin',
            timestamp='2024-01-01T00:00:00Z',
            open=47000.0,
            high=48000.0,
            low=46000.0,
            close=47500.0,
            volume=1000000.0
        )
        
        # Test to_dict
        data_dict = model.to_dict()
        assert data_dict['coin'] == 'bitcoin'
        assert data_dict['close'] == 47500.0
        
        # Test from_dict
        model_from_dict = OHLCVModel.from_dict(data_dict)
        assert model_from_dict.coin == 'bitcoin'
        assert model_from_dict.close == 47500.0
    
    def test_etl_log_model(self):
        """Test ETL log model"""
        model = ETLLogModel(
            coin='bitcoin',
            status='success',
            message='Test message',
            records_processed=10
        )
        
        # Test to_dict
        data_dict = model.to_dict()
        assert data_dict['coin'] == 'bitcoin'
        assert data_dict['status'] == 'success'
        
        # Test from_dict
        model_from_dict = ETLLogModel.from_dict(data_dict)
        assert model_from_dict.coin == 'bitcoin'
        assert model_from_dict.status == 'success'
    
    def test_anomaly_model(self):
        """Test anomaly model"""
        model = AnomalyModel(
            coin='bitcoin',
            timestamp='2024-01-01T00:00:00Z',
            anomaly_type='volume',
            value=1000000.0,
            zscore=3.5,
            threshold=3.0
        )
        
        # Test to_dict
        data_dict = model.to_dict()
        assert data_dict['coin'] == 'bitcoin'
        assert data_dict['anomaly_type'] == 'volume'
        
        # Test from_dict
        model_from_dict = AnomalyModel.from_dict(data_dict)
        assert model_from_dict.coin == 'bitcoin'
        assert model_from_dict.anomaly_type == 'volume'
