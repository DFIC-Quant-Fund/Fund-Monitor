"""
Allocation Charts Component - Reusable UI component for portfolio allocation visualizations.
"""

import streamlit as st
import plotly.express as px
import pandas as pd

def render_allocation_charts(allocation_data: pd.DataFrame):
    st.header("Portfolio Allocation")
    if not allocation_data.empty:
        col1, col2 = st.columns(2)
        with col1:
            sector_data = allocation_data.groupby('sector')['equity_weight_percent'].sum().reset_index()
            if not sector_data.empty:
                fig_sector = px.pie(sector_data, values='equity_weight_percent', names='sector', title="Sector Allocation (Equity Only)", color_discrete_sequence=px.colors.qualitative.Set3)
                fig_sector.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_sector, use_container_width=True)
        with col2:
            geo_data = allocation_data.groupby('geography')['equity_weight_percent'].sum().reset_index()
            if not geo_data.empty:
                fig_geo = px.pie(geo_data, values='equity_weight_percent', names='geography', title="Geographic Allocation (Equity Only)", color_discrete_sequence=px.colors.qualitative.Set1)
                fig_geo.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_geo, use_container_width=True)
            st.info("💡 **Note**: Allocation charts show equity holdings only (excluding cash).")
            render_allocation_summary(allocation_data)
    else:
        st.info("No allocation data available")

def render_allocation_summary(allocation_data: pd.DataFrame):
    if not allocation_data.empty:
        st.subheader("Allocation Summary")
        sector_summary = allocation_data.groupby('sector')['market_value'].sum().sort_values(ascending=False)
        st.write("**Top Sectors:**")
        for sector, value in sector_summary.head(3).items():
            weight = (value / allocation_data['market_value'].sum()) * 100
            st.write(f"• {sector}: ${value:,.0f} ({weight:.1f}%)")
        geo_summary = allocation_data.groupby('geography')['market_value'].sum().sort_values(ascending=False)
        st.write("**Geographic Breakdown:**")
        for geo, value in geo_summary.items():
            weight = (value / allocation_data['market_value'].sum()) * 100
            st.write(f"• {geo}: ${value:,.0f} ({weight:.1f}%)")


