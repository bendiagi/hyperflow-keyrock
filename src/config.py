"""
Configuration management for HyperFlow
"""

import os
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # API Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")
    COINGECKO_BASE_URL = os.getenv("COINGECKO_BASE_URL", "https://api.coingecko.com/api/v3")
    
    # Database Configuration
    DATABASE_PATH = os.getenv("DATABASE_PATH", "data/market_data.db")
    
    # Application Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY = int(os.getenv("RETRY_DELAY", "1"))
    
    # Supported Crypto Pairs
    SUPPORTED_COINS = os.getenv("SUPPORTED_COINS", "bitcoin,ethereum,solana,cardano,binancecoin").split(",")
    
    # Anomaly Detection Thresholds
    VOLUME_ZSCORE_THRESHOLD = float(os.getenv("VOLUME_ZSCORE_THRESHOLD", "3.0"))
    PRICE_ZSCORE_THRESHOLD = float(os.getenv("PRICE_ZSCORE_THRESHOLD", "2.5"))
    
    # Streamlit Configuration
    STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", "8501"))
    STREAMLIT_THEME = os.getenv("STREAMLIT_THEME", "light")
    
    # Data Processing
    DEFAULT_TIMEFRAME = "1d"
    SUPPORTED_TIMEFRAMES = ["1h", "1d", "7d", "30d"]
    
    # Rate Limiting
    API_RATE_LIMIT = 10  # requests per minute
    REQUEST_TIMEOUT = 30  # seconds
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required")
        if not cls.COINGECKO_BASE_URL:
            raise ValueError("COINGECKO_BASE_URL is required")
        return True
