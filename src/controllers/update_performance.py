"""
Performance update module for CSV operations.

This module handles the calculation and storage of performance metrics in CSV format.
It calculates returns for different time horizons (1-day, 1-week, 1-month, YTD, 1-year, and inception)
and saves them to CSV files in the appropriate data directory.

Usage:
    python update_performance.py fund                  # Run historical using all dates from portfolio_total.csv
    python update_performance.py fund yyyy-mm-dd       # Run for specific date
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
try:
    from .returns_calculator import ReturnsCalculator
    from .csv_writer import PerformanceCSVWriter
except ImportError:
    # Fallback for when running as script
    from returns_calculator import ReturnsCalculator
    from csv_writer import PerformanceCSVWriter

def update_performance_csv(fund, date=None):
    """
    Updates performance metrics for a given fund and date, saving to CSV.
    
    Args:
        fund (str): The fund name
        date (str, optional): The date to calculate metrics for. Defaults to today.
        
    Returns:
        dict: Dictionary containing performance metrics for different time horizons
    """
    # Set up paths
    input_file = os.path.join('data', fund, 'output', 'portfolio_total.csv')
    output_folder = os.path.join('data', fund, 'output')
    
    # Validate file existence
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Portfolio data file not found at {input_file}")
    
    # Load and preprocess data
    df = pd.read_csv(input_file)
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Use provided date or today
    if date is None:
        date = datetime.now().date()
    else:
        date = pd.to_datetime(date)
    
    # Calculate performance
    calculator = ReturnsCalculator(df, date)
    if not calculator.valid_date():
        print(f"Skipping performance calculation for {fund} on {date}, portfolio_total.csv data not available.")
        return None

    results = calculator.calculate_performance()
    
    # Save to CSV
    csv_writer = PerformanceCSVWriter(fund, output_folder)
    csv_writer.save_results(results, date)
    
    return results

def update_historical_performance(fund):
    """
    Updates performance metrics for all historical dates in the portfolio data.
    
    Args:
        fund (str): The fund name
    """
    input_file = os.path.join('data', fund, 'output', 'portfolio_total.csv')
    dates = pd.read_csv(input_file)['Date']
    
    for date in dates:
        print(f"Calculating performance for {fund} on {date}")
        update_performance_csv(fund, date)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("Usage: python update_performance.py <fund> <date> (date is optional, leave empty for historical run)")
    
    fund = sys.argv[1]
    date = sys.argv[2] if len(sys.argv) > 2 else None
    
    if date:
        update_performance_csv(fund, date)
    else:
        update_historical_performance(fund) 