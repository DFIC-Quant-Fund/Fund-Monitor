"""
Portfolio risk metrics calculation module.

This module calculates various risk metrics for portfolio analysis.
It provides methods for:
- Variance calculations (daily and annualized)
- Volatility calculations (daily and annualized)
- Downside risk metrics
- Maximum drawdown analysis

This module focuses solely on risk metric calculations and assumes input data is already processed.
"""

import os
import pandas as pd

class RiskMetrics:
    def __init__(self, output_folder):
        self.output_folder = output_folder

    def daily_variance(self, df):
        daily_returns = df['pct_change'].dropna()
        daily_variance = daily_returns.var()

        return daily_variance

    def annualized_variance(self, df):
        annualized_variance = self.daily_variance(df) * 252
        # print(f"Annualized Variance: {annualized_variance:.4f}")
        return annualized_variance

    def annualized_volatility(self, df):
        annualized_volatility = self.annualized_variance(df) ** 0.5
        # print(f"Annualized Volatility: {annualized_volatility:.4f}")
        return annualized_volatility

    def daily_volatility(self, df):
        # df = pd.read_csv(os.path.join(self.output_folder, 'portfolio_total.csv'))
        # daily_return = df['Total_Portfolio_Value'].pct_change()
        daily_return = df['pct_change'].dropna()
        daily_volatility = daily_return.std()

        # print(f"Daily Volatility: {daily_volatility:.4f}")
        return daily_volatility

    def daily_downside_variance(self, df):
        daily_return = df['pct_change'].dropna()
        downside_returns = daily_return[daily_return < 0]
        downside_variance = downside_returns.var()
        # print(f"Daily Downside Variance: {downside_variance:.4f}")
        return downside_variance

    def annualized_downside_variance(self, df):
        annualized_downside_variance = self.daily_downside_variance(df) * 252
        # print(f"Annualized Downside Variance: {annualized_downside_variance:.4f}")
        return annualized_downside_variance

    def daily_downside_volatility(self, df):
        daily_downside_volatility = self.daily_downside_variance(df) ** 0.5
        # print(f"Daily Downside Volatility: {daily_downside_volatility:.4f}")
        return daily_downside_volatility

    def annualized_downside_volatility(self, df):
        annualized_downside_volatility = self.annualized_downside_variance(df) ** 0.5
        # print(f"Annualized Downside Volatility: {annualized_downside_volatility:.4f}")
        return annualized_downside_volatility

    def maximum_drawdown(self, df):
        # calculate the maximum drawdown
        daily_return = df['pct_change'].dropna()
        
        return daily_return.min()