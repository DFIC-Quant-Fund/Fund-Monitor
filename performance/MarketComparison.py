import os
import pandas as pd
from .Benchmark import Benchmark
from .PortfolioPerformance import PortfolioPerformance
from .RiskMetrics import RiskMetrics


class MarketComparison:
    def __init__(self, output_folder):
        self.output_folder = output_folder

    def beta(self, benchmark='custom'):
        benchmark_class = Benchmark(self.output_folder)
        if benchmark == 'custom':
            benchmark_df = pd.read_csv(os.path.join(self.output_folder, 'custom_benchmark.csv'))
        else:
            benchmark_df = benchmark_class.get_spy_benchmark()
        
        df = pd.read_csv(os.path.join(self.output_folder, 'portfolio_total.csv'))
        daily_portfolio_return = df['pct_change'].dropna()
        daily_benchmark_var, _ = benchmark_class.benchmark_variance(benchmark)
        covariance = daily_portfolio_return.cov(benchmark_df['pct_change'])
        beta = covariance / daily_benchmark_var

        return beta
        

    def alpha(self, risk_free_rate, benchmark='custom'): 
        benchmark_class = Benchmark(self.output_folder)
        annual_benchmark_return = benchmark_class.benchmark_average_return(benchmark)[1]
        portfolio_performance = PortfolioPerformance(self.output_folder)
        print("benchmark: ", benchmark)
        print("annual_benchmark_return ", annual_benchmark_return)
        alpha = (portfolio_performance.annualized_average_return() - risk_free_rate) - self.beta() * (annual_benchmark_return - risk_free_rate)

        return alpha
        
    def portfolio_risk_premium(self, risk_free_return):
        portfolio_performance = PortfolioPerformance(self.output_folder)
        return portfolio_performance.annualized_average_return() - risk_free_return

    def risk_adjusted_return(self, risk_free_return):
        risk_metrics = RiskMetrics(self.output_folder)
        benchmark = Benchmark(self.output_folder)
        benchmark_vol = benchmark.benchmark_volatility()[1]
        portfolio_volatility = risk_metrics.annualized_volatility()
        portfolio_risk_prem = self.portfolio_risk_premium(risk_free_return)
        risk_adjusted_return = portfolio_risk_prem * benchmark_vol / portfolio_volatility + risk_free_return
        
        return risk_adjusted_return