"""
Fixed Income Analysis Component - Reusable UI component for fixed income analysis visualization.
"""

import streamlit as st
import pandas as pd


def render_fixed_income_analysis(portfolio_controller):
    """
    Render fixed income analysis including summary metrics and holdings details.
    
    Args:
        portfolio_controller: PortfolioController instance for accessing FI data
    """
    st.header("Fixed Income Analysis")
    try:
        fi_data = portfolio_controller.get_fixed_income_info()
        
        if fi_data.empty:
            st.info("No fixed income holdings in portfolio")
        else:
            # Display summary metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_fi_value = fi_data['Market Value (CAD)'].sum()
                st.metric("Total FI Value (CAD)", f"${total_fi_value:,.2f}")
            
            with col2:
                st.metric("Number of FI Holdings", len(fi_data))
            
            with col3:
                usd_holdings = (fi_data['Currency'] == 'USD').sum()
                st.metric("USD Holdings", usd_holdings)
            
            st.divider()
            
            # Display detailed table
            st.subheader("Fixed Income Holdings Details")
            st.dataframe(
                fi_data.style.format({
                    'Market Value (CAD)': '${:,.2f}',
                    'Total FI Share %': '{:.2f}%',
                    'USD FI Share %': '{:.2f}%'
                }),
                use_container_width=True
            )
            
    except Exception as e:
        st.error(f"Error loading fixed income data: {e}")
