"""
Data processing and visualization module.

This module handles data aggregation and visualization tasks.
It provides methods for:
- Aggregating market values, cash, and dividend data
- Creating portfolio value plots
- Data preprocessing for other modules

This module focuses on data processing and visualization, serving as a utility for other modules.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt


class DataProcessor:
    def __init__(self, output_folder):
        self.output_folder = output_folder

    def aggregate_data(self, market_values_file, cash_file, dividends_file, output_file):
        market_values = pd.read_csv(market_values_file)
        cash_value = pd.read_csv(cash_file)
        market_values['Date'] = pd.to_datetime(market_values['Date'])
        cash_value['Date'] = pd.to_datetime(cash_value['Date'])
        
        # Get numeric columns for market values (excluding Date)
        numeric_columns = market_values.columns.drop('Date')
        market_values[numeric_columns] = market_values[numeric_columns].apply(pd.to_numeric, errors='coerce')
        
        # Use Total_CAD column from cash file (matches portfolio_csv_builder.py)
        cash_value['Total_CAD'] = cash_value['Total_CAD'].apply(pd.to_numeric, errors='coerce')

        # Load dividends data
        dividends = pd.read_csv(dividends_file)
        dividends['Date'] = pd.to_datetime(dividends['Date'])
        
        # Calculate total market value for each date
        market_values['Total_Market_Value'] = market_values[numeric_columns].sum(axis=1)
        
        # Calculate total portfolio value: market value + cash (which already includes dividends)
        # This matches the calculation in portfolio_csv_builder.py print_final_values method
        market_values['Total_Portfolio_Value'] = market_values['Total_Market_Value'] + cash_value['Total_CAD']
        
        # Create output dataframe with required columns
        output_df = market_values[['Date', 'Total_Portfolio_Value']].copy()
        output_df = output_df.sort_values('Date')
        output_df['pct_change'] = output_df['Total_Portfolio_Value'].pct_change()

        output_df.to_csv(output_file, index=False, float_format='%.6f')
    
    def plot_portfolio_value(self):
        df = pd.read_csv(os.path.join(self.output_folder, 'portfolio_total.csv'))
        df['Date'] = pd.to_datetime(df['Date'])
        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(df['Date'],df['Total_Portfolio_Value'],color='black',linewidth=2,label='Portfolio Value')
        ax.set_title('Portfolio Value (CAD)', fontsize=16, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Amount (CAD)', fontsize=12)
        ax.legend(loc='lower right')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_folder, 'portfolio_plot.png'))