"""
CoinGecko API client for fetching crypto market data
"""

import requests
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd

try:
    from ..config import Config
except ImportError:
    from config import Config

logger = logging.getLogger(__name__)

class CoinGeckoClient:
    """Client for interacting with CoinGecko API"""
    
    def __init__(self):
        self.base_url = Config.COINGECKO_BASE_URL
        self.session = requests.Session()
        headers = {
            'User-Agent': 'HyperFlow/1.0.0',
            'Accept': 'application/json'
        }
        # Use CoinGecko Pro key when provided so usage reflects under account
        if Config.COINGECKO_API_KEY:
            headers['x-cg-pro-api-key'] = Config.COINGECKO_API_KEY
        self.session.headers.update(headers)
        self.rate_limit_delay = 60 / Config.API_RATE_LIMIT  # seconds between requests
        self.last_request_time = 0
        
    def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make API request with error handling and retries"""
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(Config.MAX_RETRIES):
            try:
                self._rate_limit()
                
                response = self.session.get(
                    url, 
                    params=params, 
                    timeout=Config.REQUEST_TIMEOUT
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    # Rate limited
                    wait_time = Config.RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    response.raise_for_status()
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt == Config.MAX_RETRIES - 1:
                    raise
                time.sleep(Config.RETRY_DELAY * (2 ** attempt))
        
        raise Exception("Max retries exceeded")
    
    def get_coin_list(self) -> List[Dict[str, Any]]:
        """Get list of all supported coins"""
        logger.info("Fetching coin list from CoinGecko")
        return self._make_request("coins/list")
    
    def get_coin_market_data(self, coin_ids: List[str], vs_currency: str = "usd") -> List[Dict[str, Any]]:
        """Get market data for multiple coins"""
        logger.info(f"Fetching market data for {len(coin_ids)} coins")
        
        params = {
            "ids": ",".join(coin_ids),
            "vs_currency": vs_currency,
            "order": "market_cap_desc",
            "per_page": 100,
            "page": 1,
            "sparkline": False,
            "price_change_percentage": "24h,7d,30d"
        }
        
        return self._make_request("coins/markets", params)
    
    def get_ohlcv_data(self, coin_id: str, vs_currency: str = "usd", days: int = 7) -> List[List[float]]:
        """Get OHLCV data for a specific coin"""
        logger.info(f"Fetching OHLCV data for {coin_id} ({days} days)")
        
        params = {
            "vs_currency": vs_currency,
            "days": days
        }
        
        endpoint = f"coins/{coin_id}/ohlc"
        return self._make_request(endpoint, params)
    
    def get_coin_price_history(self, coin_id: str, vs_currency: str = "usd", days: int = 7) -> Dict[str, Any]:
        """Get price history with timestamps"""
        logger.info(f"Fetching price history for {coin_id} ({days} days)")
        
        params = {
            "vs_currency": vs_currency,
            "days": days
        }
        
        endpoint = f"coins/{coin_id}/market_chart"
        return self._make_request(endpoint, params)
    
    def search_coin(self, query: str) -> List[Dict[str, Any]]:
        """Search for coins by name or symbol"""
        logger.info(f"Searching for coins matching: {query}")
        
        params = {"query": query}
        return self._make_request("search", params)
    
    def get_trending_coins(self) -> Dict[str, Any]:
        """Get trending coins"""
        logger.info("Fetching trending coins")
        return self._make_request("search/trending")
    
    def get_global_market_data(self) -> Dict[str, Any]:
        """Get global cryptocurrency market data"""
        logger.info("Fetching global market data")
        return self._make_request("global")
    
    def health_check(self) -> bool:
        """Check if API is accessible"""
        try:
            self._make_request("ping")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
