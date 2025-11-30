"""
Fama-French 3-Factor Model View Component

This component displays the Fama-French 3-factor analysis for a portfolio,
showing market, size, and value factor exposures.
"""

import streamlit as st
import plotly.graph_objects as go
from typing import Dict, Any


def render_fama_french_factors(ff_data: Dict[str, Any]):
    """
    Render the Fama-French 3-factor model analysis.
    
    Args:
        ff_data: Dictionary containing factor loadings and statistics
            Expected keys:
            - 'market_factor': float (beta_market)
            - 'size_factor': float (beta_SMB)
            - 'value_factor': float (beta_HML)
            - 'alpha': float (optional, Jensen's alpha from regression)
            - 'r_squared': float (optional, model fit)
    """
    st.header("🎯 Fama-French 3-Factor Analysis")
    
    if not ff_data:
        st.info("Fama-French factor data not available. Need at least 12 months of data.")
        return
    
    st.markdown("""
    The Fama-French 3-Factor Model decomposes portfolio returns into three systematic risk factors:
    - **Market Factor (β_MKT)**: Sensitivity to overall market movements
    - **Size Factor (β_SMB)**: Small Minus Big - Exposure to small-cap stocks
    - **Value Factor (β_HML)**: High Minus Low - Exposure to value stocks
    """)
    
    # Extract factors
    market_factor = ff_data.get('market_factor', 0.0)
    size_factor = ff_data.get('size_factor', 0.0)
    value_factor = ff_data.get('value_factor', 0.0)
    alpha = ff_data.get('alpha', None)
    r_squared = ff_data.get('r_squared', None)
    
    # Display factor loadings in metrics
    st.subheader("Factor Loadings")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Market factor interpretation
        market_interpretation = _interpret_market_factor(market_factor)
        st.metric(
            "Market Factor (β_MKT)",
            f"{market_factor:.3f}",
            help="Measures portfolio sensitivity to market movements"
        )
        st.caption(f"📊 {market_interpretation}")
    
    with col2:
        # Size factor interpretation
        size_interpretation = _interpret_size_factor(size_factor)
        st.metric(
            "Size Factor (β_SMB)",
            f"{size_factor:.3f}",
            help="Measures portfolio tilt toward small or large cap stocks"
        )
        st.caption(f"📏 {size_interpretation}")
    
    with col3:
        # Value factor interpretation
        value_interpretation = _interpret_value_factor(value_factor)
        st.metric(
            "Value Factor (β_HML)",
            f"{value_factor:.3f}",
            help="Measures portfolio tilt toward value or growth stocks"
        )
        st.caption(f"💎 {value_interpretation}")
    
    st.markdown("---")
    
    # Display additional regression statistics if available
    if alpha is not None or r_squared is not None:
        st.subheader("Regression Statistics")
        stat_col1, stat_col2 = st.columns(2)
        
        with stat_col1:
            if alpha is not None:
                # Convert monthly alpha to annualized percentage
                annualized_alpha = alpha * 12 * 100
                st.metric(
                    "Alpha (Annualized)",
                    f"{annualized_alpha:.2f}%",
                    help="Excess return not explained by the three factors (annualized)"
                )
                if annualized_alpha > 0:
                    st.caption("✨ Positive alpha suggests outperformance beyond factor exposure")
                else:
                    st.caption("📉 Negative alpha suggests underperformance relative to factor exposure")
        
        with stat_col2:
            if r_squared is not None:
                st.metric(
                    "R² (Model Fit)",
                    f"{r_squared:.3f}",
                    help="Proportion of return variance explained by the three factors"
                )
                st.caption(f"📈 {r_squared*100:.1f}% of returns explained by these factors")
    
    st.markdown("---")
    
    # Create factor exposure visualization
    st.subheader("Factor Exposure Visualization")
    _render_factor_chart(market_factor, size_factor, value_factor)
    
    # Create detailed interpretation
    st.subheader("💡 Portfolio Interpretation")
    _render_detailed_interpretation(market_factor, size_factor, value_factor)


def _interpret_market_factor(beta: float) -> str:
    """Interpret market factor beta value."""
    if beta > 1.1:
        return f"High volatility ({int((beta-1)*100)}% more volatile than market)"
    elif beta > 0.9:
        return "Moves in line with market"
    elif beta > 0.5:
        return f"Defensive ({int((1-beta)*100)}% less volatile than market)"
    elif beta > 0:
        return "Very defensive (low market correlation)"
    else:
        return "Negative market correlation (unusual)"


def _interpret_size_factor(beta: float) -> str:
    """Interpret size factor beta value."""
    if beta > 0.3:
        return "Strong small-cap tilt"
    elif beta > 0.1:
        return "Moderate small-cap tilt"
    elif beta > -0.1:
        return "Size-neutral"
    elif beta > -0.3:
        return "Moderate large-cap tilt"
    else:
        return "Strong large-cap tilt"


def _interpret_value_factor(beta: float) -> str:
    """Interpret value factor beta value."""
    if beta > 0.3:
        return "Strong value tilt"
    elif beta > 0.1:
        return "Moderate value tilt"
    elif beta > -0.1:
        return "Value/Growth neutral"
    elif beta > -0.3:
        return "Moderate growth tilt"
    else:
        return "Strong growth tilt"


