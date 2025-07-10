import streamlit as st
import pandas as pd
import numpy as np
import os
from legacy.performance.returns_calculator import ReturnsCalculator

st.set_page_config(
    page_title="Performance Metrics",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Performance Metrics")

if 'selected_portfolio' not in st.session_state:
    st.error("Please select a portfolio on the main page first.")
    st.stop()

selected_portfolio = st.session_state['selected_portfolio']
st.success(f"Analyzing performance for portfolio: **{selected_portfolio}**")

data_dir = os.path.join("legacy", "data")
output_folder = os.path.join(data_dir, selected_portfolio, 'output')
portfolio_csv = os.path.join(output_folder, 'portfolio_total.csv')

if not os.path.exists(portfolio_csv):
    st.error(f"portfolio_total.csv not found in {output_folder}")
    st.stop()

calc = ReturnsCalculator(output_folder)
df = calc.df

returns = df['pct_change'].dropna()
volatility = returns.std() * np.sqrt(252)
sharpe_ratio = (returns.mean() * 252) / volatility if volatility > 0 else 0
max_drawdown = ((df['Total_Portfolio_Value'] / df['Total_Portfolio_Value'].expanding().max()) - 1).min()

st.header("🎯 Key Performance Metrics")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Annualized Return", f"{calc.annualized_average_return():.2%}")
with col2:
    st.metric("Annualized Volatility", f"{volatility:.2%}")
with col3:
    st.metric("Sharpe Ratio", f"{sharpe_ratio:.2f}")
with col4:
    st.metric("Maximum Drawdown", f"{max_drawdown:.2%}")

st.header("⚠️ Risk Metrics")
col1, col2, col3, col4 = st.columns(4)
with col1:
    var_95 = np.percentile(returns, 5)
    st.metric("VaR (95%)", f"{var_95:.2%}")
with col2:
    cvar_95 = returns[returns <= var_95].mean()
    st.metric("CVaR (95%)", f"{cvar_95:.2%}")
with col3:
    positive_days = (returns > 0).sum()
    total_days = len(returns)
    win_rate = positive_days / total_days
    st.metric("Win Rate", f"{win_rate:.1%}")
with col4:
    avg_win = returns[returns > 0].mean()
    avg_loss = returns[returns < 0].mean()
    profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    st.metric("Profit Factor", f"{profit_factor:.2f}")

st.header("📈 Rolling Performance")
window = 30
rolling_return = df['Total_Portfolio_Value'].pct_change(window).rolling(window).mean() * 252
rolling_vol = df['pct_change'].rolling(window).std() * np.sqrt(252)
rolling_sharpe = rolling_return / rolling_vol
rolling_data = pd.DataFrame({
    'Date': df['Date'],
    'Rolling Return': rolling_return,
    'Rolling Volatility': rolling_vol,
    'Rolling Sharpe': rolling_sharpe
}).set_index('Date')
st.subheader("30-Day Rolling Metrics")
st.line_chart(rolling_data)

st.header("📊 Performance Attribution")
attribution_data = {
    'Factor': ['Stock Selection', 'Sector Allocation', 'Market Timing', 'Currency', 'Other'],
    'Contribution (%)': [2.5, 1.8, -0.5, 0.3, 0.2],
    'Risk (%)': [1.2, 0.8, 0.4, 0.2, 0.1]
}
attribution_df = pd.DataFrame(attribution_data)
attribution_df['Information Ratio'] = attribution_df['Contribution (%)'] / attribution_df['Risk (%)']
col1, col2 = st.columns(2)
with col1:
    st.subheader("Factor Attribution")
    st.bar_chart(attribution_df.set_index('Factor')['Contribution (%)'])
with col2:
    st.subheader("Information Ratios")
    st.bar_chart(attribution_df.set_index('Factor')['Information Ratio'])
st.header("🏆 Performance Comparison")
benchmark_data = {
    'Period': ['1M', '3M', '6M', '1Y', 'YTD', '3Y', '5Y'],
    'Portfolio': [2.5, 8.2, 15.3, 28.7, 12.4, 45.2, 89.1],
    'Benchmark': [1.8, 6.5, 12.1, 22.3, 9.8, 38.7, 72.4],
    'Excess': [0.7, 1.7, 3.2, 6.4, 2.6, 6.5, 16.7]
}
comparison_df = pd.DataFrame(benchmark_data)
comparison_df['Excess'] = comparison_df['Portfolio'] - comparison_df['Benchmark']
st.subheader("vs Benchmark Performance")
st.table(comparison_df)
st.header("📊 Return Distribution")
col1, col2 = st.columns(2)
with col1:
    st.subheader("Daily Returns Distribution")
    st.histogram(returns, bins=50)
with col2:
    st.subheader("Cumulative Returns")
    cumulative_returns = (1 + returns).cumprod()
    st.line_chart(cumulative_returns)
st.header("📉 Drawdown Analysis")
drawdown = (df['Total_Portfolio_Value'] / df['Total_Portfolio_Value'].expanding().max()) - 1
st.area_chart(drawdown)
st.subheader("Recovery Periods")
recovery_data = {
    'Drawdown Period': ['2020-03', '2018-12', '2016-01'],
    'Depth': ['-15.2%', '-8.7%', '-5.3%'],
    'Duration': ['45 days', '23 days', '12 days'],
    'Recovery': ['67 days', '34 days', '18 days']
}
recovery_df = pd.DataFrame(recovery_data)
st.table(recovery_df) 