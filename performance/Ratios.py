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
        # df = pd.read_csv('output/portfolio_total.csv')
        # daily_portfolio_return = df['pct_change'].dropna()
        # daily_benchmark_return = benchmark_df['pct_change'].dropna()
        benchmark_class = Benchmark(self.output_folder)
        _, annual_benchmark_return = benchmark_class.benchmark_average_return(benchmark)
        portfolio_performance = PortfolioPerformance(self.output_folder)
        # excess_returns = daily_portfolio_return - daily_benchmark_return
        excess_returns = portfolio_performance.annualized_average_return() - annual_benchmark_return
        # print("annualized_average_return of portfolio: ", annualized_average_return())
        # print("annual_benchmark_return: ", annual_benchmark_return)

        tracking_error = excess_returns.std() # this doesn't make sense rn since they're just scalars
        information_ratio = excess_returns.mean() / tracking_error

        return information_ratio