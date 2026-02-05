"""
Portfolio Summary Component - Reusable UI component for portfolio overview metrics.

This component displays:
- Total portfolio value
- Equity value
- Total holdings
- Return since inception
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
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric(
            "Total Portfolio Value",
            f"${total_portfolio_value:,.0f}",
            help="Total portfolio value including holdings and cash"
        )
    
    with col2:
        holdings_value = summary_data['total_holdings_value']
        st.metric(
            "Holdings Value",
            f"${holdings_value:,.0f}",
            help="Total value of all holdings (excluding cash)"
        )
    
    with col3:
        st.metric(
            "Total Holdings",
            summary_data['total_holdings'],
            help="Number of individual positions"
        )
    
    with col4:
        inception_val = summary_data.get('inception_return_pct')
        if inception_val is None:
            inception_display = "N/A"
        else:
            inception_display = f"{inception_val:.2f}%"
        st.metric("Return Since Inception", inception_display, help="Cumulative return since inception (total return including dividends/cash)")

    with col5:
        annualized_val = summary_data.get('annualized_return_pct')
        if annualized_val is None:
            annualized_display = "N/A"
        else:
            annualized_display = f"{annualized_val:.2f}%"
        st.metric("Annualized Return", annualized_display, help="Annualized return since inception")
        # Debug: uncomment to see the value
        # st.caption(f"Debug: {annualized_val}")

    with col6:
        st.metric(
            "As of Date",
            summary_data['as_of_date'].strftime('%Y-%m-%d'),
            help="Date of portfolio snapshot"
        )
    
    # Breakdown metrics
    st.markdown("---")
    st.subheader("🔎 Breakdown")
    b1, b2, b3 = st.columns(3)
    with b1:
        st.metric("CAD Holdings MV", f"${summary_data['cad_holdings_mv']:,.0f}")
    with b2:
        st.metric("USD Holdings MV", f"${summary_data['usd_holdings_mv']:,.0f}")
    with b3:
        st.metric("Total Cash (CAD)", f"${summary_data['total_cash_cad']:,.0f}")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("CAD Cash", f"${summary_data['cad_cash']:,.0f}")
    with c2:
        st.metric("USD Cash", f"${summary_data['usd_cash']:,.0f}")
    with c3:
        st.metric("Holdings + Cash", f"${total_portfolio_value:,.0f}")

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
    breakdown_col1, breakdown_col2, breakdown_col3, breakdown_col4, breakdown_col5, breakdown_col6 = st.columns(6)
    
    holdings_value = summary_data['total_holdings_value']
    
    with breakdown_col1:
        holdings_weight = (holdings_value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
        st.metric(
            "Holdings Allocation",
            f"{holdings_weight:.1f}%",
            help="Percentage of portfolio in holdings (excluding cash)"
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
            "Holdings Value",
            f"${holdings_value:,.0f}",
            help="Total value of all holdings (excluding cash)"
        )
    
    with breakdown_col4:
        st.metric(
            "Cash Value",
            f"${cash_data['Total_CAD']:,.0f}",
            help="Total cash balance in CAD"
        )

    with breakdown_col5:
        st.metric(
            "Annualized Return",
            f"{summary_data['annualized_return_pct']:.2f}%",
            help="Annualized return since inception"
        )

    with breakdown_col6:
        st.metric(
            "As of Date",
            summary_data['as_of_date'].strftime('%Y-%m-%d'),
            help="Date of portfolio snapshot"
        )
    
    # Add note about total portfolio value
    st.info("💡 **Note**: Total portfolio value includes holdings and cash.")
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


