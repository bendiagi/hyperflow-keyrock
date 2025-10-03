"""
Simple test for HyperFlow components
"""

import sys
import os
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Now we can import directly
from config import Config
from database.connection import DatabaseConnection

def test_basic_setup():
    """Test basic setup and configuration"""
    print("🧪 Testing HyperFlow basic setup...")
    
    try:
        # Test configuration
        print(f"✅ Config loaded: {Config.SUPPORTED_COINS}")
        print(f"✅ Database path: {Config.DATABASE_PATH}")
        
        # Test database connection
        db = DatabaseConnection()
        print("✅ Database connection successful")
        
        # Test database stats
        stats = db.get_database_stats()
        print(f"✅ Database stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_coingecko_api():
    """Test CoinGecko API connection"""
    print("\n🌐 Testing CoinGecko API...")
    
    try:
        from ingestion.coingecko_client import CoinGeckoClient
        
        client = CoinGeckoClient()
        
        # Test health check
        if client.health_check():
            print("✅ CoinGecko API is accessible")
            return True
        else:
            print("❌ CoinGecko API health check failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing CoinGecko API: {e}")
        return False

def test_data_processing():
    """Test data processing"""
    print("\n📊 Testing data processing...")
    
    try:
        from ingestion.data_processor import DataProcessor
        import pandas as pd
        
        processor = DataProcessor()
        
        # Create sample data
        sample_data = [
            [1640995200000, 47000, 48000, 46000, 47500, 1000000],
            [1640998800000, 47500, 48500, 47000, 48000, 1200000]
        ]
        
        # Test normalization
        df = processor.normalize_ohlcv_data(sample_data, "bitcoin")
        
        if not df.empty:
            print(f"✅ Data processing successful: {len(df)} records")
            print(f"✅ Columns: {list(df.columns)}")
            return True
        else:
            print("❌ Data processing failed - empty DataFrame")
            return False
            
    except Exception as e:
        print(f"❌ Error testing data processing: {e}")
        return False

if __name__ == "__main__":
    print("🚀 HyperFlow Component Tests\n")
    
    tests = [
        test_basic_setup,
        test_coingecko_api,
        test_data_processing
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! HyperFlow is ready to go!")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
