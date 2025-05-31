import os
import pandas as pd
from .Benchmark import Benchmark
from .MarketComparison import MarketComparison
from .PortfolioPerformance import PortfolioPerformance

class Ratios:
    def __init__(self, output_folder):
        self.output_folder = output_folder

    def sharpe_ratio(self, risk_free_rate):
        df = pd.read_csv(os.path.join(self.output_folder, 'portfolio_total.csv'))
        daily_return = df['pct_change'].dropna()
        daily_sharpe_ratio = (daily_return.mean() - risk_free_rate/252) / daily_return.std()
        annualized_sharpe_ratio = daily_sharpe_ratio * (252 ** 0.5)

        return daily_sharpe_ratio, annualized_sharpe_ratio

    def sortino_ratio(self, risk_free_rate):
        df = pd.read_csv(os.path.join(self.output_folder, 'portfolio_total.csv'))
        daily_return = df['pct_change'].dropna()
        downside_returns = daily_return[daily_return < 0]
        daily_sortino_ratio = (daily_return.mean() - risk_free_rate/252) / downside_returns.std()
        annualized_sortino_ratio = daily_sortino_ratio * (252 ** 0.5)

        return daily_sortino_ratio, annualized_sortino_ratio
    
    def treynor_ratio(self, risk_free_return):
        market_comparison = MarketComparison(self.output_folder)
        return market_comparison.portfolio_risk_premium(risk_free_return) / market_comparison.beta()

    def information_ratio(self, benchmark='custom'):
        # Read portfolio returns
        df = pd.read_csv(os.path.join(self.output_folder, 'portfolio_total.csv'))
        daily_portfolio_returns = df['pct_change'].dropna()

        benchmark_class = Benchmark(self.output_folder)
        if benchmark == 'custom':
            benchmark_df = pd.read_csv(os.path.join(self.output_folder, 'custom_benchmark.csv'))
        else:
            benchmark_df = benchmark_class.get_spy_benchmark()
        
        # Get benchmark returns
        benchmark_class = Benchmark(self.output_folder)
        daily_benchmark_returns = benchmark_df['pct_change'].dropna()
        
        # Calculate excess returns (difference between portfolio and benchmark daily returns)
        excess_returns = daily_portfolio_returns - daily_benchmark_returns
        
        # Calculate daily information ratio
        daily_information_ratio = excess_returns.mean() / excess_returns.std()
        
        # Annualize the ratio
        annualized_information_ratio = daily_information_ratio * (252 ** 0.5)
        
        return daily_information_ratio, annualized_information_ratio