"""
Returns Chart Component - Interactive Plotly chart for cumulative returns since inception.
"""

import streamlit as st
import plotly.express as px
import pandas as pd


def render_returns_chart(returns_df: pd.DataFrame):
	"""
	Render cumulative return since inception as an interactive Plotly line chart.
	Expects a DataFrame with columns: Date, Cumulative_Return_Pct
	"""
	st.header("📈 Return Since Inception")
	if returns_df is None or returns_df.empty or 'Cumulative_Return_Pct' not in returns_df.columns:
		st.info("Returns data not available.")
		return

	df = returns_df.copy()
	df = df.sort_values('Date')

	fig = px.line(
		df,
		x='Date',
		y='Cumulative_Return_Pct',
		title='Cumulative Return Since Inception',
		labels={'Date': 'Date', 'Cumulative_Return_Pct': 'Cumulative Return (%)'}
	)

	fig.update_traces(hovertemplate='%{x|%Y-%m-%d}<br>%{y:.2f}%')
	fig.update_layout(
		hovermode='x unified',
		yaxis_tickformat='.2f',
		yaxis_title='Return (%)',
		xaxis_title='Date'
	)

	st.plotly_chart(fig, use_container_width=True)


