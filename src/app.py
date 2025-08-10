"""
DFIC Fund Monitor - Main Streamlit Application

Simple MVC architecture:
- Models: portfolio_csv_builder.py (data building)
- Controllers: portfolio_controller.py (business logic)
- Views: Streamlit pages (UI) with modular components
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import controller
from src.controllers.portfolio_controller import PortfolioController

# Import UI components
from src.views.components import (
    render_portfolio_summary,
    render_portfolio_breakdown,
    render_cash_breakdown,
    render_holdings_table,
    render_allocation_charts,
    render_performance_metrics
)

# Page configuration
st.set_page_config(
    page_title="DFIC Fund Monitor",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    st.title("📊 DFIC Fund Monitor")
    st.markdown("---")
    
    # Initialize controller
    controller = PortfolioController("core")
    
    # Get available portfolios
    available_portfolios = controller.get_available_portfolios()
    
    if not available_portfolios:
        st.error("No portfolios found. Please ensure data files exist in the data directory.")
        st.info("Expected structure: data/core/output/ (for core portfolio)")
        return
    
    # Portfolio selection
    selected_portfolio = st.sidebar.selectbox(
        "Select Portfolio",
        available_portfolios,
        index=0
    )
    
    # Create controller for selected portfolio
    portfolio_controller = PortfolioController(selected_portfolio)
    
    # Check if data files exist
    output_folder = os.path.join("data", selected_portfolio, "output")
    required_files = ['holdings.csv', 'cad_market_values.csv', 'prices.csv']
    missing_files = [f for f in required_files if not os.path.exists(os.path.join(output_folder, f))]
    
    if missing_files:
        st.error(f"Missing required data files for portfolio '{selected_portfolio}': {', '.join(missing_files)}")
        st.info("Please ensure the portfolio data has been built. You may need to run the data building process.")
        return
    
    # Date selection
    try:
        st.info("Loading portfolio data...")
        summary = portfolio_controller.get_portfolio_summary()
        st.success("Portfolio data loaded successfully!")
        
        # Get the latest available date from the data
        latest_date = summary['as_of_date']
        st.info(f"Latest date from data: {latest_date} (type: {type(latest_date)})")
        
        # Convert to datetime.date for Streamlit
        latest_date_date = latest_date.date() if hasattr(latest_date, 'date') else pd.to_datetime(latest_date).date()
        st.info(f"Converted date: {latest_date_date} (type: {type(latest_date_date)})")
        
        selected_date = st.sidebar.date_input(
            "As of Date",
            value=latest_date_date,
            max_value=latest_date_date,
            min_value=pd.to_datetime('2022-05-01').date()
        )
    except Exception as e:
        st.error(f"Error loading portfolio data: {e}")
        st.error(f"Error type: {type(e)}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        st.info("This usually means the portfolio data hasn't been built yet. Please ensure the data building process has been completed.")
        return
    
    # Load data for selected date
    try:
        portfolio_summary = portfolio_controller.get_portfolio_summary(selected_date.strftime('%Y-%m-%d'))
        holdings_data = portfolio_controller.get_holdings_data(selected_date.strftime('%Y-%m-%d'))
        performance_data = portfolio_controller.get_performance_metrics(selected_date.strftime('%Y-%m-%d'))
        cash_data = portfolio_controller.get_cash_data(selected_date.strftime('%Y-%m-%d'))
        total_portfolio_value = portfolio_controller.get_total_portfolio_value(selected_date.strftime('%Y-%m-%d'))
    except Exception as e:
        st.error(f"Error loading data for selected date: {e}")
        return
    
    # Calculate equity value (sum of all holdings)
    equity_value = portfolio_summary['total_value']
    
    # Render portfolio summary using components
    render_portfolio_summary(portfolio_summary, total_portfolio_value)
    render_portfolio_breakdown(portfolio_summary, total_portfolio_value, cash_data)
    render_cash_breakdown(cash_data)
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📈 Holdings", "🏭 Allocation", "📊 Performance"])
    
    with tab1:
        # Render holdings table using component
        render_holdings_table(holdings_data, equity_value)
    
    with tab2:
        # Render allocation charts using component
        render_allocation_charts(holdings_data)
    
    with tab3:
        # Render performance metrics using component
        render_performance_metrics(performance_data)

if __name__ == "__main__":
    main()
