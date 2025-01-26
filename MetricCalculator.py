import numpy as np
import pandas as pd

class MetricCalculator:

    def __init__(self):
        pass

    def compounded_portfolio_return(self, df, column='Total'):
        df['Daily_Return'] = df[column].pct_change()  # Daily return = (P(t) - P(t-1)) / P(t-1)
        compounded_return = (1 + df['Daily_Return']).prod() - 1  # Product of (1 + daily returns)
        annualized_return = (1 + compounded_return)**252 - 1  # Annualizing assuming 252 trading days
        return compounded_return, annualized_return


    def average_portfolio_return(self, df, column='Total'):
        df['Daily_Return'] = df[column].pct_change()
        avg_daily_return = df['Daily_Return'].mean()
        avg_annualized_return = avg_daily_return * 252  # Annualize assuming 252 trading days
        return avg_daily_return, avg_annualized_return


    def portfolio_variance(self, df, column='Total'):
        df['Daily_Return'] = df[column].pct_change()
        daily_variance = df['Daily_Return'].var()
        annualized_variance = daily_variance * 252  # Annualize assuming 252 trading days
        return daily_variance, annualized_variance

    def portfolio_volatility(self, df, column='Total'):
        df['Daily_Return'] = df[column].pct_change()
        daily_volatility = df['Daily_Return'].std()
        annualized_volatility = daily_volatility * np.sqrt(252)  # Annualize assuming 252 trading days
        return daily_volatility, annualized_volatility

    def maximum_drawdown(self, df, column='Total'):
        df['Cumulative_Return'] = (1 + df['Daily_Return']).cumprod()
        df['Rolling_Max'] = df['Cumulative_Return'].cummax()
        df['Drawdown'] = df['Cumulative_Return'] / df['Rolling_Max'] - 1
        max_drawdown = df['Drawdown'].min()  # Max drawdown is the minimum of the drawdown series
        return max_drawdown

    def sharpe_ratio(self, df, risk_free_rate=0.05, column='Total'):
        df['Daily_Return'] = df[column].pct_change()
        excess_daily_return = df['Daily_Return'] - risk_free_rate / 252  # Adjust for daily risk-free rate
        sharpe_ratio_daily = excess_daily_return.mean() / excess_daily_return.std()
        sharpe_ratio_annualized = sharpe_ratio_daily * np.sqrt(252)  # Annualize
        return sharpe_ratio_daily, sharpe_ratio_annualized

    def beta(self, df, market_returns, column='Total'):
        df['Daily_Return'] = df[column].pct_change()
        cov_matrix = np.cov(df['Daily_Return'][1:], market_returns[1:])  # Covariance between portfolio and market
        beta = cov_matrix[0, 1] / market_returns.var()  # Covariance of returns / Variance of market returns
        return beta

    def alpha(self, df, market_returns, risk_free_rate=0.05, column='Total'):
        df['Daily_Return'] = df[column].pct_change()
        portfolio_return = df['Daily_Return'].mean() * 252  # Annualized portfolio return
        market_return = market_returns.mean() * 252  # Annualized market return
        beta_value = beta(self, df, market_returns, column)
        alpha = portfolio_return - (risk_free_rate + beta_value * (market_return - risk_free_rate))
        return alpha

    def sortino_ratio(self, df, risk_free_rate=0.05, column='Total'):
        df['Daily_Return'] = df[column].pct_change()
        negative_returns = df['Daily_Return'][df['Daily_Return'] < 0]
        downside_volatility = negative_returns.std()
        excess_daily_return = df['Daily_Return'] - risk_free_rate / 252
        sortino_ratio = excess_daily_return.mean() / downside_volatility
        sortino_ratio_annualized = sortino_ratio * np.sqrt(252)  # Annualize
        return sortino_ratio, sortino_ratio_annualized