"""
Holdings Table Component - Reusable UI component for displaying portfolio holdings.

This component displays:
- Holdings table with ticker, shares, price, market value, weight
- Sector and fund information
- Formatted display with proper number formatting
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any

def render_holdings_table(holdings_data: pd.DataFrame, equity_value: float):
    """
    Render the holdings table with proper formatting.
    
    Args:
        holdings_data: DataFrame containing holdings information
        equity_value: Total equity value for weight calculations
    """
    st.header("Portfolio Holdings")
    
    if not holdings_data.empty:
        # Calculate equity weights
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

def render_holdings_summary(holdings_data: pd.DataFrame):
    """
    Render a summary of holdings statistics.
    
    Args:
        holdings_data: DataFrame containing holdings information
    """
    if not holdings_data.empty:
        st.subheader("Holdings Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_holdings = len(holdings_data)
            st.metric("Total Positions", total_holdings)
        
        with col2:
            avg_position_size = holdings_data['market_value'].mean()
            st.metric("Avg Position Size", f"${avg_position_size:,.0f}")
        
        with col3:
            largest_position = holdings_data.iloc[0]['market_value']
            st.metric("Largest Position", f"${largest_position:,.0f}")
        
        with col4:
            smallest_position = holdings_data.iloc[-1]['market_value']
            st.metric("Smallest Position", f"${smallest_position:,.0f}")
        
        st.markdown("---")
