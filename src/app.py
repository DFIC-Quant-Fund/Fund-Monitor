"""
DFIC Fund Monitor - Main Streamlit Application

Simple MVC architecture:
- Models: portfolio_csv_builder.py (data building)
- Controllers: portfolio_controller.py (business logic)
- Views: Streamlit pages (UI) with modular components
"""

import streamlit as st
import pandas as pd
import sys
import os
import traceback

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import controller
from src.controllers.portfolio_controller import PortfolioController

# Import UI components
from src.views import (
    render_portfolio_summary,
    render_portfolio_breakdown,
    render_cash_breakdown,
    render_holdings_table,
    render_allocation_charts,
    render_performance_metrics,
    render_returns_chart
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
    # Default to 'core' if present
    try:
        default_index = [p.lower() for p in available_portfolios].index('core')
    except ValueError:
        default_index = 0
    selected_portfolio = st.sidebar.selectbox(
        "Select Portfolio",
        available_portfolios,
        index=default_index
    )
    
    # Create controller for selected portfolio
    portfolio_controller = PortfolioController(selected_portfolio)
    
    # Check if data files exist
    output_folder = os.path.join("data", selected_portfolio, "output")
    required_files = ['daily_holdings.csv', 'market_values.csv', 'prices.csv']
    missing_files = [f for f in required_files if not os.path.exists(os.path.join(output_folder, f))]
    
    if missing_files:
        st.error(f"Missing required data files for portfolio '{selected_portfolio}': {', '.join(missing_files)}")
        st.info("Please ensure the portfolio data has been built. You may need to run the data building process.")
        return
    
    # Date selection
    try:
        loading_placeholder = st.empty()
        loading_placeholder.info("Loading portfolio data...")
        summary = portfolio_controller.get_portfolio_summary()
        
        # Get the latest available date from portfolio totals for accuracy
        totals_df = portfolio_controller.get_portfolio_total_data()
        latest_date = totals_df['Date'].max() if not totals_df.empty else summary['as_of_date']
        latest_date_date = pd.to_datetime(latest_date).date()
        
        selected_date = st.sidebar.date_input(
            "As of Date",
            value=latest_date_date,
            max_value=latest_date_date,
            min_value=pd.to_datetime('2022-05-01').date()
        )
        # Clear loading message once loaded
        loading_placeholder.empty()
    except Exception as e:
        st.error(f"Error loading portfolio data: {e}")
        st.error(f"Error type: {type(e)}")
        st.error(f"Traceback: {traceback.format_exc()}")
        st.info("This usually means the portfolio data hasn't been built yet. Please ensure the data building process has been completed.")
        return
    
    # Fetch cumulative returns (since inception) and render chart at the top
    try:
        returns_df = portfolio_controller.get_cumulative_returns()
        render_returns_chart(returns_df)
        st.markdown("---")
    except Exception as e:
        st.warning(f"Could not render returns chart: {e}")

    # Load data for selected date
    try:
        portfolio_summary = portfolio_controller.get_portfolio_summary(selected_date.strftime('%Y-%m-%d'))
        holdings_data = portfolio_controller.get_holdings_data()
        # allocations_data = portfolio_controller.get_allocation_data()
        performance_data = portfolio_controller.get_performance_metrics(selected_date.strftime('%Y-%m-%d'))
        # Use cash breakdown from cash.csv and totals from portfolio_total.csv
        cash_data = portfolio_controller.get_cash_data(selected_date.strftime('%Y-%m-%d'))
        total_portfolio_value = portfolio_summary.get('total_portfolio_value', 0.0)
    except Exception as e:
        st.error(f"Error loading data for selected date: {e}")
        return
    
    # Render portfolio summary using components
    render_portfolio_summary(portfolio_summary, total_portfolio_value)
    render_portfolio_breakdown(portfolio_summary, total_portfolio_value, cash_data)
    render_cash_breakdown(cash_data)
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📈 Holdings", "🏭 Allocation", "📊 Performance"])
    
    with tab1:
        # Holdings search
        unique_tickers = sorted(holdings_data['ticker'].unique())
            
        search_col, _ = st.columns([1, 2])
        with search_col:
            selected_tickers = st.multiselect(
                "Search/Filter Tickers",
                options=unique_tickers,
                placeholder="Type ticker symbol..."
            )

        if selected_tickers:
            filtered_holdings = holdings_data[holdings_data['ticker'].isin(selected_tickers)]
        else:
            filtered_holdings = holdings_data

        # Render holdings table using component
        render_holdings_table(filtered_holdings)
    
    with tab2:
        # Render allocation charts using component
        render_allocation_charts(selected_portfolio)
    
    with tab3:
        # Render performance metrics using component
        render_performance_metrics(performance_data)

if __name__ == "__main__":
    main()
