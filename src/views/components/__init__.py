"""
UI Components Package - Reusable Streamlit UI components for portfolio analysis.

This package contains modular UI components that can be imported and used
across different Streamlit pages for consistent, maintainable UI.
"""

from .portfolio_summary import (
    render_portfolio_summary,
    render_portfolio_breakdown,
    render_cash_breakdown
)

from .holdings_table import (
    render_holdings_table,
    render_holdings_summary
)

from .allocation_charts import (
    render_allocation_charts,
    render_allocation_summary
)

from .performance_metrics import (
    render_performance_metrics,
    render_period_returns,
    render_risk_metrics,
    render_risk_ratios,
    render_market_metrics,
    render_performance_summary
)

__all__ = [
    # Portfolio Summary
    'render_portfolio_summary',
    'render_portfolio_breakdown', 
    'render_cash_breakdown',
    
    # Holdings Table
    'render_holdings_table',
    'render_holdings_summary',
    
    # Allocation Charts
    'render_allocation_charts',
    'render_allocation_summary',
    
    # Performance Metrics
    'render_performance_metrics',
    'render_period_returns',
    'render_risk_metrics',
    'render_risk_ratios',
    'render_market_metrics',
    'render_performance_summary'
]
