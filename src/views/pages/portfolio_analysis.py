"""
Portfolio Analysis Page - Example of using modular components in a separate page.

This demonstrates how to create additional pages using the same UI components
for consistency and maintainability.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Import controller
from src.controllers.portfolio_controller import PortfolioController

# Import UI components
from src.views.components import (
    render_portfolio_summary,
    render_holdings_summary,
    render_allocation_summary,
    render_performance_summary
)

def render_portfolio_analysis_page():
    """Render the portfolio analysis page"""
    st.title("🔍 Portfolio Analysis")
    st.markdown("---")
    
    # Portfolio selection
    controller = PortfolioController("core")
    available_portfolios = controller.get_available_portfolios()
    
    if not available_portfolios:
        st.error("No portfolios found.")
        return
    
    selected_portfolio = st.sidebar.selectbox(
        "Select Portfolio",
        available_portfolios,
        index=0
    )
    
    # Create controller for selected portfolio
    portfolio_controller = PortfolioController(selected_portfolio)
    
    # Date range selection
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=30),
            max_value=datetime.now()
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.now(),
            max_value=datetime.now()
        )
    
    # Load data
    try:
        portfolio_summary = portfolio_controller.get_portfolio_summary(end_date.strftime('%Y-%m-%d'))
        holdings_data = portfolio_controller.get_holdings_data(end_date.strftime('%Y-%m-%d'))
        performance_data = portfolio_controller.get_performance_metrics(end_date.strftime('%Y-%m-%d'))
        cash_data = portfolio_controller.get_cash_data(end_date.strftime('%Y-%m-%d'))
        total_portfolio_value = portfolio_controller.get_total_portfolio_value(end_date.strftime('%Y-%m-%d'))
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return
    
    # Analysis tabs
    tab1, tab2, tab3 = st.tabs(["📊 Summary", "📈 Holdings Analysis", "🎯 Performance Analysis"])
    
    with tab1:
        st.header("Portfolio Summary Analysis")
        
        # Use components for consistent UI
        render_portfolio_summary(portfolio_summary, total_portfolio_value)
        render_holdings_summary(holdings_data)
        
        # Additional analysis specific to this page
        st.subheader("Portfolio Health Indicators")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Concentration risk
            top_5_weight = holdings_data.head(5)['market_value'].sum() / holdings_data['market_value'].sum() * 100
            st.metric("Top 5 Concentration", f"{top_5_weight:.1f}%")
        
        with col2:
            # Cash ratio
            cash_ratio = cash_data['Total_CAD'] / total_portfolio_value * 100
            st.metric("Cash Ratio", f"{cash_ratio:.1f}%")
        
        with col3:
            # Number of sectors
            num_sectors = holdings_data['sector'].nunique()
            st.metric("Sectors Held", num_sectors)
    
    with tab2:
        st.header("Holdings Analysis")
        
        # Sector analysis
        st.subheader("Sector Analysis")
        sector_analysis = holdings_data.groupby('sector').agg({
            'market_value': ['sum', 'count'],
            'price': 'mean'
        }).round(2)
        
        sector_analysis.columns = ['Total Value', 'Number of Positions', 'Average Price']
        sector_analysis['Weight %'] = (sector_analysis['Total Value'] / sector_analysis['Total Value'].sum() * 100).round(2)
        
        st.dataframe(sector_analysis, use_container_width=True)
        
        # Geographic analysis
        st.subheader("Geographic Analysis")
        geo_analysis = holdings_data.groupby('geography').agg({
            'market_value': ['sum', 'count']
        }).round(2)
        
        geo_analysis.columns = ['Total Value', 'Number of Positions']
        geo_analysis['Weight %'] = (geo_analysis['Total Value'] / geo_analysis['Total Value'].sum() * 100).round(2)
        
        st.dataframe(geo_analysis, use_container_width=True)
    
    with tab3:
        st.header("Performance Analysis")
        
        # Use performance component
        render_performance_summary(performance_data)
        
        # Additional performance analysis
        if performance_data and 'performance' in performance_data:
            st.subheader("Return Analysis")
            
            perf = performance_data['performance']
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if 'one_month' in perf and perf['one_month'] is not None:
                    st.metric("1 Month Return", f"{perf['one_month']:.2f}%")
            
            with col2:
                if 'one_year' in perf and perf['one_year'] is not None:
                    st.metric("1 Year Return", f"{perf['one_year']:.2f}%")
            
            with col3:
                if 'inception' in perf and perf['inception'] is not None:
                    st.metric("Inception Return", f"{perf['inception']:.2f}%")

if __name__ == "__main__":
    render_portfolio_analysis_page()
