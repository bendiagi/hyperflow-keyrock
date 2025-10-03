"""
Database models for HyperFlow
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass
class OHLCVModel:
    """OHLCV data model"""
    coin: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    id: Optional[int] = None
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'coin': self.coin,
            'timestamp': self.timestamp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'id': self.id,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OHLCVModel':
        """Create from dictionary"""
        return cls(
            id=data.get('id'),
            coin=data['coin'],
            timestamp=data['timestamp'],
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close'],
            volume=data['volume'],
            created_at=data.get('created_at')
        )

@dataclass
class ETLLogModel:
    """ETL log model"""
    coin: str
    status: str
    message: str
    records_processed: int
    id: Optional[int] = None
    timestamp: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'coin': self.coin,
            'status': self.status,
            'message': self.message,
            'records_processed': self.records_processed,
            'id': self.id,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ETLLogModel':
        """Create from dictionary"""
        return cls(
            id=data.get('id'),
            coin=data['coin'],
            status=data['status'],
            message=data['message'],
            records_processed=data['records_processed'],
            timestamp=data.get('timestamp')
        )

@dataclass
class AnomalyModel:
    """Anomaly detection model"""
    coin: str
    timestamp: str
    anomaly_type: str
    value: float
    zscore: float
    threshold: float
    id: Optional[int] = None
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'coin': self.coin,
            'timestamp': self.timestamp,
            'anomaly_type': self.anomaly_type,
            'value': self.value,
            'zscore': self.zscore,
            'threshold': self.threshold,
            'id': self.id,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnomalyModel':
        """Create from dictionary"""
        return cls(
            id=data.get('id'),
            coin=data['coin'],
            timestamp=data['timestamp'],
            anomaly_type=data['anomaly_type'],
            value=data['value'],
            zscore=data['zscore'],
            threshold=data['threshold'],
            created_at=data.get('created_at')
        )
