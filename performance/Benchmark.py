import os
import pandas as pd

class Benchmark:
    def __init__(self, output_folder):
        self.output_folder = output_folder

    def get_spy_benchmark(self):
        prices = pd.read_csv(os.path.join(self.output_folder, 'prices.csv'))
        dividend_df = pd.read_csv(os.path.join(self.output_folder, 'dividends.csv'))[['Date', 'SPY']]

        # upon further thought, I guess dividends are baked into the price?
        dividend_df['Date'] = pd.to_datetime(dividend_df['Date'])
        dividend_df = dividend_df.set_index('Date')
        dividend_df['SPY'].fillna(0)

        # create a new dataframe with only the date and SPY columns
        benchmark_df = prices[['Date', 'SPY']].copy()
        benchmark_df['Date'] = pd.to_datetime(benchmark_df['Date'])
        benchmark_df = benchmark_df.sort_values('Date')

        # use exchange_rates.csv to convert USD to CAD in the SPY column
        exchange_rates = pd.read_csv(os.path.join(self.output_folder, 'exchange_rates.csv'))
        exchange_rates['Date'] = pd.to_datetime(exchange_rates['Date'])
        exchange_rates = exchange_rates.sort_values('Date')
        exchange_rates.set_index('Date', inplace=True)

        benchmark_df.set_index('Date', inplace=True)
        benchmark_df['SPY'] = (benchmark_df['SPY'] + dividend_df['SPY'].cumsum()) * exchange_rates['USD']
        # benchmark_df['SPY'] = (benchmark_df['SPY']) * exchange_rates['USD']
        benchmark_df['pct_change'] = benchmark_df['SPY'].pct_change()

        # can write this to csv if we want but don't rly need it so I left it for now
        return benchmark_df
    
    def create_custom_benchmark(self):
        STARTING_CASH = 101644.99
        exchange_rates = pd.read_csv(os.path.join(self.output_folder, 'exchange_rates.csv'))
        prices = pd.read_csv(os.path.join(self.output_folder, 'prices.csv'))
        prices['Date'] = pd.to_datetime(prices['Date'])
        dividends = pd.read_csv(os.path.join(self.output_folder, 'dividends.csv'))[['Date', 'XIU.TO', 'SPY', 'AGG', 'XBB.TO']]
        initial_exchange_rate = exchange_rates['USD'].iloc[0]

        # assuming we can buy fractional shares for now I guess or else use //
        # and leave remainder as cash
        xiu_initial_shares = 0.3*STARTING_CASH/prices['XIU.TO'].iloc[0]
        spy_initial_shares = 0.3*STARTING_CASH/(prices['SPY'].iloc[0] * initial_exchange_rate)
        agg_initial_shares = 0.2*STARTING_CASH/(prices['AGG'].iloc[0] * initial_exchange_rate)
        xbb_initial_shares = 0.2*STARTING_CASH/prices['XBB.TO'].iloc[0]

        xiu_dividends = dividends['XIU.TO'].cumsum() * xiu_initial_shares
        spy_dividends = dividends['SPY'].cumsum() * spy_initial_shares * exchange_rates['USD']
        agg_dividends = dividends['AGG'].cumsum() * agg_initial_shares * exchange_rates['USD']
        xbb_dividends = dividends['XBB.TO'].cumsum() * xbb_initial_shares

        xiu_value = xiu_initial_shares * prices['XIU.TO'] + xiu_dividends
        spy_value = (spy_initial_shares * prices['SPY'] * exchange_rates['USD'] + spy_dividends).rename('SPY')
        agg_value = (agg_initial_shares * prices['AGG'] * exchange_rates['USD'] + agg_dividends).rename('AGG')
        xbb_value = xbb_initial_shares * prices['XBB.TO'] + xbb_dividends

        # combine the above four value variables into one dataframe with the date index
        custom_benchmark = pd.concat([xiu_value, spy_value, agg_value, xbb_value], axis=1)
        custom_benchmark['Total'] = custom_benchmark.sum(axis=1)
        custom_benchmark['Date'] = prices['Date']
        custom_benchmark.set_index('Date', inplace=True)
        custom_benchmark['pct_change'] = custom_benchmark['Total'].pct_change()
        print("Custom Benchmark:", custom_benchmark.head())
        
        #output the custom benchmark to a csv file
        custom_benchmark.to_csv(os.path.join(self.output_folder, 'custom_benchmark.csv'), index=True)

    def benchmark_variance(self, benchmark='custom'):
        if benchmark == 'custom':
            benchmark_df = pd.read_csv(os.path.join(self.output_folder, 'custom_benchmark.csv'))
        else:
            benchmark_df = self.get_spy_benchmark()
        
        daily_benchmark_variance = benchmark_df['pct_change'].dropna().var()
        annualized_benchmark_variance = daily_benchmark_variance * 252
        return daily_benchmark_variance, annualized_benchmark_variance
    
    def benchmark_volatility(self, benchmark='custom'):
        if benchmark == 'custom':
            benchmark_df = pd.read_csv(os.path.join(self.output_folder, 'custom_benchmark.csv'))
        else:
            benchmark_df = self.get_spy_benchmark()
        
        daily_benchmark_volatility = benchmark_df['pct_change'].dropna().std()
        annualized_benchmark_volatility = daily_benchmark_volatility * (252 ** 0.5)

        return daily_benchmark_volatility, annualized_benchmark_volatility
    
    def benchmark_average_return(self, benchmark='custom'):
        if benchmark == 'custom':
            benchmark_df = pd.read_csv(os.path.join(self.output_folder, 'custom_benchmark.csv'))
        else:
            benchmark_df = self.get_spy_benchmark()
        daily_benchmark_return = benchmark_df['pct_change'].dropna().mean()
        annualized_benchmark_return = (1+daily_benchmark_return) ** 252 - 1

        return daily_benchmark_return, annualized_benchmark_return