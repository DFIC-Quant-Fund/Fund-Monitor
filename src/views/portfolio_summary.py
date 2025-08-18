"""
Portfolio Summary Component - Reusable UI component for portfolio overview metrics.

This component displays:
- Total portfolio value
- Equity value
- Total holdings
- Largest position
- As of date
"""

import streamlit as st
from typing import Dict, Any

def render_portfolio_summary(summary_data: Dict[str, Any], total_portfolio_value: float):
    """
    Render the main portfolio summary metrics.
    
    Args:
        summary_data: Dictionary containing portfolio summary information
        total_portfolio_value: Total portfolio value including cash
    """
    st.subheader("📊 Portfolio Overview")
    
    # Main dashboard metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Total Portfolio Value",
            f"${total_portfolio_value:,.0f}",
            help="Total portfolio value including equities, cash, and dividends"
        )
    
    with col2:
        equity_value = summary_data['total_value']
        st.metric(
            "Equity Value",
            f"${equity_value:,.0f}",
            help="Total value of equity holdings only"
        )
    
    with col3:
        st.metric(
            "Total Holdings",
            summary_data['total_holdings'],
            help="Number of individual equity positions"
        )
    
    with col4:
        st.metric(
            "Largest Position",
            f"{summary_data['largest_position_ticker']} ({summary_data['largest_position_weight']:.1f}%)",
            help="Largest equity holding by market value"
        )
    
    with col5:
        st.metric(
            "As of Date",
            summary_data['as_of_date'].strftime('%Y-%m-%d'),
            help="Date of portfolio snapshot"
        )
    
    st.markdown("---")

def render_portfolio_breakdown(summary_data: Dict[str, Any], total_portfolio_value: float, cash_data: Dict[str, float]):
    """
    Render the portfolio breakdown section.
    
    Args:
        summary_data: Dictionary containing portfolio summary information
        total_portfolio_value: Total portfolio value including cash
        cash_data: Dictionary containing cash information
    """
    st.subheader("📊 Portfolio Breakdown")
    breakdown_col1, breakdown_col2, breakdown_col3, breakdown_col4 = st.columns(4)
    
    equity_value = summary_data['total_value']
    
    with breakdown_col1:
        equity_weight = (equity_value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
        st.metric(
            "Equity Allocation",
            f"{equity_weight:.1f}%",
            help="Percentage of portfolio in equities"
        )
    
    with breakdown_col2:
        cash_weight = (cash_data['Total_CAD'] / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
        st.metric(
            "Cash Allocation",
            f"{cash_weight:.1f}%",
            help="Percentage of portfolio in cash"
        )
    
    with breakdown_col3:
        st.metric(
            "Equity Value",
            f"${equity_value:,.0f}",
            help="Total value of equity holdings"
        )
    
    with breakdown_col4:
        st.metric(
            "Cash Value",
            f"${cash_data['Total_CAD']:,.0f}",
            help="Total cash balance in CAD"
        )
    
    # Add note about total portfolio value
    st.info("💡 **Note**: Total portfolio value includes equities, cash, and cumulative dividends.")
    st.markdown("---")

def render_cash_breakdown(cash_data: Dict[str, float]):
    """
    Render the cash breakdown section.
    
    Args:
        cash_data: Dictionary containing cash information
    """
    if cash_data['CAD_Cash'] > 0 or cash_data['USD_Cash'] > 0:
        st.subheader("💰 Cash Breakdown")
        cash_col1, cash_col2, cash_col3, cash_col4 = st.columns(4)
        
        with cash_col1:
            st.metric(
                "CAD Cash",
                f"${cash_data['CAD_Cash']:,.2f}",
                help="Canadian dollar cash balance"
            )
        
        with cash_col2:
            st.metric(
                "USD Cash",
                f"${cash_data['USD_Cash']:,.2f}",
                help="US dollar cash balance"
            )
        
        with cash_col3:
            st.metric(
                "Total Cash (CAD)",
                f"${cash_data['Total_CAD']:,.2f}",
                help="Total cash converted to CAD"
            )
        
        with cash_col4:
            if cash_data.get('USD_CAD_Rate') is not None:
                st.metric(
                    "USD→CAD Rate",
                    f"{cash_data['USD_CAD_Rate']:.4f}",
                    help="Exchange rate used to convert USD cash to CAD"
                )
        
        st.markdown("---")


