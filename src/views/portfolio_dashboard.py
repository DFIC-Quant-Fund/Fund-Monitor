"""
Portfolio Dashboard View - Streamlit interface for portfolio analysis.

This view demonstrates the new architecture:
- Direct DataFrame access from controllers
- Cached data loading
- Clean separation of concerns
- Efficient data serving
"""

import streamlit as st
import plotly.express as px
from datetime import datetime
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.controllers.portfolio_controller import PortfolioController

class PortfolioDashboard:
    """Main dashboard view for portfolio analysis"""
    
    def __init__(self):
        self.portfolio_controller = None
        self.portfolio_name = None
    
    def setup_page(self):
        """Setup Streamlit page configuration"""
        st.set_page_config(
            page_title="DFIC Fund Monitor",
            page_icon="📈",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        st.title("📈 DFIC Fund Monitor")
        st.markdown("---")
    
    def setup_sidebar(self):
        """Setup sidebar with portfolio selection and controls"""
        st.sidebar.header("Portfolio Selection")
        
        # Get available portfolios
        controller = PortfolioController("core")  # Temporary for getting portfolio list
        available_portfolios = controller.get_available_portfolios()
        
        if not available_portfolios:
            st.sidebar.error("No portfolios found. Please run portfolio data build first.")
            return False
        
        # Portfolio selection
        self.portfolio_name = st.sidebar.selectbox(
            "Select Portfolio",
            available_portfolios,
            index=0
        )
        
        # Initialize controller for selected portfolio
        self.portfolio_controller = PortfolioController(self.portfolio_name)
        
        # Date selection
        st.sidebar.header("Date Selection")
        as_of_date = st.sidebar.date_input(
            "As of Date",
            value=datetime.now().date(),
            max_value=datetime.now().date()
        )
        
        # Cache controls
        st.sidebar.header("Cache Management")
        if st.sidebar.button("Clear Cache"):
            self.portfolio_controller.clear_cache()
            st.sidebar.success("Cache cleared!")
        
        # Show cache info
        cache_info = self.portfolio_controller.get_cache_info()
        if cache_info:
            st.sidebar.subheader("Cache Status")
            for key, info in cache_info.items():
                st.sidebar.text(f"{key}: {info['age_minutes']:.1f}min old")
        
        return str(as_of_date)
    
    def display_portfolio_summary(self, as_of_date: str):
        """Display portfolio summary metrics"""
        st.header("📊 Portfolio Summary")
        
        try:
            summary = self.portfolio_controller.get_portfolio_summary(as_of_date)
            
            # Create metrics columns
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Holdings Value",
                    f"${summary['total_holdings_value']:,.2f}",
                    help="Total market value of all holdings (excluding cash)"
                )
            
            with col2:
                st.metric(
                    "Total Holdings",
                    f"{summary['total_holdings']}",
                    help="Number of different securities held"
                )
            
            with col3:
                st.metric(
                    "Largest Position",
                    f"{summary['largest_position_ticker']}",
                    f"{summary['largest_position_weight']:.1f}%",
                    help="Largest position by market value"
                )
            
            with col4:
                st.metric(
                    "As of Date",
                    summary['as_of_date'],
                    help="Date of the data shown"
                )

            st.markdown("---")
            st.subheader("🔎 Breakdown")
            h1, h2, h3 = st.columns(3)
            with h1:
                st.metric("CAD Holdings MV", f"${summary['cad_holdings_mv']:,.0f}")
            with h2:
                st.metric("USD Holdings MV", f"${summary['usd_holdings_mv']:,.0f}")
            with h3:
                st.metric("Total Cash (CAD)", f"${summary['total_cash_cad']:,.0f}")

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("CAD Cash", f"${summary['cad_cash']:,.0f}")
            with c2:
                st.metric("USD Cash", f"${summary['usd_cash']:,.0f}")
            with c3:
                st.metric("Holdings + Cash", f"${summary['total_portfolio_value']:,.0f}")
                
        except Exception as e:
            st.error(f"Error loading portfolio summary: {e}")
    
    def display_holdings_table(self, as_of_date: str):
        """Display holdings table"""
        st.header("📋 Current Holdings")
        
        try:
            holdings_df = self.portfolio_controller.get_holdings_data(as_of_date)
            
            if holdings_df.empty:
                st.warning("No holdings data available for the selected date.")
                return
            
            # Format the DataFrame for display
            display_df = holdings_df.copy()
            display_df['market_value'] = display_df['market_value'].apply(lambda x: f"${x:,.2f}")
            display_df['price'] = display_df['price'].apply(lambda x: f"${x:.2f}")
            display_df['shares'] = display_df['shares'].apply(lambda x: f"{x:,.0f}")
            display_df['weight_percent'] = display_df['weight_percent'].apply(lambda x: f"{x:.1f}%")
            
            # Rename columns for display
            display_df = display_df.rename(columns={
                'ticker': 'Ticker',
                'shares': 'Shares',
                'price': 'Price',
                'market_value': 'Market Value',
                'weight_percent': 'Weight %',
                'sector': 'sector',
                'geography': 'Geography'
            })
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
            
        except Exception as e:
            st.error(f"Error loading holdings data: {e}")
    
    def display_performance_metrics(self, as_of_date: str):
        """Display performance metrics"""
        st.header("📈 Performance Metrics")
        
        try:
            metrics = self.portfolio_controller.get_performance_metrics(as_of_date)
            
            # Performance metrics
            st.subheader("Returns")
            performance = metrics['performance']
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("1 Day", f"{(performance.get('one_day') or 0):.2f}%")
            with col2:
                st.metric("1 Week", f"{(performance.get('one_week') or 0):.2f}%")
            with col3:
                st.metric("1 Month", f"{(performance.get('one_month') or 0):.2f}%")
            with col4:
                st.metric("1 Year", f"{(performance.get('one_year') or 0):.2f}%")
            
            # Risk metrics
            st.subheader("Risk Metrics")
            risk_metrics = metrics['risk_metrics']
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Daily Volatility", f"{risk_metrics.get('daily_volatility', 0)*100:.2f}%")
            with col2:
                st.metric("Annualized Volatility", f"{risk_metrics.get('annualized_volatility', 0)*100:.2f}%")
            with col3:
                st.metric("Max Drawdown", f"{risk_metrics.get('maximum_drawdown', 0)*100:.2f}%")
            with col4:
                st.metric("Sharpe Ratio", f"{metrics['ratios'].get('annualized_sharpe_ratio', 0):.2f}")
                
        except Exception as e:
            st.error(f"Error loading performance metrics: {e}")
    
    def display_portfolio_chart(self):
        """Display portfolio value chart"""
        st.header("📊 Portfolio Value Over Time")
        
        try:
            portfolio_df = self.portfolio_controller.get_portfolio_total_data()
            
            if portfolio_df.empty:
                st.warning("No portfolio data available.")
                return
            
            # Create the chart
            fig = px.line(
                portfolio_df,
                x='Date',
                y='Total_Portfolio_Value',
                title='Portfolio Total Value (CAD)',
                labels={'Total_Portfolio_Value': 'Portfolio Value (CAD)', 'Date': 'Date'}
            )
            
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Portfolio Value (CAD)",
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error loading portfolio chart: {e}")
    
    def display_cash_info(self, as_of_date: str):
        """Display cash information"""
        st.header("💰 Cash Information")
        
        try:
            cash_data = self.portfolio_controller.get_cash_data(as_of_date)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "CAD Cash",
                    f"${cash_data['CAD_Cash']:,.2f}",
                    help="Cash balance in Canadian dollars"
                )
            
            with col2:
                st.metric(
                    "USD Cash",
                    f"${cash_data['USD_Cash']:,.2f}",
                    help="Cash balance in US dollars"
                )
            
            with col3:
                st.metric(
                    "Total CAD",
                    f"${cash_data['Total_CAD']:,.2f}",
                    help="Total cash converted to CAD"
                )
                
        except Exception as e:
            st.error(f"Error loading cash data: {e}")
    
    def run(self):
        """Main method to run the dashboard"""
        self.setup_page()
        
        # Setup sidebar and get date
        as_of_date = self.setup_sidebar()
        
        if not self.portfolio_controller:
            st.error("Please select a portfolio from the sidebar.")
            return
        
        # Display dashboard sections
        self.display_portfolio_summary(as_of_date)
        self.display_cash_info(as_of_date)
        
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["Holdings", "Performance", "Charts"])
        
        with tab1:
            self.display_holdings_table(as_of_date)
        
        with tab2:
            self.display_performance_metrics(as_of_date)
        
        with tab3:
            self.display_portfolio_chart()

def main():
    """Main function to run the dashboard"""
    dashboard = PortfolioDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()
