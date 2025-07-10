import streamlit as st
import pandas as pd
import os

st.set_page_config(
    page_title="Holdings Analysis",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Holdings Analysis")

if 'selected_portfolio' not in st.session_state:
    st.error("Please select a portfolio on the main page first.")
    st.stop()

selected_portfolio = st.session_state['selected_portfolio']
st.success(f"Analyzing holdings for portfolio: **{selected_portfolio}**")

# Dummy holdings data
st.header("📊 Current Holdings")
holdings_data = {
    'Ticker': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'CRM', 'ADBE'],
    'Company': ['Apple Inc.', 'Microsoft Corp.', 'Alphabet Inc.', 'Amazon.com Inc.', 'Tesla Inc.', 
                'NVIDIA Corp.', 'Meta Platforms Inc.', 'Netflix Inc.', 'Salesforce Inc.', 'Adobe Inc.'],
    'Shares': [100, 50, 25, 30, 20, 15, 40, 35, 45, 30],
    'Price': [150.25, 320.50, 2800.75, 3300.25, 850.00, 450.75, 280.50, 450.25, 220.75, 380.50],
    'Market Value': [15025, 16025, 70019, 99008, 17000, 6761, 11220, 15759, 9934, 11415],
    'Weight (%)': [8.2, 8.7, 38.1, 53.8, 9.2, 3.7, 6.1, 8.6, 5.4, 6.2],
    'Sector': ['Technology', 'Technology', 'Technology', 'Consumer Discretionary', 'Consumer Discretionary',
               'Technology', 'Technology', 'Communication Services', 'Technology', 'Technology']
}
holdings_df = pd.DataFrame(holdings_data)
holdings_df['Market Value'] = holdings_df['Shares'] * holdings_df['Price']
total_value = holdings_df['Market Value'].sum()
holdings_df['Weight (%)'] = (holdings_df['Market Value'] / total_value * 100).round(1)
st.subheader("Holdings Summary")
st.dataframe(holdings_df, use_container_width=True)
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Holdings", len(holdings_df))
with col2:
    st.metric("Total Value", f"${total_value:,.0f}")
with col3:
    st.metric("Largest Position", f"{holdings_df.loc[holdings_df['Weight (%)'].idxmax(), 'Ticker']} ({holdings_df['Weight (%)'].max():.1f}%)")
with col4:
    st.metric("Average Position", f"${total_value/len(holdings_df):,.0f}")
st.header("🏭 Sector Allocation")
sector_allocation = holdings_df.groupby('Sector')['Weight (%)'].sum().sort_values(ascending=False)
st.bar_chart(sector_allocation)
st.header("🏆 Top Holdings")
top_holdings = holdings_df.nlargest(5, 'Weight (%)')[['Ticker', 'Company', 'Weight (%)', 'Market Value']]
st.table(top_holdings)
col1, col2 = st.columns(2)
with col1:
    st.subheader("📈 Position Size Distribution")
    position_sizes = pd.cut(holdings_df['Weight (%)'], 
                           bins=[0, 5, 10, 15, 20, 100], 
                           labels=['<5%', '5-10%', '10-15%', '15-20%', '>20%'])
    size_dist = position_sizes.value_counts().sort_index()
    st.bar_chart(size_dist)
with col2:
    st.subheader("💰 Market Value Distribution")
    value_bins = pd.cut(holdings_df['Market Value'], 
                       bins=[0, 10000, 20000, 50000, 100000, 1000000], 
                       labels=['<10K', '10K-20K', '20K-50K', '50K-100K', '>100K'])
    value_dist = value_bins.value_counts().sort_index()
    st.bar_chart(value_dist)
st.header("⚠️ Risk Metrics")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Concentration Risk", f"{holdings_df['Weight (%)'].max():.1f}%")
with col2:
    st.metric("Top 5 Holdings", f"{holdings_df.nlargest(5, 'Weight (%)')['Weight (%)'].sum():.1f}%")
with col3:
    st.metric("Technology Exposure", f"{holdings_df[holdings_df['Sector'] == 'Technology']['Weight (%)'].sum():.1f}%") 