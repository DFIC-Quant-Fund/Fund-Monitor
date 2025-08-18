"""
Performance Metrics Component - Reusable UI component for performance analysis.
"""

import streamlit as st
from typing import Dict, Any

def render_performance_metrics(performance_data: Dict[str, Any]):
    st.header("Performance Metrics")
    if not performance_data:
        st.info("Performance data not available")
        return
    if 'performance' in performance_data:
        render_period_returns(performance_data['performance'])
    if 'risk_metrics' in performance_data:
        render_risk_metrics(performance_data['risk_metrics'])
    if 'ratios' in performance_data:
        render_risk_ratios(performance_data['ratios'])
    if 'market_metrics' in performance_data:
        render_market_metrics(performance_data['market_metrics'])

def render_period_returns(perf_data: Dict[str, Any]):
    st.subheader("Period Returns")
    col1, col2, col3 = st.columns(3)
    with col1:
        if perf_data.get('one_day') is not None:
            st.metric("1 Day", f"{perf_data['one_day']:.2f}%")
        if perf_data.get('one_week') is not None:
            st.metric("1 Week", f"{perf_data['one_week']:.2f}%")
    with col2:
        if perf_data.get('one_month') is not None:
            st.metric("1 Month", f"{perf_data['one_month']:.2f}%")
        if perf_data.get('ytd') is not None:
            st.metric("YTD", f"{perf_data['ytd']:.2f}%")
    with col3:
        if perf_data.get('one_year') is not None:
            st.metric("1 Year", f"{perf_data['one_year']:.2f}%")
        if perf_data.get('inception') is not None:
            st.metric("Inception", f"{perf_data['inception']:.2f}%")
    st.markdown("---")

def render_risk_metrics(risk_data: Dict[str, Any]):
    st.subheader("Risk Metrics")
    col1, col2, col3 = st.columns(3)
    with col1:
        if 'daily_volatility' in risk_data:
            st.metric("Daily Volatility", f"{risk_data['daily_volatility']:.4f}")
        if 'annualized_volatility' in risk_data:
            st.metric("Annualized Volatility", f"{risk_data['annualized_volatility']:.4f}")
    with col2:
        if 'maximum_drawdown' in risk_data:
            st.metric("Max Drawdown", f"{risk_data['maximum_drawdown']:.4f}")
        if 'daily_downside_volatility' in risk_data:
            st.metric("Downside Volatility", f"{risk_data['daily_downside_volatility']:.4f}")
    with col3:
        if 'annualized_downside_volatility' in risk_data:
            st.metric("Annualized Downside Vol", f"{risk_data['annualized_downside_volatility']:.4f}")
    st.markdown("---")

def render_risk_ratios(ratios_data: Dict[str, Any]):
    st.subheader("Risk-Adjusted Ratios")
    col1, col2, col3 = st.columns(3)
    with col1:
        if 'annualized_sharpe_ratio' in ratios_data:
            st.metric("Sharpe Ratio", f"{ratios_data['annualized_sharpe_ratio']:.3f}")
    with col2:
        if 'annualized_sortino_ratio' in ratios_data:
            st.metric("Sortino Ratio", f"{ratios_data['annualized_sortino_ratio']:.3f}")
    with col3:
        if 'annualized_information_ratio' in ratios_data:
            st.metric("Information Ratio", f"{ratios_data['annualized_information_ratio']:.3f}")
    st.markdown("---")

def render_market_metrics(market_data: Dict[str, Any]):
    st.subheader("Market Comparison")
    col1, col2, col3 = st.columns(3)
    with col1:
        if 'beta' in market_data:
            st.metric("Beta", f"{market_data['beta']:.3f}")
    with col2:
        if 'alpha' in market_data:
            st.metric("Alpha", f"{market_data['alpha']:.4f}")
    with col3:
        if 'risk_premium' in market_data:
            st.metric("Risk Premium", f"{market_data['risk_premium']:.4f}")
    st.markdown("---")

def render_performance_summary(performance_data: Dict[str, Any]):
    if not performance_data:
        return
    st.subheader("Performance Highlights")
    highlights = []
    if 'performance' in performance_data:
        perf = performance_data['performance']
        if perf.get('inception') is not None:
            highlights.append(f"**Inception Return:** {perf['inception']:.2f}%")
        if perf.get('one_year') is not None:
            highlights.append(f"**1-Year Return:** {perf['one_year']:.2f}%")
        if perf.get('ytd') is not None:
            highlights.append(f"**YTD Return:** {perf['ytd']:.2f}%")
    if 'risk_metrics' in performance_data:
        risk = performance_data['risk_metrics']
        if 'annualized_volatility' in risk:
            highlights.append(f"**Annualized Volatility:** {risk['annualized_volatility']:.2f}%")
        if 'maximum_drawdown' in risk:
            highlights.append(f"**Max Drawdown:** {risk['maximum_drawdown']:.2f}%")
    if 'ratios' in performance_data:
        ratios = performance_data['ratios']
        if 'annualized_sharpe_ratio' in ratios:
            highlights.append(f"**Sharpe Ratio:** {ratios['annualized_sharpe_ratio']:.3f}")
    for highlight in highlights:
        st.write(highlight)


