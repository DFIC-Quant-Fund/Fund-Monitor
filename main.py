import streamlit as st
import pandas as pd
import os

# Import ReturnsCalculator directly since we're in the same directory
from legacy.performance.returns_calculator import ReturnsCalculator

st.set_page_config(
    page_title="DFIC Fund Monitor",
    layout="wide"
)

st.title("📊 DFIC Fund Monitor")
st.markdown("### Portfolio Performance & Analysis Dashboard")

# Quick overview section
st.header("🏠 Welcome")
st.write("""
This dashboard provides comprehensive analysis of your portfolio performance, holdings, and risk metrics.
Use the sidebar to navigate between different views and analysis tools.
""")

# Portfolio selector (shared across pages)
st.header("📁 Portfolio Selection")
data_dir = os.path.join("legacy", "data")
if os.path.exists(data_dir):
    folders = [f for f in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, f))]
    if folders:
        selected_portfolio = st.selectbox("Select Portfolio", folders)
        st.success(f"Selected portfolio: **{selected_portfolio}**")
        
        # Store in session state for other pages to use
        st.session_state['selected_portfolio'] = selected_portfolio
        
        # Quick stats preview
        output_folder = os.path.join(data_dir, selected_portfolio, 'output')
        portfolio_csv = os.path.join(output_folder, 'portfolio_total.csv')
        
        if os.path.exists(portfolio_csv):
            calc = ReturnsCalculator(output_folder)
            df = calc.df
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Latest Value", f"${df['Total_Portfolio_Value'].iloc[-1]:,.0f}")
            with col2:
                st.metric("Data Points", len(df))
            with col3:
                st.metric("Date Range", f"{df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}")
            with col4:
                total_return = calc.total_return()
                st.metric("Total Return", f"{total_return:.2%}")
    else:
        st.error("No portfolio folders found in data directory")
else:
    st.error("Data directory not found") 