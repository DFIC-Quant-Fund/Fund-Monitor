"""
Portfolio returns calculation module.

This module provides comprehensive portfolio return calculations.
It handles:
- Period returns (1-day, 1-week, 1-month, YTD, 1-year, inception)
- Total return calculations
- Daily and annualized average returns

The module is designed to work with either a DataFrame or CSV file input.
"""

import os
import pandas as pd
from datetime import timedelta


class ReturnsCalculator:
    def __init__(self, portfolio_data=None, date=None, portfolio_column="Total_Portfolio_Value"):
        """
        Initialize the ReturnsCalculator.
        
        Args:
            output_folder (str, optional): Path to folder containing CSV files
            portfolio_data (pd.DataFrame, optional): DataFrame containing portfolio values
            date (str/datetime, optional): The date for performance calculation
            portfolio_column (str): Column name representing portfolio value
        """
        self.df = portfolio_data
        self.date = pd.to_datetime(date) if date else None
        self.portfolio_column = portfolio_column

    def valid_date(self):
        """
        Validate the date provided by the user. It must be an available date in the dataset.
        
        Returns:
            bool: True if the date is valid, False otherwise
        """
        return self.date in self.df['Date'].values

    def _closest_date(self, target_date, side='left'):
        """
        Finds the closest available date in the dataset.
        
        Args:
            target_date: The target date to search for
            side: 'left' to find the closest past date, 'right' for the closest future date
            
        Returns:
            The closest date found in the dataset
        """
        target_date = pd.to_datetime(target_date)
        valid_dates = self.df[self.df['Date'] <= target_date]['Date'] if side == 'left' else self.df[self.df['Date'] >= target_date]['Date']
        return valid_dates.max() if side == 'left' else valid_dates.min()

    def _get_value_by_date(self, date):
        """
        Retrieves the portfolio value on a specific date.
        
        Args:
            date: The date for which to fetch the portfolio value
            
        Returns:
            Portfolio value on the given date or None if unavailable
        """
        row = self.df[self.df['Date'] == date]
        return row[self.portfolio_column].values[0] if not row.empty else None

    def calculate_performance(self):
        """
        Calculates portfolio performance over multiple periods.
        
        Returns:
            dict: A dictionary containing returns for different periods
        """
        periods = {
            "one_day": self.date - timedelta(days=1),
            "one_week": self.date - timedelta(days=7),
            "one_month": self.date - timedelta(days=30),
            "ytd": pd.Timestamp(year=self.date.year, month=1, day=1),
            "one_year": self.date - timedelta(days=365),
            "inception": self.df['Date'].min()
        }

        performance = {}
        current_value = self._get_value_by_date(self.date)

        for key, period_date in periods.items():
            closest_date = self._closest_date(period_date, side='right' if key == 'ytd' else 'left')
            previous_value = self._get_value_by_date(closest_date)

            # Calculate return only if both values exist
            performance[key] = (current_value / previous_value - 1) * 100 if current_value and previous_value else None

        return performance

    def total_return(self):
        """
        Calculate the total return from inception to the latest date.
        
        Returns:
            float: Total return as a decimal
        """
        total_return = (self.df[self.portfolio_column].iloc[-1] - self.df[self.portfolio_column].iloc[0]) / self.df[self.portfolio_column].iloc[0]
        return total_return

    def daily_average_return(self):
        """
        Calculate the average daily return.
        
        Returns:
            float: Average daily return as a decimal
        """
        daily_returns = self.df['pct_change'].dropna()
        return daily_returns.mean()
    
    def annualized_average_return(self):
        """
        Calculate the annualized average return.
        
        Returns:
            float: Annualized average return as a decimal
        """
        daily_returns = self.df['pct_change'].dropna()
        average_daily_return = daily_returns.mean()
        return (1 + average_daily_return) ** 252 - 1 