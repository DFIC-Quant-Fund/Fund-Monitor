"""
Views package - Streamlit UI components.
"""

from .portfolio_summary import (
	render_portfolio_summary,
	render_portfolio_breakdown,
	render_cash_breakdown,
)
from .holdings_table import (
	render_holdings_table,
	render_holdings_summary,
)
from .allocation_charts import (
	render_allocation_charts,
	render_allocation_summary,
)
from .performance_metrics import (
	render_performance_metrics,
	render_period_returns,
	render_risk_metrics,
	render_risk_ratios,
	render_market_metrics,
	render_performance_summary,
)
from .returns_chart import (
	render_returns_chart,
)
from .fama_french_view import (
	render_fama_french_factors,
	render_fama_french_summary_card,
)

__all__ = [
	'render_portfolio_summary',
	'render_portfolio_breakdown',
	'render_cash_breakdown',
	'render_holdings_table',
	'render_holdings_summary',
	'render_allocation_charts',
	'render_allocation_summary',
	'render_performance_metrics',
	'render_period_returns',
	'render_risk_metrics',
	'render_risk_ratios',
	'render_market_metrics',
	'render_performance_summary',
	'render_returns_chart',
	'render_fama_french_factors',
	'render_fama_french_summary_card',
]
