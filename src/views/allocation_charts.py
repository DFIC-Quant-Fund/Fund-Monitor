import streamlit as st
import plotly.express as px
import pandas as pd
import os

def render_allocation_charts(portfolio_name: str):
    st.header("Portfolio Allocation")
    
    # Construct file paths
    base_path = os.path.join("data", portfolio_name, "output")
    holdings_path = os.path.join(base_path, "holdings.csv")
    total_path = os.path.join(base_path, "portfolio_total.csv")
    
    # Check if files exist
    if not os.path.exists(holdings_path) or not os.path.exists(total_path):
        st.error(f"Data files not found in {base_path}")
        return

    try:
        # Load data directly from CSVs
        holdings_df = pd.read_csv(holdings_path)
        total_df = pd.read_csv(total_path)
    except Exception as e:
        st.error(f"Error reading data files: {e}")
        return

    if total_df.empty:
        st.info("No portfolio data available")
        return

    # Get totals from the last row of portfolio_total.csv (authoritative source)
    latest_total_row = total_df.iloc[-1]
    total_portfolio_value = float(latest_total_row['Total_Portfolio_Value'])
    total_cash_cad = float(latest_total_row['Total_Cash_CAD'])

    if total_portfolio_value == 0:
        st.info("Portfolio value is zero")
        return

    # --- Sector Allocation Calculation ---
    # Group holdings by sector and sum market_value_cad
    # Ensure 'sector' column exists
    if 'sector' not in holdings_df.columns or 'market_value_cad' not in holdings_df.columns:
        st.error("Holdings file missing required columns (sector, market_value_cad)")
        return

    sector_group = holdings_df.groupby('sector')['market_value_cad'].sum().reset_index()
    
    # Prepare data for plotting: Sectors + Cash
    allocation_data = []
    
    # Add Sectors
    for _, row in sector_group.iterrows():
        allocation_data.append({
            'Sector': row['sector'],
            'Value': row['market_value_cad']
        })
    
    # Add Cash as a sector
    allocation_data.append({
        'Sector': 'Cash',
        'Value': total_cash_cad
    })
    
    allocation_df = pd.DataFrame(allocation_data)
    
    # Calculate weights relative to Total Portfolio Value
    # Note: Sum of Values should match Total Portfolio Value approximately
    allocation_df['Weight'] = (allocation_df['Value'] / total_portfolio_value) * 100.0
    
    # Sort by Weight descending
    allocation_df = allocation_df.sort_values('Weight', ascending=False)

    # --- Asset Class Allocation Calculation ---
    asset_class_df = pd.DataFrame()
    if 'asset_class' in holdings_df.columns:
        asset_group = holdings_df.groupby('asset_class')['market_value_cad'].sum().reset_index()
        
        asset_data = []
        # Add Asset Classes
        for _, row in asset_group.iterrows():
            asset_data.append({
                'Asset Class': row['asset_class'],
                'Value': row['market_value_cad']
            })
            
        # Add Cash as an asset class
        # Check if 'Cash' already exists (unlikely but good to be safe)
        cash_exists = False
        for item in asset_data:
            if item['Asset Class'] == 'Cash':
                item['Value'] += total_cash_cad
                cash_exists = True
                break
        
        if not cash_exists:
            asset_data.append({
                'Asset Class': 'Cash',
                'Value': total_cash_cad
            })
            
        asset_class_df = pd.DataFrame(asset_data)
        asset_class_df['Weight'] = (asset_class_df['Value'] / total_portfolio_value) * 100.0
        asset_class_df = asset_class_df.sort_values('Weight', ascending=False)

    # Render Charts
    st.subheader("Allocations (Total Portfolio)")
    
    col1, col2 = st.columns(2)
    with col1:
        if not allocation_df.empty:
            fig_sector = px.pie(
                allocation_df, 
                values='Weight', 
                names='Sector', 
                title="Sector Allocation (Total Portfolio)", 
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_sector.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_sector, use_container_width=True)
            
    with col2:
        if not asset_class_df.empty:
            fig_asset = px.pie(
                asset_class_df, 
                values='Weight', 
                names='Asset Class', 
                title="Asset Class Allocation", 
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_asset.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_asset, use_container_width=True)

    # Render Summaries below charts
    col3, col4 = st.columns(2)
    with col3:
        render_allocation_summary(allocation_df, "Sector", total_portfolio_value)
    with col4:
        if not asset_class_df.empty:
            render_allocation_summary(asset_class_df, "Asset Class", total_portfolio_value)

def render_allocation_summary(df: pd.DataFrame, category_col: str, total_portfolio_value: float):
    if not df.empty:
        st.subheader(f"{category_col} Summary")
        
        for _, row in df.iterrows():
            st.write(f"• {row[category_col]}: ${row['Value']:,.0f} ({row['Weight']:.1f}%)")
            
        st.write("---")
        st.write(f"**Total Portfolio Value:** ${total_portfolio_value:,.0f}")
