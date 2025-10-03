"""
Streamlit dashboard for HyperFlow
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, Any, List
import logging

try:
    # Prefer absolute imports when running via app.py (which adds src to sys.path)
    from database.connection import DatabaseConnection
    from analysis.anomaly_detection import AnomalyDetector
    from analysis.metrics import MetricsCalculator
    from config import Config
except ImportError:
    # Fallback for package-relative execution
    from ..database.connection import DatabaseConnection
    from ..analysis.anomaly_detection import AnomalyDetector
    from ..analysis.metrics import MetricsCalculator
    from ..config import Config

logger = logging.getLogger(__name__)

class StreamlitDashboard:
    """Streamlit dashboard for market data visualization"""
    
    def __init__(self):
        self.db_connection = DatabaseConnection()
        self.anomaly_detector = AnomalyDetector(self.db_connection)
        self.metrics_calculator = MetricsCalculator()
        
        # Configure Streamlit
        st.set_page_config(
            page_title="HyperFlow - Market Data Dashboard",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def run(self):
        """Run the Streamlit dashboard"""
        st.title("🚀 HyperFlow - Market Data Dashboard")
        st.markdown("**Automated Market Data Pipeline with LLM-powered Insights**")
        
        # Sidebar
        self._render_sidebar()
        
        # Main content
        self._render_main_content()
    
    def _render_sidebar(self):
        """Render sidebar controls"""
        st.sidebar.header("📈 Controls")
        
        # Coin selection
        available_coins = self._get_available_coins()
        selected_coin = st.sidebar.selectbox(
            "Select Coin",
            available_coins,
            index=0 if available_coins else None
        )
        
        # Time range selection
        time_range = st.sidebar.selectbox(
            "Time Range",
            ["Last 24 Hours", "Last 7 Days", "Last 30 Days", "Last 90 Days"],
            index=1
        )
        
        # Anomaly detection settings
        st.sidebar.header("🔍 Anomaly Detection")
        volume_threshold = st.sidebar.slider(
            "Volume Z-Score Threshold",
            min_value=1.0,
            max_value=5.0,
            value=Config.VOLUME_ZSCORE_THRESHOLD,
            step=0.1
        )
        
        price_threshold = st.sidebar.slider(
            "Price Z-Score Threshold",
            min_value=1.0,
            max_value=5.0,
            value=Config.PRICE_ZSCORE_THRESHOLD,
            step=0.1
        )
        
        # Store in session state
        st.session_state.selected_coin = selected_coin
        st.session_state.time_range = time_range
        st.session_state.volume_threshold = volume_threshold
        st.session_state.price_threshold = price_threshold
    
    def _render_main_content(self):
        """Render main dashboard content"""
        if not st.session_state.get('selected_coin'):
            st.warning("Please select a coin from the sidebar")
            return
        
        coin = st.session_state.selected_coin
        time_range = st.session_state.time_range
        
        # Get data
        data = self._get_coin_data(coin, time_range)
        
        if data.empty:
            st.error(f"No data available for {coin}")
            return
        
        # Calculate metrics
        data = self.metrics_calculator.calculate_all_metrics(data)
        
        # Detect anomalies
        data = self.anomaly_detector.detect_all_anomalies(data, coin)
        
        # Render tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Charts", "🔍 Anomalies", "📈 Metrics", "🤖 AI Insights"])
        
        with tab1:
            self._render_charts(data, coin)
        
        with tab2:
            self._render_anomalies(coin)
        
        with tab3:
            self._render_metrics(data, coin)
        
        with tab4:
            self._render_ai_insights(data, coin)
    
    def _get_available_coins(self) -> List[str]:
        """Get list of available coins"""
        try:
            stats = self.db_connection.get_database_stats()
            # This would need to be implemented in the database connection
            return Config.SUPPORTED_COINS
        except Exception as e:
            logger.error(f"Error getting available coins: {e}")
            return Config.SUPPORTED_COINS
    
    def _get_coin_data(self, coin: str, time_range: str) -> pd.DataFrame:
        """Get data for selected coin and time range"""
        try:
            # Map time range to days
            days_map = {
                "Last 24 Hours": 1,
                "Last 7 Days": 7,
                "Last 30 Days": 30,
                "Last 90 Days": 90
            }
            
            days = days_map.get(time_range, 7)
            limit = days * 24  # Assuming hourly data
            
            data = self.db_connection.get_latest_data(coin, limit)
            
            if not data:
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting coin data: {e}")
            return pd.DataFrame()
    
    def _render_charts(self, data: pd.DataFrame, coin: str):
        """Render price and volume charts"""
        st.header(f"📊 {coin.upper()} Market Data")
        
        # OHLCV Chart
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=(f"{coin.upper()} Price", "Volume"),
            row_heights=[0.7, 0.3]
        )
        
        # Price chart
        fig.add_trace(
            go.Candlestick(
                x=data['timestamp'],
                open=data['open'],
                high=data['high'],
                low=data['low'],
                close=data['close'],
                name="OHLC"
            ),
            row=1, col=1
        )
        
        # Moving averages
        if 'sma_7' in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data['timestamp'],
                    y=data['sma_7'],
                    name="SMA 7",
                    line=dict(color='orange', width=1)
                ),
                row=1, col=1
            )
        
        if 'sma_30' in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data['timestamp'],
                    y=data['sma_30'],
                    name="SMA 30",
                    line=dict(color='blue', width=1)
                ),
                row=1, col=1
            )
        
        # Volume chart
        colors = ['red' if x else 'green' for x in data.get('volume_anomaly', [False] * len(data))]
        
        fig.add_trace(
            go.Bar(
                x=data['timestamp'],
                y=data['volume'],
                name="Volume",
                marker_color=colors
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            title=f"{coin.upper()} OHLCV Chart",
            xaxis_rangeslider_visible=False,
            height=600
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Additional charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Volatility chart
            if 'volatility' in data.columns:
                fig_vol = go.Figure()
                fig_vol.add_trace(
                    go.Scatter(
                        x=data['timestamp'],
                        y=data['volatility'],
                        name="Volatility",
                        line=dict(color='purple')
                    )
                )
                fig_vol.update_layout(
                    title="Volatility",
                    xaxis_title="Time",
                    yaxis_title="Volatility"
                )
                st.plotly_chart(fig_vol, use_container_width=True)
        
        with col2:
            # RSI chart
            if 'rsi' in data.columns:
                fig_rsi = go.Figure()
                fig_rsi.add_trace(
                    go.Scatter(
                        x=data['timestamp'],
                        y=data['rsi'],
                        name="RSI",
                        line=dict(color='orange')
                    )
                )
                fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought")
                fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold")
                fig_rsi.update_layout(
                    title="RSI",
                    xaxis_title="Time",
                    yaxis_title="RSI",
                    yaxis=dict(range=[0, 100])
                )
                st.plotly_chart(fig_rsi, use_container_width=True)
    
    def _render_anomalies(self, coin: str):
        """Render anomaly detection results"""
        st.header("🔍 Anomaly Detection")
        
        # Get anomaly summary
        summary = self.anomaly_detector.get_anomaly_summary(coin)
        
        if summary['total_anomalies'] == 0:
            st.success("No anomalies detected! 🎉")
            return
        
        # Anomaly summary cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Anomalies", summary['total_anomalies'])
        
        with col2:
            st.metric("Volume Anomalies", summary['by_type'].get('volume', 0))
        
        with col3:
            st.metric("Price Anomalies", summary['by_type'].get('price', 0))
        
        with col4:
            st.metric("Volatility Anomalies", summary['by_type'].get('volatility', 0))
        
        # Recent anomalies table
        st.subheader("Recent Anomalies")
        if summary['recent_anomalies']:
            anomalies_df = pd.DataFrame(summary['recent_anomalies'])
            st.dataframe(anomalies_df, use_container_width=True)
        
        # Anomaly trends
        trends = self.anomaly_detector.get_anomaly_trends(coin)
        if 'daily_anomaly_counts' in trends:
            st.subheader("Anomaly Trends")
            daily_counts = trends['daily_anomaly_counts']
            if daily_counts:
                fig = go.Figure()
                fig.add_trace(
                    go.Bar(
                        x=list(daily_counts.keys()),
                        y=list(daily_counts.values()),
                        name="Daily Anomalies"
                    )
                )
                fig.update_layout(
                    title="Anomalies Over Time",
                    xaxis_title="Date",
                    yaxis_title="Number of Anomalies"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    def _render_metrics(self, data: pd.DataFrame, coin: str):
        """Render financial metrics"""
        st.header("📈 Financial Metrics")
        
        # Get summary statistics
        stats = self.metrics_calculator.get_summary_statistics(data)
        
        if 'error' in stats:
            st.error(stats['error'])
            return
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if 'price' in stats:
                current_price = stats['price'].get('current', 0)
                st.metric("Current Price", f"${current_price:,.2f}")
        
        with col2:
            if 'volatility' in stats:
                current_vol = stats['volatility'].get('current', 0)
                st.metric("Current Volatility", f"{current_vol:.4f}")
        
        with col3:
            if 'volume' in stats:
                current_vol = stats['volume'].get('current', 0)
                st.metric("Current Volume", f"{current_vol:,.0f}")
        
        with col4:
            if 'returns' in stats:
                mean_return = stats['returns'].get('mean', 0)
                st.metric("Mean Return", f"{mean_return:.4f}")
        
        # Detailed statistics
        st.subheader("Detailed Statistics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if 'price' in stats:
                st.write("**Price Statistics**")
                price_stats = stats['price']
                for key, value in price_stats.items():
                    if isinstance(value, float):
                        st.write(f"{key.title()}: ${value:,.2f}")
                    else:
                        st.write(f"{key.title()}: {value}")
        
        with col2:
            if 'volume' in stats:
                st.write("**Volume Statistics**")
                volume_stats = stats['volume']
                for key, value in volume_stats.items():
                    if isinstance(value, float):
                        st.write(f"{key.title()}: {value:,.0f}")
                    else:
                        st.write(f"{key.title()}: {value}")
        
        # Data quality
        st.subheader("Data Quality")
        if 'data_quality' in stats:
            quality = stats['data_quality']
            st.write(f"**Total Records:** {quality.get('total_records', 0)}")
            
            if 'date_range' in quality:
                date_range = quality['date_range']
                st.write(f"**Date Range:** {date_range.get('start')} to {date_range.get('end')}")
    
    def _render_ai_insights(self, data: pd.DataFrame, coin: str):
        """Render AI-powered insights"""
        st.header("🤖 AI Insights")
        
        st.info("AI insights feature will be implemented in the next phase with GPT integration.")
        
        # Placeholder for AI insights
        st.write("**Coming Soon:**")
        st.write("- Natural language queries about market data")
        st.write("- Automated market analysis and insights")
        st.write("- Trading recommendations based on patterns")
        st.write("- Risk assessment and alerts")
        
        # Sample query interface
        st.subheader("Sample Queries")
        sample_queries = [
            f"What's {coin.upper()}'s volatility trend?",
            f"Show me {coin.upper()}'s price anomalies",
            f"Analyze {coin.upper()}'s volume patterns",
            f"What are the key metrics for {coin.upper()}?"
        ]
        
        for query in sample_queries:
            st.write(f"• {query}")

def main():
    """Main function to run the dashboard"""
    dashboard = StreamlitDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()
