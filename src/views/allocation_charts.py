"""
Allocation Charts Component - Reusable UI component for portfolio allocation visualizations.
"""

import streamlit as st
import plotly.express as px
import pandas as pd

def render_allocation_charts(holdings_data: pd.DataFrame):
    st.header("Portfolio Allocation")
    if not holdings_data.empty:
        equity_value = holdings_data['market_value'].sum()
        holdings_data['equity_weight_percent'] = (holdings_data['market_value'] / equity_value * 100) if equity_value > 0 else 0
        col1, col2 = st.columns(2)
        with col1:
            sector_data = holdings_data.groupby('sector')['equity_weight_percent'].sum().reset_index()
            if not sector_data.empty:
                fig_sector = px.pie(sector_data, values='equity_weight_percent', names='sector', title="Sector Allocation (Equity Only)", color_discrete_sequence=px.colors.qualitative.Set3)
                fig_sector.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_sector, use_container_width=True)
            fund_data = holdings_data.groupby('fund')['equity_weight_percent'].sum().reset_index()
            if not fund_data.empty:
                fig_fund = px.pie(fund_data, values='equity_weight_percent', names='fund', title="Fund Allocation (Equity Only)", color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_fund.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_fund, use_container_width=True)
        with col2:
            geo_data = holdings_data.groupby('geography')['equity_weight_percent'].sum().reset_index()
            if not geo_data.empty:
                fig_geo = px.pie(geo_data, values='equity_weight_percent', names='geography', title="Geographic Allocation (Equity Only)", color_discrete_sequence=px.colors.qualitative.Set1)
                fig_geo.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_geo, use_container_width=True)
            st.info("💡 **Note**: Allocation charts show equity holdings only (excluding cash).")
            render_allocation_summary(holdings_data)
    else:
        st.info("No allocation data available")

def render_allocation_summary(holdings_data: pd.DataFrame):
    if not holdings_data.empty:
        st.subheader("Allocation Summary")
        sector_summary = holdings_data.groupby('sector')['market_value'].sum().sort_values(ascending=False)
        st.write("**Top Sectors:**")
        for sector, value in sector_summary.head(3).items():
            weight = (value / holdings_data['market_value'].sum()) * 100
            st.write(f"• {sector}: ${value:,.0f} ({weight:.1f}%)")
        fund_summary = holdings_data.groupby('fund')['market_value'].sum().sort_values(ascending=False)
        st.write("**Fund Breakdown:**")
        for fund, value in fund_summary.items():
            weight = (value / holdings_data['market_value'].sum()) * 100
            st.write(f"• {fund}: ${value:,.0f} ({weight:.1f}%)")
        geo_summary = holdings_data.groupby('geography')['market_value'].sum().sort_values(ascending=False)
        st.write("**Geographic Breakdown:**")
        for geo, value in geo_summary.items():
            weight = (value / holdings_data['market_value'].sum()) * 100
            st.write(f"• {geo}: ${value:,.0f} ({weight:.1f}%)")


