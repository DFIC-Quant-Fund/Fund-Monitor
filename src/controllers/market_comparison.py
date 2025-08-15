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

import os
import pandas as pd
try:
    from .benchmark import Benchmark
    from .returns_calculator import ReturnsCalculator
    from .risk_metrics import RiskMetrics
except ImportError:
    # Fallback for when running as script
    from benchmark import Benchmark
    from returns_calculator import ReturnsCalculator
    from risk_metrics import RiskMetrics


class MarketComparison:
    def __init__(self, useSpy: bool = False):
        # Mirror Benchmark's constructor pattern: local path constant via Benchmark and a chosen source
        self.benchmark_instance = Benchmark(useSpy=useSpy)

    def beta(self, df):
        # Use the configured benchmark instance
        benchmark_df = self.benchmark_instance.benchmark_df
        
        daily_portfolio_return = df['pct_change'].dropna()
        
        # Handle empty or NaN values in benchmark pct_change
        if 'pct_change' in benchmark_df.columns:
            daily_benchmark_return = benchmark_df['pct_change'].dropna()
        else:
            # If pct_change column doesn't exist, calculate it
            benchmark_df['pct_change'] = benchmark_df['Total Mkt Val'].pct_change()
            daily_benchmark_return = benchmark_df['pct_change'].dropna()
        
        # Ensure we have matching data
        min_length = min(len(daily_portfolio_return), len(daily_benchmark_return))
        if min_length == 0:
            return 0.0  # Return 0 if no valid data
        
        daily_portfolio_return = daily_portfolio_return.iloc[:min_length]
        daily_benchmark_return = daily_benchmark_return.iloc[:min_length]
        
        daily_benchmark_var, _ = self.benchmark_instance.benchmark_variance()
        if daily_benchmark_var == 0:
            return 0.0  # Avoid division by zero
        
        covariance = daily_portfolio_return.cov(daily_benchmark_return)
        beta = covariance / daily_benchmark_var

        return beta
        

    def alpha(self, risk_free_rate, df): 
        try:
            benchmark_returns = self.benchmark_instance.benchmark_average_return()
            annual_benchmark_return = benchmark_returns[1]  # Get the annualized return
            
            # Load portfolio data for ReturnsCalculator
            portfolio_performance = ReturnsCalculator(df)
            
            print("annual_benchmark_return", annual_benchmark_return)
            beta_value = self.beta(df)
            alpha = (portfolio_performance.annualized_average_return() - risk_free_rate) - beta_value * (annual_benchmark_return - risk_free_rate)
            return alpha
        except Exception as e:
            print(f"Warning: Could not calculate alpha: {e}")
            return 0.0
        
    def portfolio_risk_premium(self, risk_free_return, df):
        try:
            # Load portfolio data for ReturnsCalculator
            portfolio_performance = ReturnsCalculator(df)
            return portfolio_performance.annualized_average_return() - risk_free_return
        except Exception as e:
            print(f"Warning: Could not calculate portfolio risk premium: {e}")
            return 0.0

    def treynor_ratio(self, risk_free_return, df):
        try:
            return self.portfolio_risk_premium(risk_free_return, df) / self.beta(df)
        except Exception as e:
            print(f"Warning: Could not calculate treynor ratio: {e}")
            return 0.0

    def information_ratio(self, df, benchmark_is_custom: bool = True):
        try:
            # Read portfolio returns
            daily_portfolio_returns = df['pct_change'].dropna()

            # Select benchmark source
            benchmark_df = (Benchmark(useSpy=not benchmark_is_custom)).benchmark_df
            daily_benchmark_returns = benchmark_df['pct_change'].dropna()

            # Excess returns and IR
            excess_returns = daily_portfolio_returns - daily_benchmark_returns
            daily_information_ratio = excess_returns.mean() / excess_returns.std()
            annualized_information_ratio = daily_information_ratio * (252 ** 0.5)
            return daily_information_ratio, annualized_information_ratio
        except Exception as e:
            print(f"Warning: Could not calculate information ratio: {e}")
            return 0.0, 0.0

    def risk_adjusted_return(self, risk_free_return, df):
        try:
            risk_metrics = RiskMetrics(df)
            benchmark_vol = self.benchmark_instance.benchmark_volatility()[1]
            portfolio_volatility = risk_metrics.annualized_volatility()
            portfolio_risk_prem = self.portfolio_risk_premium(risk_free_return, df)
            risk_adjusted_return = portfolio_risk_prem * benchmark_vol / portfolio_volatility + risk_free_return
            
            return risk_adjusted_return
        except Exception as e:
            print(f"Warning: Could not calculate risk adjusted return: {e}")
            return 0.0