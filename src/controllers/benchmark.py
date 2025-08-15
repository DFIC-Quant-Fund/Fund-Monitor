"""
Benchmark data management and calculation module.

This module handles benchmark-related operations and calculations.
It provides methods for:
- Retrieving and processing SPY benchmark data
- Creating and managing custom benchmarks
- Calculating benchmark-specific metrics (returns, variance, volatility)
- Managing benchmark inception returns

This module focuses on benchmark data management and calculations.
"""

import os
import pandas as pd

class Benchmark:
    def __init__(self, useSpy=False):
        self.OUTPUT_PATH = "data/benchmark/output"

        if useSpy:
            self.benchmark_df = self.get_spy_benchmark()
        else:
            self.benchmark_df = pd.read_csv(os.path.join(self.OUTPUT_PATH, 'custom_benchmark.csv'))
        

    def get_spy_benchmark(self):
        prices = pd.read_csv(os.path.join(self.OUTPUT_PATH, 'prices.csv'))
        dividend_df = pd.read_csv(os.path.join(self.OUTPUT_PATH, 'dividends.csv'))[['Date', 'SPY']]

        dividend_df['Date'] = pd.to_datetime(dividend_df['Date'])
        dividend_df['SPY'].fillna(0)

        # create a new dataframe with only the date and SPY columns
        benchmark_df = prices[['Date', 'SPY']].copy()
        benchmark_df.rename(columns={'SPY': 'Price'}, inplace=True)
        benchmark_df['dividends cumsum'] = dividend_df['SPY'].values.cumsum()

        benchmark_df['Total'] = benchmark_df['Price'] + benchmark_df['dividends cumsum']
        benchmark_df['pct_change'] = benchmark_df['Total'].pct_change().fillna(0)

        # NOTE: this is still all in USD which is fine since we are comparing it by percentages
        # can write this to csv if we want but don't rly need it so I left it for now
        return benchmark_df
    
    def create_custom_benchmark(self):
        STARTING_CASH = 101644.99
        prices = pd.read_csv(os.path.join(self.OUTPUT_PATH, 'prices.csv'))[['Date', 'XIU.TO', 'SPY', 'AGG', 'XBB.TO']]
        prices['Date'] = pd.to_datetime(prices['Date'])

        exchange_rates = pd.read_csv(os.path.join(self.OUTPUT_PATH, 'exchange_rates.csv'))
        exchange_rates['Date'] = pd.to_datetime(exchange_rates['Date'])
        initial_exchange_rate = exchange_rates['USD'].iloc[0]

        # dividends.csv is $/share dividend payments
        dividend_payments = pd.read_csv(os.path.join(self.OUTPUT_PATH, 'dividends.csv'))[['Date', 'XIU.TO', 'SPY', 'AGG', 'XBB.TO']]

        xiu_shares = 0.3*STARTING_CASH/prices['XIU.TO'].iloc[0]
        spy_shares = 0.3*STARTING_CASH/(prices['SPY'].iloc[0] * initial_exchange_rate)
        agg_shares = 0.2*STARTING_CASH/(prices['AGG'].iloc[0] * initial_exchange_rate)
        xbb_shares = 0.2*STARTING_CASH/prices['XBB.TO'].iloc[0]

        # get dividend data
        dividends = dividend_payments.copy()
        dividends['Date'] = pd.to_datetime(dividends['Date'])

        dividends['XIU.TO'] = dividends['XIU.TO'] * xiu_shares
        dividends['SPY'] = dividends['SPY'] * spy_shares * exchange_rates['USD']
        dividends['AGG'] = dividends['AGG'] * agg_shares * exchange_rates['USD']
        dividends['XBB.TO'] = dividends['XBB.TO'] * xbb_shares

        # calculate the market value of each asset
        xiu_values = xiu_shares * prices['XIU.TO']
        spy_values = (spy_shares * prices['SPY'] * exchange_rates['USD']).rename('SPY')
        agg_values = (agg_shares * prices['AGG'] * exchange_rates['USD']).rename('AGG')
        xbb_values = xbb_shares * prices['XBB.TO']

        # concatenate the values of each asset into a single dataframe
        custom_benchmark = pd.concat([xiu_values, spy_values, agg_values, xbb_values], axis=1)
        custom_benchmark['Date'] = prices['Date']
        custom_benchmark.set_index('Date', inplace=True)
        custom_benchmark['XIU.TO dividends cumsum'] = dividends['XIU.TO'].cumsum().values
        custom_benchmark['SPY dividends cumsum'] = dividends['SPY'].cumsum().values
        custom_benchmark['AGG dividends cumsum'] = dividends['AGG'].cumsum().values
        custom_benchmark['XBB.TO dividends cumsum'] = dividends['XBB.TO'].cumsum().values
        custom_benchmark['Total Mkt Val'] = custom_benchmark.sum(axis=1)
        custom_benchmark['pct_change'] = custom_benchmark['Total Mkt Val'].pct_change()

        #output the custom benchmark to a csv file
        custom_benchmark.to_csv(os.path.join(self.OUTPUT_PATH, 'custom_benchmark.csv'), index=True)

    def benchmark_inception_return(self):
        inception_value = self.benchmark_df['Total Mkt Val'].iloc[0]
        latest_value = self.benchmark_df['Total Mkt Val'].iloc[-1]

        inception_return = (latest_value - inception_value) / inception_value

        return inception_return

    def spy_inception_return(self):
        benchmark_df = self.get_spy_benchmark()
        inception_value = benchmark_df['Total'].iloc[0]
        latest_value = benchmark_df['Total'].iloc[-1]

        inception_return = (latest_value - inception_value) / inception_value

        return inception_return

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
        annualized_benchmark_return = (1+daily_benchmark_return) ** 252 - 1

        return daily_benchmark_return, annualized_benchmark_return