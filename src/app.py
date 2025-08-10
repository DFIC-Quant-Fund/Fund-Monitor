"""
DFIC Fund Monitor - Main Streamlit Application

Simple MVC architecture:
- Models: portfolio_csv_builder.py (data building)
- Controllers: portfolio_controller.py (business logic)
- Views: Streamlit pages (UI)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import controller
from src.controllers.portfolio_controller import PortfolioController

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
    required_files = ['holdings.csv', 'market_values.csv', 'prices.csv']
    missing_files = [f for f in required_files if not os.path.exists(os.path.join(output_folder, f))]
    
    if missing_files:
        st.error(f"Missing required data files for portfolio '{selected_portfolio}': {', '.join(missing_files)}")
        st.info("Please ensure the portfolio data has been built. You may need to run the data building process.")
        return
    
    # Date selection
    try:
        summary = portfolio_controller.get_portfolio_summary()
        # Get the latest available date from the data
        latest_date = summary['as_of_date']
        selected_date = st.sidebar.date_input(
            "As of Date",
            value=latest_date.date(),
            max_value=latest_date.date(),
            min_value=pd.to_datetime('2022-05-01').date()
        )
    except Exception as e:
        st.error(f"Error loading portfolio data: {e}")
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
    
    # Calculate equity value (sum of all holdings) - this is what portfolio_summary['total_value'] contains
    equity_value = portfolio_summary['total_value']
    
    # Main dashboard
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Total Portfolio Value",
            f"${total_portfolio_value:,.0f}",
            help="Total portfolio value including equities, cash, and dividends"
        )
    
    with col2:
        st.metric(
            "Equity Value",
            f"${equity_value:,.0f}",
            help="Total value of equity holdings only"
        )
    
    with col3:
        st.metric(
            "Total Holdings",
            portfolio_summary['total_holdings'],
            help="Number of individual equity positions"
        )
    
    with col4:
        st.metric(
            "Largest Position",
            f"{portfolio_summary['largest_position_ticker']} ({portfolio_summary['largest_position_weight']:.1f}%)",
            help="Largest equity holding by market value"
        )
    
    with col5:
        st.metric(
            "As of Date",
            portfolio_summary['as_of_date'].strftime('%Y-%m-%d'),
            help="Date of portfolio snapshot"
        )
    
    st.markdown("---")
    
    # Portfolio Breakdown Section
    st.subheader("📊 Portfolio Breakdown")
    breakdown_col1, breakdown_col2, breakdown_col3, breakdown_col4 = st.columns(4)
    
    with breakdown_col1:
        equity_weight = (equity_value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
        st.metric(
            "Equity Allocation",
            f"{equity_weight:.1f}%",
            help="Percentage of portfolio in equities"
        )
    
    with breakdown_col2:
        cash_weight = (cash_data['Total_CAD'] / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
        st.metric(
            "Cash Allocation",
            f"{cash_weight:.1f}%",
            help="Percentage of portfolio in cash"
        )
    
    with breakdown_col3:
        st.metric(
            "Equity Value",
            f"${equity_value:,.0f}",
            help="Total value of equity holdings"
        )
    
    with breakdown_col4:
        st.metric(
            "Cash Value",
            f"${cash_data['Total_CAD']:,.0f}",
            help="Total cash balance in CAD"
        )
    
    # Add note about total portfolio value
    st.info("💡 **Note**: Total portfolio value includes equities, cash, and cumulative dividends.")
    
    st.markdown("---")
    
    # Cash breakdown
    if cash_data['CAD_Cash'] > 0 or cash_data['USD_Cash'] > 0:
        st.subheader("💰 Cash Breakdown")
        cash_col1, cash_col2, cash_col3 = st.columns(3)
        
        with cash_col1:
            st.metric(
                "CAD Cash",
                f"${cash_data['CAD_Cash']:,.2f}",
                help="Canadian dollar cash balance"
            )
        
        with cash_col2:
            st.metric(
                "USD Cash",
                f"${cash_data['USD_Cash']:,.2f}",
                help="US dollar cash balance"
            )
        
        with cash_col3:
            st.metric(
                "Total Cash (CAD)",
                f"${cash_data['Total_CAD']:,.2f}",
                help="Total cash converted to CAD"
            )
    
    st.markdown("---")
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📈 Holdings", "🏭 Allocation", "📊 Performance"])
    
    with tab1:
        st.header("Portfolio Holdings")
        
        if not holdings_data.empty:
            # Use the same equity value for consistency
            equity_value = portfolio_summary['total_value']
            holdings_data['equity_weight_percent'] = (holdings_data['market_value'] / equity_value * 100) if equity_value > 0 else 0
            
            # Format holdings for display
            display_data = holdings_data.copy()
            display_data['Shares'] = display_data['shares'].apply(lambda x: f"{x:,.0f}")
            display_data['Price ($)'] = display_data['price'].apply(lambda x: f"${x:.2f}")
            display_data['Market Value ($)'] = display_data['market_value'].apply(lambda x: f"${x:,.0f}")
            display_data['Weight (%)'] = display_data['equity_weight_percent'].apply(lambda x: f"{x:.2f}%")
            
            # Select columns for display
            display_columns = ['ticker', 'Shares', 'Price ($)', 'Market Value ($)', 'Weight (%)', 'sector', 'fund']
            st.dataframe(display_data[display_columns].rename(columns={
                'ticker': 'Ticker',
                'sector': 'Sector',
                'fund': 'Fund'
            }), use_container_width=True)
            
            # Add note about weights
            st.info("💡 **Note**: Weights shown are relative to equity holdings only (excluding cash).")
        else:
            st.info("No holdings data available")
    
    with tab2:
        st.header("Portfolio Allocation")
        
        if not holdings_data.empty:
            # Use the same equity value for consistency
            equity_value = portfolio_summary['total_value']
            holdings_data['equity_weight_percent'] = (holdings_data['market_value'] / equity_value * 100) if equity_value > 0 else 0
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Sector allocation
                sector_data = holdings_data.groupby('sector')['equity_weight_percent'].sum().reset_index()
                if not sector_data.empty:
                    fig_sector = px.pie(
                        sector_data,
                        values='equity_weight_percent',
                        names='sector',
                        title="Sector Allocation (Equity Only)"
                    )
                    st.plotly_chart(fig_sector, use_container_width=True)
                
                # Fund allocation
                fund_data = holdings_data.groupby('fund')['equity_weight_percent'].sum().reset_index()
                if not fund_data.empty:
                    fig_fund = px.pie(
                        fund_data,
                        values='equity_weight_percent',
                        names='fund',
                        title="Fund Allocation (Equity Only)"
                    )
                    st.plotly_chart(fig_fund, use_container_width=True)
            
            with col2:
                # Geographic allocation
                geo_data = holdings_data.groupby('geography')['equity_weight_percent'].sum().reset_index()
                if not geo_data.empty:
                    fig_geo = px.pie(
                        geo_data,
                        values='equity_weight_percent',
                        names='geography',
                        title="Geographic Allocation (Equity Only)"
                    )
                    st.plotly_chart(fig_geo, use_container_width=True)
                
                # Add note about allocation charts
                st.info("💡 **Note**: Allocation charts show equity holdings only (excluding cash).")
        else:
            st.info("No allocation data available")
    
    with tab3:
        st.header("Performance Metrics")
        
        if performance_data:
            # Performance returns
            if 'performance' in performance_data:
                st.subheader("Period Returns")
                perf_data = performance_data['performance']
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if 'one_day' in perf_data and perf_data['one_day'] is not None:
                        st.metric("1 Day", f"{perf_data['one_day']:.2f}%")
                    if 'one_week' in perf_data and perf_data['one_week'] is not None:
                        st.metric("1 Week", f"{perf_data['one_week']:.2f}%")
                
                with col2:
                    if 'one_month' in perf_data and perf_data['one_month'] is not None:
                        st.metric("1 Month", f"{perf_data['one_month']:.2f}%")
                    if 'ytd' in perf_data and perf_data['ytd'] is not None:
                        st.metric("YTD", f"{perf_data['ytd']:.2f}%")
                
                with col3:
                    if 'one_year' in perf_data and perf_data['one_year'] is not None:
                        st.metric("1 Year", f"{perf_data['one_year']:.2f}%")
                    if 'inception' in perf_data and perf_data['inception'] is not None:
                        st.metric("Inception", f"{perf_data['inception']:.2f}%")
            
            # Risk metrics
            if 'risk_metrics' in performance_data:
                st.subheader("Risk Metrics")
                risk_data = performance_data['risk_metrics']
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if 'daily_volatility' in risk_data:
                        st.metric("Daily Volatility", f"{risk_data['daily_volatility']:.4f}")
                    if 'annualized_volatility' in risk_data:
                        st.metric("Annualized Volatility", f"{risk_data['annualized_volatility']:.4f}")
                
                with col2:
                    if 'maximum_drawdown' in risk_data:
                        st.metric("Max Drawdown", f"{risk_data['maximum_drawdown']:.4f}")
                    if 'daily_downside_volatility' in risk_data:
                        st.metric("Downside Volatility", f"{risk_data['daily_downside_volatility']:.4f}")
                
                with col3:
                    if 'annualized_downside_volatility' in risk_data:
                        st.metric("Annualized Downside Vol", f"{risk_data['annualized_downside_volatility']:.4f}")
            
            # Ratios
            if 'ratios' in performance_data:
                st.subheader("Risk-Adjusted Ratios")
                ratios_data = performance_data['ratios']
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if 'annualized_sharpe_ratio' in ratios_data:
                        st.metric("Sharpe Ratio", f"{ratios_data['annualized_sharpe_ratio']:.3f}")
                
                with col2:
                    if 'annualized_sortino_ratio' in ratios_data:
                        st.metric("Sortino Ratio", f"{ratios_data['annualized_sortino_ratio']:.3f}")
                
                with col3:
                    if 'annualized_information_ratio' in ratios_data:
                        st.metric("Information Ratio", f"{ratios_data['annualized_information_ratio']:.3f}")
            
            # Market metrics
            if 'market_metrics' in performance_data:
                st.subheader("Market Comparison")
                market_data = performance_data['market_metrics']
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if 'beta' in market_data:
                        st.metric("Beta", f"{market_data['beta']:.3f}")
                
                with col2:
                    if 'alpha' in market_data:
                        st.metric("Alpha", f"{market_data['alpha']:.4f}")
                
                with col3:
                    if 'risk_premium' in market_data:
                        st.metric("Risk Premium", f"{market_data['risk_premium']:.4f}")
        else:
            st.info("Performance data not available")

if __name__ == "__main__":
    main()
