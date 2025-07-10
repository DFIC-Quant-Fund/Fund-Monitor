import streamlit as st
import pandas as pd
import os
import sys

from legacy.performance.returns_calculator import ReturnsCalculator

st.set_page_config(
    page_title="Returns Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Returns Dashboard")

if 'selected_portfolio' not in st.session_state:
    st.error("Please select a portfolio on the main page first.")
    st.stop()

selected_portfolio = st.session_state['selected_portfolio']
st.success(f"Analyzing portfolio: **{selected_portfolio}**")

data_dir = os.path.join("legacy", "data")
output_folder = os.path.join(data_dir, selected_portfolio, 'output')
portfolio_csv = os.path.join(output_folder, 'portfolio_total.csv')

if not os.path.exists(portfolio_csv):
    st.error(f"portfolio_total.csv not found in {output_folder}")
    st.stop()

calc = ReturnsCalculator(output_folder)
df = calc.df

max_date = df['Date'].max()
min_date = df['Date'].min()
selected_date = st.date_input("Select performance date", value=max_date, min_value=min_date, max_value=max_date)
calc.date = selected_date

if not calc.valid_date():
    st.error(f"Selected date {selected_date} not in data. Showing closest available date.")
    selected_date = calc._closest_date(selected_date)
    st.write(f"Closest available date: {selected_date.date()}")
    calc.date = selected_date

performance = calc.calculate_performance()
total_return = calc.total_return()

st.header("Performance Metrics")
col1, col2 = st.columns(2)
with col1:
    st.metric("Total Return (Inception)", f"{total_return:.2%}")
with col2:
    try:
        annualized_return = calc.annualized_average_return()
        st.metric("Annualized Return", f"{annualized_return:.2%}")
    except:
        st.metric("Annualized Return", "N/A")

period_names = {
    "one_day": "1 Day",
    "one_week": "1 Week", 
    "one_month": "1 Month",
    "ytd": "YTD",
    "one_year": "1 Year",
    "inception": "Inception"
}
returns_data = []
for key, value in performance.items():
    if value is not None:
        returns_data.append({
            "Period": period_names.get(key, key),
            "Return (%)": f"{value:.2f}%"
        })
    else:
        returns_data.append({
            "Period": period_names.get(key, key),
            "Return (%)": "N/A"
        })
returns_df = pd.DataFrame(returns_data)
st.subheader("Period Returns")
st.table(returns_df)
st.header("Portfolio Value Over Time")
st.line_chart(df.set_index('Date')['Total_Portfolio_Value'])
with st.expander("📊 View Raw Data"):
    st.dataframe(df) 