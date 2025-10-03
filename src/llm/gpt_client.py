"""
GPT API client for conversational insights
"""

import openai
from typing import Dict, Any, List, Optional
import logging
import json

try:
    from ..config import Config
except ImportError:
    from config import Config

logger = logging.getLogger(__name__)

class GPTClient:
    """Client for interacting with OpenAI GPT API"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = "gpt-3.5-turbo"
        self.max_tokens = 1000
        self.temperature = 0.7
    
    def analyze_market_data(self, data_summary: Dict[str, Any], question: str) -> str:
        """
        Analyze market data and answer questions
        
        Args:
            data_summary: Summary of market data
            question: User's question
            
        Returns:
            AI-generated response
        """
        try:
            prompt = self._create_analysis_prompt(data_summary, question)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a crypto market analyst. Provide clear, concise, and trader-friendly insights."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error analyzing market data: {e}")
            return f"Sorry, I encountered an error while analyzing the data: {str(e)}"
    
    def generate_market_summary(self, data_summary: Dict[str, Any]) -> str:
        """
        Generate a market summary
        
        Args:
            data_summary: Summary of market data
            
        Returns:
            AI-generated market summary
        """
        try:
            prompt = self._create_summary_prompt(data_summary)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a crypto market analyst. Provide a clear and insightful market summary."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating market summary: {e}")
            return f"Sorry, I encountered an error while generating the summary: {str(e)}"
    
    def detect_patterns(self, data_summary: Dict[str, Any]) -> str:
        """
        Detect patterns in market data
        
        Args:
            data_summary: Summary of market data
            
        Returns:
            AI-generated pattern analysis
        """
        try:
            prompt = self._create_pattern_prompt(data_summary)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a crypto market analyst. Identify patterns and trends in the data."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error detecting patterns: {e}")
            return f"Sorry, I encountered an error while detecting patterns: {str(e)}"
    
    def _create_analysis_prompt(self, data_summary: Dict[str, Any], question: str) -> str:
        """Create prompt for market data analysis"""
        prompt = f"""
        You are analyzing cryptocurrency market data. Here's the data summary:
        
        {json.dumps(data_summary, indent=2)}
        
        Question: {question}
        
        Please provide a clear, concise answer that would be helpful for a trader or analyst.
        Focus on actionable insights and avoid speculation.
        """
        return prompt
    
    def _create_summary_prompt(self, data_summary: Dict[str, Any]) -> str:
        """Create prompt for market summary generation"""
        prompt = f"""
        You are analyzing cryptocurrency market data. Here's the data summary:
        
        {json.dumps(data_summary, indent=2)}
        
        Please provide a comprehensive market summary that includes:
        1. Key price movements and trends
        2. Volume analysis
        3. Volatility assessment
        4. Any notable patterns or anomalies
        5. Overall market sentiment
        
        Write this as if you're briefing a trading team.
        """
        return prompt
    
    def _create_pattern_prompt(self, data_summary: Dict[str, Any]) -> str:
        """Create prompt for pattern detection"""
        prompt = f"""
        You are analyzing cryptocurrency market data for patterns. Here's the data summary:
        
        {json.dumps(data_summary, indent=2)}
        
        Please identify and explain any notable patterns, including:
        1. Price patterns (trends, reversals, consolidations)
        2. Volume patterns (unusual activity, accumulation/distribution)
        3. Volatility patterns (spikes, periods of calm)
        4. Technical patterns (support/resistance, moving average crossovers)
        5. Anomalies or unusual behavior
        
        Focus on patterns that could be significant for trading decisions.
        """
        return prompt
    
    def health_check(self) -> bool:
        """Check if GPT API is accessible"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            return True
        except Exception as e:
            logger.error(f"GPT API health check failed: {e}")
            return False
