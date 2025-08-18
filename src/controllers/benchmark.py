"""
Benchmark data management and calculation module.

This module handles benchmark-related operations and calculations.
It provides methods for:
- Retrieving and processing SPY benchmark data
- Reading custom benchmark totals
- Calculating benchmark-specific metrics (returns, variance, volatility)
"""

import os
import pandas as pd

# TODO: This is a temporary solution to get the benchmark data.

class Benchmark:
    def __init__(self, useSpy: bool = False):
        self.OUTPUT_PATH = "data/benchmark/output"

        if useSpy:
            self.benchmark_df = self.get_spy_benchmark()
        else:
            # Read prebuilt totals
            self.benchmark_df = pd.read_csv(os.path.join(self.OUTPUT_PATH, 'portfolio_total.csv'))
            if 'Date' in self.benchmark_df.columns:
                self.benchmark_df['Date'] = pd.to_datetime(self.benchmark_df['Date'])
            # Ensure daily % change exists
            if 'Total_Portfolio_Value' in self.benchmark_df.columns:
                self.benchmark_df['pct_change'] = self.benchmark_df['Total_Portfolio_Value'].pct_change()
            elif 'Total Mkt Val' in self.benchmark_df.columns:
                self.benchmark_df['pct_change'] = self.benchmark_df['Total Mkt Val'].pct_change()

    def get_spy_benchmark(self) -> pd.DataFrame:
        prices = pd.read_csv(os.path.join(self.OUTPUT_PATH, 'prices.csv'))
        prices['Date'] = pd.to_datetime(prices['Date'])
        price_series = prices.set_index('Date')['SPY']

        # Dividend income per day for SPY in USD-equivalent terms (as built by the builder)
        div_df = pd.read_csv(os.path.join(self.OUTPUT_PATH, 'dividend_income.csv'))[['Date', 'SPY']]
        div_df['Date'] = pd.to_datetime(div_df['Date'])
        div_series = div_df.set_index('Date')['SPY']

        # Align to price index and fill missing with zeros
        div_series = div_series.reindex(price_series.index).fillna(0.0)
        div_cumsum = div_series.cumsum()

        benchmark_df = price_series.to_frame(name='Price').copy()
        benchmark_df['dividends cumsum'] = div_cumsum
        benchmark_df['Total'] = benchmark_df['Price'] + benchmark_df['dividends cumsum']
        benchmark_df['pct_change'] = benchmark_df['Total'].pct_change()
        benchmark_df.reset_index(inplace=True)
        benchmark_df.rename(columns={'index': 'Date'}, inplace=True)
        return benchmark_df

    def benchmark_variance(self):
        daily_benchmark_variance = self.benchmark_df['pct_change'].dropna().var()
        annualized_benchmark_variance = daily_benchmark_variance * 252
        return daily_benchmark_variance, annualized_benchmark_variance

    def benchmark_volatility(self):
        daily_benchmark_volatility = self.benchmark_df['pct_change'].dropna().std()
        annualized_benchmark_volatility = daily_benchmark_volatility * (252 ** 0.5)
        return daily_benchmark_volatility, annualized_benchmark_volatility

    def benchmark_average_return(self):
        daily_benchmark_return = self.benchmark_df['pct_change'].dropna().mean()
        annualized_benchmark_return = (1 + daily_benchmark_return) ** 252 - 1
        return daily_benchmark_return, annualized_benchmark_return


