"""
Test script for HyperFlow pipeline
"""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from ingestion.coingecko_client import CoinGeckoClient
from ingestion.data_processor import DataProcessor
from database.connection import DatabaseConnection
from analysis.anomaly_detection import AnomalyDetector
from analysis.metrics import MetricsCalculator
from config import Config

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_pipeline():
    """Test the HyperFlow pipeline"""
    logger.info("Starting HyperFlow pipeline test")
    
    try:
        # Validate configuration
        Config.validate()
        logger.info("Configuration validated successfully")
        
        # Initialize components
        db_connection = DatabaseConnection()
        coingecko_client = CoinGeckoClient()
        data_processor = DataProcessor()
        anomaly_detector = AnomalyDetector(db_connection)
        metrics_calculator = MetricsCalculator()
        
        # Check API health
        if not coingecko_client.health_check():
            logger.error("CoinGecko API is not accessible")
            return False
        
        logger.info("CoinGecko API health check passed")
        
        # Test with just one coin first
        test_coin = "bitcoin"
        logger.info(f"Testing with {test_coin}")
        
        try:
            # Fetch OHLCV data
            ohlcv_data = coingecko_client.get_ohlcv_data(test_coin, days=1)
            
            if not ohlcv_data:
                logger.warning(f"No OHLCV data received for {test_coin}")
                return False
            
            logger.info(f"Received {len(ohlcv_data)} OHLCV records for {test_coin}")
            
            # Process and normalize data
            df = data_processor.normalize_ohlcv_data(ohlcv_data, test_coin)
            
            if df.empty:
                logger.warning(f"No data to process for {test_coin}")
                return False
            
            logger.info(f"Normalized {len(df)} records for {test_coin}")
            
            # Calculate metrics
            df = metrics_calculator.calculate_all_metrics(df)
            logger.info("Metrics calculated successfully")
            
            # Detect anomalies
            df = anomaly_detector.detect_all_anomalies(df, test_coin)
            logger.info("Anomaly detection completed")
            
            # Store data in database
            records = df.to_dict('records')
            records_inserted = db_connection.insert_ohlcv_data(records)
            
            # Log ETL success
            db_connection.insert_etl_log(
                coin=test_coin,
                status="success",
                message=f"Test processed {records_inserted} records",
                records_processed=records_inserted
            )
            
            logger.info(f"Successfully processed {records_inserted} records for {test_coin}")
            
            # Get database statistics
            stats = db_connection.get_database_stats()
            logger.info(f"Database statistics: {stats}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing {test_coin}: {e}")
            
            # Log ETL error
            db_connection.insert_etl_log(
                coin=test_coin,
                status="error",
                message=str(e),
                records_processed=0
            )
            return False
        
    except Exception as e:
        logger.error(f"Fatal error in pipeline test: {e}")
        return False

if __name__ == "__main__":
    success = test_pipeline()
    if success:
        print("✅ Pipeline test completed successfully!")
        sys.exit(0)
    else:
        print("❌ Pipeline test failed!")
        sys.exit(1)

