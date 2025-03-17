import os
import pandas as pd

class RiskMetrics:
    def __init__(self, output_folder):
        self.output_folder = output_folder

    def daily_variance(self):
        df = pd.read_csv(os.path.join(self.output_folder, 'portfolio_total.csv'))
        daily_returns = df['pct_change'].dropna()
        daily_variance = daily_returns.var()

        return daily_variance

    def annualized_variance(self):
        df = pd.read_csv(os.path.join(self.output_folder, 'portfolio_total.csv'))
        annualized_variance = self.daily_variance() * 252
        # print(f"Annualized Variance: {annualized_variance:.4f}")
        return annualized_variance

    def annualized_volatility(self):
        annualized_volatility = self.annualized_variance() ** 0.5
        # print(f"Annualized Volatility: {annualized_volatility:.4f}")
        return annualized_volatility

    def daily_volatility(self):
        df = pd.read_csv(os.path.join(self.output_folder, 'portfolio_total.csv'))
        # daily_return = df['Total_Portfolio_Value'].pct_change()
        daily_return = df['pct_change'].dropna()
        daily_volatility = daily_return.std()

        # print(f"Daily Volatility: {daily_volatility:.4f}")
        return daily_volatility

    def daily_downside_variance(self):
        df = pd.read_csv(os.path.join(self.output_folder, 'portfolio_total.csv'))
        daily_return = df['pct_change'].dropna()
        downside_returns = daily_return[daily_return < 0]
        downside_variance = downside_returns.var()
        # print(f"Daily Downside Variance: {downside_variance:.4f}")
        return downside_variance

    def annualized_downside_variance(self):
        annualized_downside_variance = self.daily_downside_variance() * 252
        # print(f"Annualized Downside Variance: {annualized_downside_variance:.4f}")
        return annualized_downside_variance

    def daily_downside_volatility(self):
        daily_downside_volatility = self.daily_downside_variance() ** 0.5
        # print(f"Daily Downside Volatility: {daily_downside_volatility:.4f}")
        return daily_downside_volatility

    def annualized_downside_volatility(self):
        annualized_downside_volatility = self.annualized_downside_variance() ** 0.5
        # print(f"Annualized Downside Volatility: {annualized_downside_volatility:.4f}")
        return annualized_downside_volatility

    def maximum_drawdown(self):
        # calculate the maximum drawdown
        df = pd.read_csv(os.path.join(self.output_folder, 'portfolio_total.csv'))
        daily_return = df['pct_change'].dropna()
        
        return daily_return.min()