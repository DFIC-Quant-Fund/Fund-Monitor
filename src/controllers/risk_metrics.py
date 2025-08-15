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

import pandas as pd

class RiskMetrics:
    def __init__(self, df):
        self.df = df

    def daily_variance(self):
        daily_returns = self.df['pct_change'].dropna()
        daily_variance = daily_returns.var()

        return daily_variance

    def annualized_variance(self):
        annualized_variance = self.daily_variance(self.df) * 252
        # print(f"Annualized Variance: {annualized_variance:.4f}")
        return annualized_variance

    def annualized_volatility(self):
        annualized_volatility = self.annualized_variance(self.df) ** 0.5
        # print(f"Annualized Volatility: {annualized_volatility:.4f}")
        return annualized_volatility

    def daily_volatility(self):
        # self.df = pd.read_csv(os.path.join(self.output_folder, 'portfolio_total.csv'))
        # daily_return = self.df['Total_Portfolio_Value'].pct_change()
        daily_return = self.df['pct_change'].dropna()
        daily_volatility = daily_return.std()

        # print(f"Daily Volatility: {daily_volatility:.4f}")
        return daily_volatility

    def daily_downside_variance(self):
        daily_return = self.df['pct_change'].dropna()
        downside_returns = daily_return[daily_return < 0]
        downside_variance = downside_returns.var()
        # print(f"Daily Downside Variance: {downside_variance:.4f}")
        return downside_variance

    def annualized_downside_variance(self):
        annualized_downside_variance = self.daily_downside_variance(self.df) * 252
        # print(f"Annualized Downside Variance: {annualized_downside_variance:.4f}")
        return annualized_downside_variance

    def daily_downside_volatility(self):
        daily_downside_volatility = self.daily_downside_variance(self.df) ** 0.5
        # print(f"Daily Downside Volatility: {daily_downside_volatility:.4f}")
        return daily_downside_volatility

    def annualized_downside_volatility(self):
        annualized_downside_volatility = self.annualized_downside_variance(self.df) ** 0.5
        # print(f"Annualized Downside Volatility: {annualized_downside_volatility:.4f}")
        return annualized_downside_volatility

    def maximum_drawdown(self):
        # calculate the maximum drawdown
        daily_return = self.df['pct_change'].dropna()
        
        return daily_return.min()

    def sharpe_ratio(self, risk_free_rate: float):
        daily_return = self.df['pct_change'].dropna()
        daily_sharpe_ratio = (daily_return.mean() - risk_free_rate/252) / daily_return.std()
        annualized_sharpe_ratio = daily_sharpe_ratio * (252 ** 0.5)
        return daily_sharpe_ratio, annualized_sharpe_ratio

    def sortino_ratio(self, risk_free_rate: float):
        daily_return = self.df['pct_change'].dropna()
        downside_returns = daily_return[daily_return < 0]
        daily_sortino_ratio = (daily_return.mean() - risk_free_rate/252) / downside_returns.std()
        annualized_sortino_ratio = daily_sortino_ratio * (252 ** 0.5)
        return daily_sortino_ratio, annualized_sortino_ratio