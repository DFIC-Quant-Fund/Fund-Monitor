"""
Holdings Table Component - Reusable UI component for displaying portfolio holdings.
"""

import streamlit as st
import pandas as pd

def render_holdings_table(holdings_data: pd.DataFrame, equity_value: float):
    st.header("Portfolio Holdings")
    if not holdings_data.empty:
        holdings_data['equity_weight_percent'] = (holdings_data['market_value'] / equity_value * 100) if equity_value > 0 else 0
        display_data = holdings_data.copy()
        display_data['Shares'] = display_data['shares'].apply(lambda x: f"{x:,.0f}")
        display_data['Price ($)'] = display_data['price'].apply(lambda x: f"${x:.2f}")
        display_data['Market Value ($)'] = display_data['market_value'].apply(lambda x: f"${x:,.0f}")
        display_data['Weight (%)'] = display_data['equity_weight_percent'].apply(lambda x: f"{x:.2f}%")
        display_columns = ['ticker', 'Shares', 'Price ($)', 'Market Value ($)', 'Weight (%)', 'sector', 'fund']
        st.dataframe(display_data[display_columns].rename(columns={'ticker': 'Ticker','sector': 'Sector','fund': 'Fund'}), use_container_width=True)
        st.info("💡 **Note**: Weights shown are relative to equity holdings only (excluding cash).")
    else:
        st.info("No holdings data available")

def render_holdings_summary(holdings_data: pd.DataFrame):
    if not holdings_data.empty:
        st.subheader("Holdings Summary")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Positions", len(holdings_data))
        with col2:
            st.metric("Avg Position Size", f"${holdings_data['market_value'].mean():,.0f}")
        with col3:
            st.metric("Largest Position", f"${holdings_data.iloc[0]['market_value']:,.0f}")
        with col4:
            st.metric("Smallest Position", f"${holdings_data.iloc[-1]['market_value']:,.0f}")
        st.markdown("---")


