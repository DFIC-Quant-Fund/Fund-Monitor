"""
Market comparison metrics module.

This module calculates metrics that compare portfolio performance against market benchmarks.
It provides methods for:
- Beta calculation: Portfolio volatility relative to benchmark
- Alpha calculation: Excess return relative to benchmark
- Risk premium calculations
- Risk-adjusted return metrics

This module focuses on comparative analysis and assumes benchmark data is available.
"""

from .benchmark import Benchmark
from .returns_calculator import ReturnsCalculator
from .risk_metrics import RiskMetrics
from ..config.logging_config import get_logger

# Set up logger for this module
logger = get_logger(__name__)


class MarketComparison:
    def __init__(self, df=None, useSpy: bool = False, risk_free_rate: float = 0.02):
        # Mirror Benchmark's constructor pattern: local path constant via Benchmark and a chosen source
        self.benchmark_instance = Benchmark(useSpy=useSpy)
        self.df = df
        self.RISK_FREE_RATE = risk_free_rate

    def beta(self):
        # Use the configured benchmark instance
        benchmark_df = self.benchmark_instance.benchmark_df
        
        daily_portfolio_return = self.df['pct_change'].dropna()
        
        # Handle empty or NaN values in benchmark pct_change
        if 'pct_change' in benchmark_df.columns:
            daily_benchmark_return = benchmark_df['pct_change'].dropna()
        else:
            # If pct_change column doesn't exist, calculate it
            benchmark_df['pct_change'] = benchmark_df['Total Mkt Val'].pct_change()
            daily_benchmark_return = benchmark_df['pct_change'].dropna()
        
        # Align on dates to ensure matching observations
        aligned = daily_portfolio_return.align(daily_benchmark_return, join='inner')
        daily_portfolio_return, daily_benchmark_return = aligned
        if len(daily_portfolio_return) == 0:
            return 0.0
        
        daily_benchmark_var, _ = self.benchmark_instance.benchmark_variance()
        if daily_benchmark_var == 0:
            return 0.0  # Avoid division by zero
        
        covariance = daily_portfolio_return.cov(daily_benchmark_return)
        beta = covariance / daily_benchmark_var

        return beta
        

    def alpha(self): 
        try:
            benchmark_returns = self.benchmark_instance.benchmark_average_return()
            annual_benchmark_return = benchmark_returns[1]  # Get the annualized return
            
            # Load portfolio data for ReturnsCalculator
            portfolio_performance = ReturnsCalculator(self.df)
            
            logger.debug(f"annual_benchmark_return: {annual_benchmark_return}")
            beta_value = self.beta()
            alpha = (portfolio_performance.annualized_average_return() - self.RISK_FREE_RATE) - beta_value * (annual_benchmark_return - self.RISK_FREE_RATE)
            return alpha
        except Exception as e:
            logger.exception(f"Could not calculate alpha: {e}")
            return 0.0
        
    def portfolio_risk_premium(self):
        try:
            # Load portfolio data for ReturnsCalculator
            portfolio_performance = ReturnsCalculator(self.df)
            return portfolio_performance.annualized_average_return() - self.RISK_FREE_RATE
        except Exception as e:
            logger.exception(f"Could not calculate portfolio risk premium: {e}")
            return 0.0

    def treynor_ratio(self):
        try:
            return self.portfolio_risk_premium() / self.beta()
        except Exception as e:
            logger.exception(f"Could not calculate treynor ratio: {e}")
            return 0.0

    def information_ratio(self):
        try:
            # Read portfolio returns
            daily_portfolio_returns = self.df['pct_change'].dropna()
            daily_benchmark_returns = self.benchmark_instance.benchmark_df['pct_change'].dropna()

            # Align on dates to avoid NaNs due to mismatch
            aligned = daily_portfolio_returns.align(daily_benchmark_returns, join='inner')
            daily_portfolio_returns, daily_benchmark_returns = aligned
            if len(daily_portfolio_returns) == 0:
                return 0.0, 0.0

            # Excess returns and IR
            excess_returns = daily_portfolio_returns - daily_benchmark_returns
            daily_information_ratio = excess_returns.mean() / excess_returns.std()
            annualized_information_ratio = daily_information_ratio * (252 ** 0.5)
            return daily_information_ratio, annualized_information_ratio
        except Exception as e:
            logger.exception(f"Could not calculate information ratio: {e}")
            return 0.0, 0.0

    def risk_adjusted_return(self):
        try:
            risk_metrics = RiskMetrics(self.df, self.RISK_FREE_RATE)
            benchmark_vol = self.benchmark_instance.benchmark_volatility()[1]
            portfolio_volatility = risk_metrics.annualized_volatility()
            portfolio_risk_prem = self.portfolio_risk_premium()
            risk_adjusted_return = portfolio_risk_prem * benchmark_vol / portfolio_volatility + self.RISK_FREE_RATE
            
            return risk_adjusted_return
        except Exception as e:
            logger.exception(f"Could not calculate risk adjusted return: {e}")
            return 0.0