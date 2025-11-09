"""
Holdings Table Component - Reusable UI component for displaying portfolio holdings.
Updated to optionally split holdings by currency (USD / CAD).
"""

import streamlit as st
import pandas as pd

def _format_currency(value: float, currency: str):
    """Return a formatted string for a value in the specified currency code."""
    if pd.isna(value):
        return ""
    if str(currency).upper() in ("CAD", "C$"):
        return f"C${value:,.2f}"
    # default to USD
    return f"${value:,.2f}"

def _render_grouped_table(df: pd.DataFrame, currency_code: str):
    """Render one grouped holdings table and small summary."""
    if df.empty:
        st.info(f"No holdings for {currency_code}")
        return

    # Prefer market_value_local; fall back to market_value
    mv_col = 'market_value_local' if 'market_value_local' in df.columns else 'market_value'

    equity_value = df[mv_col].sum() if mv_col in df.columns else 0

    display_data = df.copy()
    # Numeric formatting
    display_data['Shares'] = display_data.get('shares', pd.Series(index=display_data.index)).apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
    display_data['Price'] = display_data.get('price', pd.Series(index=display_data.index)).apply(lambda x: _format_currency(x, currency_code) if pd.notna(x) else "")
    display_data['Market Value'] = display_data[mv_col].apply(lambda x: _format_currency(x, currency_code))
    # Weight relative to equity in same currency
    display_data['Weight (%)'] = display_data[mv_col].apply(lambda x: f"{(x / equity_value * 100):.2f}%" if equity_value and pd.notna(x) else "0.00%")

    display_columns = ['ticker', 'Shares', 'Price', 'Market Value', 'Weight (%)', 'sector', 'fund']
    st.subheader(f"Holdings — {currency_code}")
    st.dataframe(
        display_data.reindex(columns=[c for c in display_columns if c in display_data.columns]).rename(
            columns={'ticker': 'Ticker','sector': 'Sector','fund': 'Fund'}
        ),
        use_container_width=True
    )

    # small summary
    col1, col2 = st.columns(2)
    with col1:
        st.metric(f"Total Value ({currency_code})", _format_currency(equity_value, currency_code))
    with col2:
        st.metric(f"Positions ({currency_code})", len(display_data))


def render_holdings_table(holdings_data: pd.DataFrame, equity_value: float, split_by_currency: bool = False):
    """
    Render the holdings table. If split_by_currency is True, shows separate tables for CAD and USD.
    - holdings_data: expected to contain either:
        * a 'currency' column with 'CAD' or 'USD', OR
        * a 'geography' column that allows mapping, AND
        * ideally a 'market_value_local' column.
      If market_value_local is not present, falls back to 'market_value'.
    """
    st.header("Portfolio Holdings")

    if holdings_data is None or holdings_data.empty:
        st.info("No holdings data available")
        return

    df = holdings_data.copy()

    if split_by_currency:
        # Determine currency
        if 'currency' in df.columns:
            df['currency_code'] = df['currency'].astype(str).str.upper()
        elif 'geography' in df.columns:
            def map_geo_to_currency(g):
                if pd.isna(g):
                    return 'USD'
                s = str(g).lower()
                if 'canada' in s or 'canadian' in s or s == 'ca':
                    return 'CAD'
                return 'USD'
            df['currency_code'] = df['geography'].apply(map_geo_to_currency)
        else:
            df['currency_code'] = 'CAD'

        col_left, col_right = st.columns(2)
        with col_left:
            _render_grouped_table(df[df['currency_code'] == 'CAD'], 'CAD')
        with col_right:
            _render_grouped_table(df[df['currency_code'] == 'USD'], 'USD')

        st.info("Showing holdings split by native currency. Weights are relative to equity in each currency.")
    else:
        # Legacy single-table behavior
        display_data = df.copy()
        display_data['equity_weight_percent'] = (display_data.get('market_value', 0) / equity_value * 100) if equity_value > 0 else 0
        display_data['Shares'] = display_data.get('shares', pd.Series(index=display_data.index)).apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
        display_data['Price ($)'] = display_data.get('price', pd.Series(index=display_data.index)).apply(lambda x: f"${x:.2f}" if pd.notna(x) else "")
        display_data['Market Value ($)'] = display_data.get('market_value', pd.Series(index=display_data.index)).apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "")
        display_data['Weight (%)'] = display_data['equity_weight_percent'].apply(lambda x: f"{x:.2f}%")
        display_columns = ['ticker', 'Shares', 'Price ($)', 'Market Value ($)', 'Weight (%)', 'sector', 'fund']
        st.dataframe(display_data[display_columns].rename(columns={'ticker': 'Ticker','sector': 'Sector','fund': 'Fund'}), use_container_width=True)
        st.info("💡 **Note**: Weights shown are relative to equity holdings only (excluding cash).")
