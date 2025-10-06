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
        # Auto-refresh UI to pick latest DB rows (does not call external APIs)
        try:
            from streamlit_autorefresh import st_autorefresh as _st_autorefresh
            _st_autorefresh(interval=60000, key="auto_refresh")
        except Exception:
            # If optional dependency not installed, skip auto-refresh
            pass
        
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
        
        # Freshness bar: show last ingested time and manual refresh
        top_col1, top_col2, top_col3 = st.columns([2,1,1])
        with top_col1:
            last_updated = self._get_last_updated()
            st.caption(f"Last updated: {last_updated if last_updated else 'N/A'}")
        with top_col2:
            refresh_now = st.button("Refresh now (30d / 4H)")
        with top_col3:
            st.caption("Auto refresh: 60s")
        
        if refresh_now:
            self._refresh_ohlc_30d(coin)
        
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
    
    def _get_last_updated(self) -> str:
        """Get last ingested timestamp from ETL logs"""
        try:
            logs = self.db_connection.get_etl_logs(limit=1)
            if logs:
                return logs[0].get('timestamp')
        except Exception as e:
            logger.error(f"Error fetching last updated: {e}")
        return ""
    
    def _attempt_refresh(self):
        """Attempt to refresh pipeline run with 5-min backoff"""
        import subprocess, time
        
        # Check last run
        try:
            logs = self.db_connection.get_etl_logs(limit=1)
            if logs:
                last_ts = pd.to_datetime(logs[0].get('timestamp'))
                if (pd.Timestamp.utcnow() - last_ts) < pd.Timedelta(minutes=5):
                    st.warning("Recent run detected. Please try again in a few minutes.")
                    return
        except Exception:
            pass
        
        try:
            subprocess.Popen(["python", "-m", "src.main"])  # fallback full pipeline
            st.info("Full refresh started. This may take ~10–20s.")
        except Exception as e:
            st.error(f"Failed to start full refresh: {e}")

    def _refresh_ohlc_30d(self, coin: str):
        """Fetch last 30d OHLC (4H) from CoinGecko and replace this coin's rows"""
        import pandas as pd
        from ingestion.coingecko_client import CoinGeckoClient
        try:
            client = CoinGeckoClient()
            raw = client.get_ohlcv_data(coin_id=coin, days=30)
            if not raw:
                st.warning("No OHLC data returned.")
                return
            df = pd.DataFrame(raw, columns=['timestamp','open','high','low','close'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_convert(None)

            # Fetch coin volume from market_chart/range over same 30d window and resample to 4H sums
            try:
                end_ts = int(pd.Timestamp.utcnow().timestamp())
                start_ts = end_ts - 30 * 24 * 3600
                range_payload = client.get_coin_price_history_range(coin, vs_currency="usd", from_ts=start_ts, to_ts=end_ts)
                vol_points = range_payload.get('total_volumes', []) if range_payload else []
                if vol_points:
                    vdf = pd.DataFrame(vol_points, columns=['timestamp','volume'])
                    vdf['timestamp'] = pd.to_datetime(vdf['timestamp'], unit='ms', utc=True).dt.tz_convert(None)
                    vdf = vdf.set_index('timestamp').sort_index()
                    vdf_4h = vdf.resample('4h', label='right', closed='right').sum().reset_index()
                    df = df.merge(vdf_4h, on='timestamp', how='left')
                else:
                    df['volume'] = 0.0
            except Exception:
                df['volume'] = 0.0
            df['volume'] = df['volume'].fillna(0.0)
            df['coin'] = coin
            # purge and insert
            self.db_connection.execute_update("DELETE FROM ohlcv WHERE coin = ?", (coin,))
            self.db_connection.insert_ohlcv_data(df[['coin','timestamp','open','high','low','close','volume']].to_dict('records'))
            self.db_connection.insert_etl_log(coin=coin, status='success', message=f'refresh_30d_4h: {len(df)} rows', records_processed=len(df))
            st.success("Refreshed 30d (4H) OHLC. Data will update on next auto-refresh.")
        except Exception as e:
            st.error(f"Refresh failed: {e}")
    
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
        
        # Volume chart (may be all zeros if OHLC endpoint used)
        if 'volume' in data.columns:
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
        else:
            fig.update_yaxes(visible=False, row=2, col=1)
            fig.update_xaxes(visible=False, row=2, col=1)
        
        fig.update_layout(
            title=f"{coin.upper()} OHLCV Chart",
            xaxis_rangeslider_visible=False,
            height=600
        )
        
        st.plotly_chart(fig, config={"responsive": True, "displaylogo": False})
        
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
                st.plotly_chart(fig_vol, config={"responsive": True, "displaylogo": False})
        
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
                st.plotly_chart(fig_rsi, config={"responsive": True, "displaylogo": False})
    
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
                st.plotly_chart(fig, config={"responsive": True, "displaylogo": False})
    
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
        
        # Lazy import to avoid hard dependency when key is missing
        try:
            try:
                from llm.gpt_client import GPTClient
            except ImportError:
                from ..llm.gpt_client import GPTClient
        except Exception as _e:
            st.warning("GPT client unavailable. Check installation.")
            return
        
        # Build a lightweight data summary for the model
        summary = {}
        try:
            if not data.empty:
                summary = {
                    "coin": coin,
                    "records": int(len(data)),
                    "start": str(data['timestamp'].iloc[0]),
                    "end": str(data['timestamp'].iloc[-1]),
                    "last_price": float(data['close'].iloc[-1]),
                }
                if 'volatility' in data.columns:
                    summary["last_volatility"] = float(data['volatility'].iloc[-1])
                if 'rsi' in data.columns:
                    summary["last_rsi"] = float(data['rsi'].iloc[-1])
                if 'sma_7' in data.columns:
                    summary["sma_7"] = float(data['sma_7'].iloc[-1])
                if 'sma_30' in data.columns:
                    summary["sma_30"] = float(data['sma_30'].iloc[-1])
                # Include last 24 four-hour candles for concrete recent context
                recent = data.tail(24)[['timestamp','open','high','low','close']].copy()
                recent['timestamp'] = recent['timestamp'].astype(str)
                summary["recent_ohlc_24x4h"] = [
                    {
                        "t": str(row['timestamp']),
                        "o": float(row['open']),
                        "h": float(row['high']),
                        "l": float(row['low']),
                        "c": float(row['close'])
                    }
                    for _, row in recent.iterrows()
                ]
        except Exception:
            pass
        
        client = None
        try:
            client = GPTClient()
        except Exception as e:
            st.warning("OpenAI client not configured. Set OPENAI_API_KEY to enable AI Insights.")
            return
        
        # Quick health check (non-blocking if it fails)
        healthy = False
        try:
            healthy = client.health_check()
        except Exception:
            healthy = False
        if not healthy:
            st.warning("AI service unavailable right now. Insights may not work.")
        
        # UI: summary + Q&A
        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("Generate market summary"):
                with st.spinner("Generating summary..."):
                    resp = client.generate_market_summary(summary)
                st.markdown(resp)
        with col2:
            question = st.text_area("Ask a question about the data", key="ai_q", height=100, placeholder=f"e.g., What stands out for {coin.upper()} in the last 30 days?")
            if st.button("Analyze question"):
                if not question.strip():
                    st.warning("Please enter a question.")
                else:
                    with st.spinner("Analyzing..."):
                        resp = client.analyze_market_data(summary, question.strip())
                    st.markdown(resp)

def main():
    """Main function to run the dashboard"""
    dashboard = StreamlitDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()
