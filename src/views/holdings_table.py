"""
Holdings Table Component - Reusable UI component for displaying portfolio holdings.
"""

import streamlit as st
import pandas as pd


def render_holdings_table(holdings_data: pd.DataFrame):
    st.header("Portfolio Holdings")

    # Search Holdings
    unique_tickers = sorted(holdings_data["ticker"].unique())

    search_col, _ = st.columns([1, 2])
    with search_col:
        selected_tickers = st.multiselect(
            "Search/Filter Tickers",
            options=unique_tickers,
            placeholder="Type ticker symbol...",
        )

    if selected_tickers:
        display_data = holdings_data[holdings_data["ticker"].isin(selected_tickers)]
    else:
        display_data = holdings_data.copy()

    if not holdings_data.empty:
        # Select columns to show
        cols = [
            "ticker",
            "currency",
            "shares",
            "first_purchase_date",  # ✅ ADDED COLUMN
            "holding_weight",
            "current_price",
            "avg_price",
            "market_value",
            "book_value",
            "dividends",
            "realized_pnl",
            "unrealized_pnl",
            "total_return",
            "total_return_pct",
            "annualized_return_pct",
            "sector",
            "asset_class",
            "status",
        ]

        # Filter to available columns
        cols = [c for c in cols if c in display_data.columns]

        df_show = display_data[cols].rename(
            columns={
                "ticker": "Ticker",
                "currency": "Currency",
                "shares": "Shares",
                "first_purchase_date": "First Purchase Date",  # ✅ RENAME
                "holding_weight": "Weight (%)",
                "current_price": "Price",
                "avg_price": "Avg Cost",
                "market_value": "Market Value",
                "book_value": "Book Value",
                "dividends": "Dividends",
                "realized_pnl": "Realized PnL",
                "unrealized_pnl": "Unrealized PnL",
                "total_return": "Total Return ($)",
                "total_return_pct": "Total Return (%)",
                "annualized_return_pct": "Annualized Return (%)",
                "sector": "Sector",
                "asset_class": "Asset Class",
                "status": "Status",
            }
        )

        # Render table
        st.dataframe(
            df_show,
            use_container_width=True,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker"),
                "Currency": st.column_config.TextColumn("Currency"),
                "Shares": st.column_config.NumberColumn("Shares", format="%.2f"),
                "First Purchase Date": st.column_config.DateColumn(
                    "First Purchase Date"
                ),  # ✅ CONFIG
                "Weight (%)": st.column_config.NumberColumn(
                    "Weight (%)", format="%.2f%%"
                ),
                "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                "Avg Cost": st.column_config.NumberColumn("Avg Cost", format="$%.2f"),
                "Market Value": st.column_config.NumberColumn(
                    "Market Value", format="$%.2f"
                ),
                "Book Value": st.column_config.NumberColumn(
                    "Book Value", format="$%.2f"
                ),
                "Dividends": st.column_config.NumberColumn("Dividends", format="$%.2f"),
                "Realized PnL": st.column_config.NumberColumn(
                    "Realized PnL", format="$%.2f"
                ),
                "Unrealized PnL": st.column_config.NumberColumn(
                    "Unrealized PnL", format="$%.2f"
                ),
                "Total Return ($)": st.column_config.NumberColumn(
                    "Total Return ($)", format="$%.2f"
                ),
                "Total Return (%)": st.column_config.NumberColumn(
                    "Total Return (%)", format="%.2f%%"
                ),
                "Annualized Return (%)": st.column_config.NumberColumn(
                    "Annualized Return (%)", format="%.2f%%"
                ),
                "Sector": st.column_config.TextColumn("Sector"),
                "Asset Class": st.column_config.TextColumn("Asset Class"),
                "Status": st.column_config.TextColumn("Status"),
            },
            hide_index=True,
        )

        st.info(
            "💡 **Note**: All values are in the native currency of the asset (CAD or USD). Weights are normalized to portfolio total."
        )
    else:
        st.info("No holdings data available")


def render_holdings_summary(holdings_data: pd.DataFrame):
    if not holdings_data.empty:
        st.subheader("Holdings Summary")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Positions", len(holdings_data))
        with col2:
            st.metric(
                "Avg Position Size (Native)",
                f"${holdings_data['market_value'].mean():,.0f}",
            )
        with col3:
            st.metric(
                "Largest Position (Native)",
                f"${holdings_data.iloc[0]['market_value']:,.0f}",
            )
        with col4:
            st.metric(
                "Smallest Position (Native)",
                f"${holdings_data.iloc[-1]['market_value']:,.0f}",
            )
        st.markdown("---")
