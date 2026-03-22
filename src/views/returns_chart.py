"""
Returns Chart Component - Interactive Plotly chart for cumulative returns since inception.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from src.config.benchmark_yaml import format_benchmark_target_allocation_caption
except ImportError:
    from config.benchmark_yaml import format_benchmark_target_allocation_caption

BENCHMARK_ALLOCATION_RATIONALE = (
    "We shifted the portfolio allocation from 60/40 to 70/30 primarily to capitalize on "
    "stronger opportunities in equities and leverage the larger number of equity teams "
    "generating investment ideas. While the fund remains balanced, the higher equity "
    "allocation allows greater flexibility to deploy capital into alternatives or global "
    "exposures (e.g., gold or international markets) while keeping a smaller fixed-income "
    "allocation, particularly since we cannot purchase single-name bonds. Additionally, "
    "recent asset correlations have reduced the diversification benefits of bonds, making "
    "a slightly more equity-focused strategy more effective for both performance and "
    "active portfolio management."
)


def render_returns_chart(returns_df: pd.DataFrame):
	"""
	Render cumulative return since inception as an interactive Plotly line chart.
	Expects a DataFrame with columns: Date, Cumulative_Return_Pct
	"""
	st.header("📈 Return Since Inception")
	# if returns_df is None or returns_df.empty or 'Cumulative_Return_Pct' not in returns_df.columns:
	# 	st.info("Returns data not available.")
	# 	return

	df = returns_df.copy()
	df = df.sort_values('Date')

	fig = px.line(
		df,
		x='Date',
		y='Cumulative_Return_Pct',
		title='Cumulative Return Since Inception',
		labels={'Date': 'Date', 'Cumulative_Return_Pct': 'Cumulative Return (%)'}
	)

	# Add Benchmark Trace if available
	if 'Benchmark_Cumulative_Return_Pct' in df.columns:
		fig.add_scatter(
			x=df['Date'], 
			y=df['Benchmark_Cumulative_Return_Pct'], 
			mode='lines', 
			name='Benchmark',
			line=dict(color='gray', dash='dash')
		)
		# Rename the main trace
		fig.data[0].name = 'Portfolio'
		fig.data[0].showlegend = True

	# Add SPY Trace if available
	if 'SPY_Cumulative_Return_Pct' in df.columns:
		fig.add_scatter(
			x=df['Date'], 
			y=df['SPY_Cumulative_Return_Pct'], 
			mode='lines', 
			name='SPY',
			line=dict(color='orange', dash='dot')
		)
		# Rename the main trace if not already done
		fig.data[0].name = 'Portfolio'
		fig.data[0].showlegend = True

	fig.update_traces(hovertemplate='%{x|%Y-%m-%d}<br>%{y:.2f}%')
	fig.update_layout(
		hovermode='x unified',
		yaxis_tickformat='.2f',
		yaxis_title='Return (%)',
		xaxis_title='Date'
	)

	st.plotly_chart(fig, use_container_width=True)


def render_benchmark_target_allocation_note(project_root: str) -> None:
	"""Prominent centered benchmark policy line from YAML (below returns chart only)."""
	text = format_benchmark_target_allocation_caption(project_root)
	if text:
		st.markdown(
			(
				'<div style="text-align:center;margin:1rem 0 0.75rem 0;padding:0.85rem 1rem;'
				'background-color:rgba(99,110,250,0.08);border-radius:8px;border:1px solid rgba(99,110,250,0.2);">'
				f'<p style="margin:0;font-size:1.5rem;font-weight:700;line-height:1.35;letter-spacing:0.01em;">{text}</p>'
				"</div>"
			),
			unsafe_allow_html=True,
		)


def render_benchmark_rationale_section() -> None:
	"""Centered rationale copy for the benchmark portfolio (below target allocation)."""
	st.markdown(
		(
			'<section style="max-width:52rem;margin:1.25rem auto 0.5rem auto;padding:0 1rem;">'
			'<h3 style="text-align:center;font-size:1.35rem;font-weight:700;margin:0 0 1rem 0;'
			'letter-spacing:0.02em;">Rationale</h3>'
			'<p style="text-align:center;font-size:1.08rem;line-height:1.7;margin:0;'
			'font-weight:400;">'
			f"{BENCHMARK_ALLOCATION_RATIONALE}"
			"</p></section>"
		),
		unsafe_allow_html=True,
	)