def _render_factor_chart(market: float, size: float, value: float):
    """Create a visual representation of factor exposures."""
    
    # Create horizontal bar chart
    factors = ['Market (β_MKT)', 'Size (β_SMB)', 'Value (β_HML)']
    values = [market, size, value]
    
    # Color based on magnitude and direction
    colors = []
    for val in values:
        if abs(val) < 0.1:
            colors.append('#95a5a6')  # Gray for neutral
        elif val > 0:
            colors.append('#27ae60')  # Green for positive
        else:
            colors.append('#e74c3c')  # Red for negative
    
    fig = go.Figure(go.Bar(
        x=values,
        y=factors,
        orientation='h',
        marker=dict(color=colors),
        text=[f'{v:.3f}' for v in values],
        textposition='outside',
    ))
    
    fig.update_layout(
        title="Factor Loadings",
        xaxis_title="Beta Coefficient",
        yaxis_title="Factor",
        height=300,
        showlegend=False,
        xaxis=dict(
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='lightgray',
            range=[min(-1, min(values) - 0.2), max(1.5, max(values) + 0.2)]
        )
    )
    
    # Add reference line at 1.0 for market factor comparison
    fig.add_vline(x=1.0, line_dash="dash", line_color="gray", opacity=0.5,
                  annotation_text="Market", annotation_position="top")
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Create a radar/spider chart for multi-factor view
    fig_radar = go.Figure()
    
    fig_radar.add_trace(go.Scatterpolar(
        r=[abs(market), abs(size), abs(value)],
        theta=['Market<br>Sensitivity', 'Size<br>Exposure', 'Value<br>Exposure'],
        fill='toself',
        name='Factor Magnitude',
        marker=dict(color='#3498db')
    ))
    
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max(1.5, max(abs(market), abs(size), abs(value)) + 0.2)]
            )
        ),
        showlegend=False,
        title="Factor Exposure Magnitude",
        height=400
    )
    
    st.plotly_chart(fig_radar, use_container_width=True)


def _render_detailed_interpretation(market: float, size: float, value: float):
    """Provide detailed interpretation of the factor loadings."""
    
    interpretation_parts = []
    
    # Market interpretation
    if market > 1.1:
        interpretation_parts.append(
            f"📈 **Aggressive Market Exposure**: With a market beta of {market:.3f}, "
            f"this portfolio amplifies market movements. When the market rises 1%, "
            f"the portfolio is expected to rise approximately {market:.1%}."
        )
    elif market > 0.9:
        interpretation_parts.append(
            f"📊 **Market-Like Behavior**: With a market beta near {market:.3f}, "
            f"this portfolio closely tracks overall market movements."
        )
    else:
        interpretation_parts.append(
            f"🛡️ **Defensive Positioning**: With a market beta of {market:.3f}, "
            f"this portfolio is less volatile than the market and may provide downside protection."
        )
    
    # Size interpretation
    if abs(size) > 0.2:
        cap_bias = "small-cap" if size > 0 else "large-cap"
        interpretation_parts.append(
            f"🏢 **{cap_bias.title()} Bias**: The portfolio shows {'significant' if abs(size) > 0.4 else 'moderate'} "
            f"exposure to {cap_bias} stocks (β_SMB = {size:.3f}). This means returns will be influenced by "
            f"the performance spread between small and large companies."
        )
    else:
        interpretation_parts.append(
            f"⚖️ **Size Neutral**: The portfolio is well-balanced across market capitalizations "
            f"(β_SMB = {size:.3f}), with no significant small or large-cap bias."
        )
    
    # Value interpretation
    if abs(value) > 0.2:
        style_bias = "value" if value > 0 else "growth"
        interpretation_parts.append(
            f"💼 **{style_bias.title()} Orientation**: The portfolio leans toward {style_bias} stocks "
            f"(β_HML = {value:.3f}). {'Value stocks tend to outperform during economic recoveries and periods of rising rates.' if value > 0 else 'Growth stocks often lead during low-rate environments and innovation-driven markets.'}"
        )
    else:
        interpretation_parts.append(
            f"🎯 **Style Balanced**: The portfolio maintains a balanced mix of value and growth stocks "
            f"(β_HML = {value:.3f}), not heavily tilted toward either investment style."
        )
    
    # Display interpretations
    for i, part in enumerate(interpretation_parts):
        st.markdown(part)
        if i < len(interpretation_parts) - 1:
            st.markdown("")  # Add spacing
    
    # Risk implications
    st.markdown("---")
    st.markdown("### ⚠️ Risk Implications")
    
    risk_notes = []
    
    if market > 1.2:
        risk_notes.append("• Higher volatility during market downturns")
    if abs(size) > 0.4:
        risk_notes.append(f"• Concentrated exposure to {'small' if size > 0 else 'large'}-cap risks")
    if abs(value) > 0.4:
        risk_notes.append(f"• Style risk - vulnerable when {'growth' if value > 0 else 'value'} outperforms")
    
    if risk_notes:
        for note in risk_notes:
            st.markdown(note)
    else:
        st.markdown("• Well-diversified factor exposure reduces concentration risk")


def render_fama_french_summary_card(ff_data: Dict[str, Any]):
    """
    Render a compact summary card for Fama-French factors.
    Useful for dashboards where space is limited.
    
    Args:
        ff_data: Dictionary containing factor loadings
    """
    if not ff_data:
        return
    
    market = ff_data.get('market_factor', 0.0)
    size = ff_data.get('size_factor', 0.0)
    value = ff_data.get('value_factor', 0.0)
    
    with st.expander("🎯 Fama-French Factor Summary", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Market β", f"{market:.3f}")
        with col2:
            st.metric("Size β", f"{size:.3f}")
        with col3:
            st.metric("Value β", f"{value:.3f}")
        
        st.caption(
            f"Portfolio is {'aggressive' if market > 1.1 else 'defensive' if market < 0.9 else 'market-like'}, "
            f"{'small-cap' if size > 0.2 else 'large-cap' if size < -0.2 else 'size-neutral'}, "
            f"and {'value' if value > 0.2 else 'growth' if value < -0.2 else 'style-neutral'}."
        )

