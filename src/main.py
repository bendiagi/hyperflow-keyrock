"""
Main application entry point for HyperFlow
"""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))

from .ingestion.coingecko_client import CoinGeckoClient
from .ingestion.data_processor import DataProcessor
from .database.connection import DatabaseConnection
from .analysis.anomaly_detection import AnomalyDetector
from .analysis.metrics import MetricsCalculator
from .config import Config

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Main application function"""
    logger.info("Starting HyperFlow data pipeline")
    
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
            return
        
        logger.info("CoinGecko API health check passed")
        
        # Process each supported coin
        for coin in Config.SUPPORTED_COINS:
            logger.info(f"Processing {coin}")
            
            try:
                # Fetch OHLCV data
                ohlcv_data = coingecko_client.get_ohlcv_data(coin, days=7)
                
                if not ohlcv_data:
                    logger.warning(f"No OHLCV data received for {coin}")
                    continue
                
                # Process and normalize data
                df = data_processor.normalize_ohlcv_data(ohlcv_data, coin)
                
                if df.empty:
                    logger.warning(f"No data to process for {coin}")
                    continue
                
                # Calculate metrics
                df = metrics_calculator.calculate_all_metrics(df)
                
                # Detect anomalies
                df = anomaly_detector.detect_all_anomalies(df, coin)
                
                # Store data in database
                records = df.to_dict('records')
                records_inserted = db_connection.insert_ohlcv_data(records)
                
                # Log ETL success
                db_connection.insert_etl_log(
                    coin=coin,
                    status="success",
                    message=f"Processed {records_inserted} records",
                    records_processed=records_inserted
                )
                
                logger.info(f"Successfully processed {records_inserted} records for {coin}")
                
            except Exception as e:
                logger.error(f"Error processing {coin}: {e}")
                
                # Log ETL error
                db_connection.insert_etl_log(
                    coin=coin,
                    status="error",
                    message=str(e),
                    records_processed=0
                )
        
        # Get database statistics
        stats = db_connection.get_database_stats()
        logger.info(f"Database statistics: {stats}")
        
        logger.info("HyperFlow data pipeline completed successfully")
        
    except Exception as e:
        logger.error(f"Fatal error in main pipeline: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
