"""
Holdings Table Component - Reusable UI component for displaying portfolio holdings.
"""

import streamlit as st
import pandas as pd

def render_holdings_table(holdings_data: pd.DataFrame, equity_value: float):
    st.header("Portfolio Holdings")
    if not holdings_data.empty:
        display_data = holdings_data.copy()
        # Ensure numeric current_price column exists (fallback to price if needed)
        if 'current_price' not in display_data.columns and 'price' in display_data.columns:
            display_data['current_price'] = display_data['price']

        # Select columns to show (keep numeric types for proper sorting)
        cols = ['ticker', 'currency', 'shares', 'holding_weight', 'dividends_to_date', 'current_price', 'avg_purchase_price', 'market_value', 'book_value', 'pnl', 'pnl_percent']
        if 'sector' in display_data.columns: cols.append('sector')
        if 'fund' in display_data.columns: cols.append('fund')
        # Filter to available columns
        cols = [c for c in cols if c in display_data.columns]
        df_show = display_data[cols].rename(columns={
            'ticker': 'Ticker',
            'shares': 'Shares',
            'holding_weight': 'Weight (%)',
            'currency': 'Currency',
            'dividends_to_date': 'Dividends to Date ($)',
            'current_price': 'Current Price ($)',
            'avg_purchase_price': 'Avg Purchase ($)',
            'market_value': 'Market Value ($)',
            'book_value': 'Book Value ($)',
            'pnl': 'PnL ($)',
            'pnl_percent': 'PnL (%)',
            'sector': 'Sector',
            'fund': 'Fund'
        })
        # Scale percentage columns for display while retaining numeric types
        if 'PnL (%)' in df_show.columns:
            df_show['PnL (%)'] = df_show['PnL (%)'] * 100.0
        # Use column_config to format while retaining numeric dtype for correct sorting
        st.dataframe(
            df_show,
            use_container_width=True,
            column_config={
                'Currency': st.column_config.TextColumn('Currency'),
                'Shares': st.column_config.NumberColumn('Shares', format='%d'),
                'Weight (%)': st.column_config.NumberColumn('Weight (%)', format='%.2f%%'),
                'Dividends to Date ($)': st.column_config.NumberColumn('Dividends to Date ($)', format='$%d'),
                'Current Price ($)': st.column_config.NumberColumn('Current Price ($)', format='$%.2f'),
                'Avg Purchase ($)': st.column_config.NumberColumn('Avg Purchase ($)', format='$%.2f'),
                'Market Value ($)': st.column_config.NumberColumn('Market Value ($)', format='$%d'),
                'Book Value ($)': st.column_config.NumberColumn('Book Value ($)', format='$%d'),
                'PnL ($)': st.column_config.NumberColumn('PnL ($)', format='$%d'),
                'PnL (%)': st.column_config.NumberColumn('PnL (%)', format='%.2f%%'),
                'Weight (%)': st.column_config.NumberColumn('Weight (%)', format='%.2f%%'),
            }
        )
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


