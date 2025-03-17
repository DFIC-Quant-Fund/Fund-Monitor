import os
import pandas as pd
import sys
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import timedelta

# def aggregate_data_old(input_file, output_file):
#     df = pd.read_csv(input_file)
#     df['Date'] = pd.to_datetime(df['Date'])
#     df = df.replace('', 0)
#     numeric_columns = df.columns.drop('Date')
#     df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors='coerce')

#     df['Total_Portfolio_Value'] = df[numeric_columns].sum(axis=1)
#     df_filtered = df[df['Total_Portfolio_Value'] > 0]
#     output_df = df_filtered[['Date', 'Total_Portfolio_Value']].copy()
#     output_df = output_df.sort_values('Date')
#     output_df['pct_change'] = output_df['Total_Portfolio_Value'].pct_change()

#     output_df.to_csv(output_file, index=False, float_format='%.6f')

#     print(output_df.head())

class DataProcessor:
    def __init__(self):
        pass

    def aggregate_data(self, market_values_file, cash_file, dividends_file, output_file):
        market_values = pd.read_csv(market_values_file)
        cash_value = pd.read_csv(cash_file)
        market_values['Date'] = pd.to_datetime(market_values['Date'])
        cash_value['Date'] = pd.to_datetime(cash_value['Date'])
        numeric_columns = market_values.columns.drop('Date')
        market_values[numeric_columns] = market_values[numeric_columns].apply(pd.to_numeric, errors='coerce')
        cash_value['Cash'] = cash_value['Cash'].apply(pd.to_numeric, errors='coerce')

        dividends = pd.read_csv(dividends_file)
        # get the sum of all dividends for each day and all previous days
        dividends['Date'] = pd.to_datetime(dividends['Date'])
        dividends['Daily Total'] = dividends[numeric_columns].sum(axis=1)
        dividends['Cum Sum'] = dividends['Daily Total'].cumsum()
        # print(dividends.head())

        market_values['Total_Portfolio_Value'] = market_values[numeric_columns].sum(axis=1) + cash_value['Cash'] + dividends['Cum Sum']
        output_df = market_values[['Date', 'Total_Portfolio_Value']].copy()
        output_df = output_df.sort_values('Date')
        output_df['pct_change'] = output_df['Total_Portfolio_Value'].pct_change()

        output_df.to_csv(output_file, index=False, float_format='%.6f')
    
    def plot_portfolio_value(self):
        df = pd.read_csv(os.path.join(output_folder, 'portfolio_total.csv'))
        df['Date'] = pd.to_datetime(df['Date'])
        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(df['Date'],df['Total_Portfolio_Value'],color='black',linewidth=2,label='Portfolio Value')
        ax.set_title('Portfolio Value (CAD)', fontsize=16, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Amount (CAD)', fontsize=12)
        ax.legend(loc='lower right')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(output_folder, 'portfolio_plot.png'))

class Benchmark:
    def __init__(self):
        pass

    def get_spy_benchmark(self):
        prices = pd.read_csv(os.path.join(output_folder, 'prices.csv'))
        dividend_df = pd.read_csv(os.path.join(output_folder, 'dividends.csv'))[['Date', 'SPY']]

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
        prices = pd.read_csv(os.path.join(output_folder, 'prices.csv'))[['Date', 'XIU.TO', 'SPY', 'AGG', 'XBB.TO']]
        prices['Date'] = pd.to_datetime(prices['Date'])

        exchange_rates = pd.read_csv(os.path.join(output_folder, 'exchange_rates.csv'))
        exchange_rates['Date'] = pd.to_datetime(exchange_rates['Date'])
        initial_exchange_rate = exchange_rates['USD'].iloc[0]

        # dividends.csv is $/share dividend payments
        dividend_payments = pd.read_csv(os.path.join(output_folder, 'dividends.csv'))[['Date', 'XIU.TO', 'SPY', 'AGG', 'XBB.TO']]

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
        custom_benchmark.to_csv(os.path.join(output_folder, 'custom_benchmark.csv'), index=True)

    def benchmark_variance(self, benchmark='custom'):
        if benchmark == 'custom':
            benchmark_df = pd.read_csv(os.path.join(output_folder, 'custom_benchmark.csv'))
        else:
            benchmark_df = self.get_spy_benchmark()
        
        daily_benchmark_variance = benchmark_df['pct_change'].dropna().var()
        annualized_benchmark_variance = daily_benchmark_variance * 252
        return daily_benchmark_variance, annualized_benchmark_variance
    
    def benchmark_volatility(self, benchmark='custom'):
        if benchmark == 'custom':
            benchmark_df = pd.read_csv(os.path.join(output_folder, 'custom_benchmark.csv'))
        else:
            benchmark_df = self.get_spy_benchmark()
        
        daily_benchmark_volatility = benchmark_df['pct_change'].dropna().std()
        annualized_benchmark_volatility = daily_benchmark_volatility * (252 ** 0.5)

        return daily_benchmark_volatility, annualized_benchmark_volatility
    
    def benchmark_average_return(self, benchmark='custom'):
        if benchmark == 'custom':
            benchmark_df = pd.read_csv(os.path.join(output_folder, 'custom_benchmark.csv'))
        else:
            benchmark_df = self.get_spy_benchmark()
        daily_benchmark_return = benchmark_df['pct_change'].dropna().mean()
        annualized_benchmark_return = (1+daily_benchmark_return) ** 252 - 1

        return daily_benchmark_return, annualized_benchmark_return
    
    def benchmark_inception_return(self):
        benchmark_df = pd.read_csv(os.path.join(output_folder, 'custom_benchmark.csv'))
        inception_value = benchmark_df['Total Mkt Val'].iloc[0]
        latest_value = benchmark_df['Total Mkt Val'].iloc[-1]

        inception_return = (latest_value - inception_value) / inception_value

        return inception_return

    def spy_inception_return(self):
        benchmark_df = self.get_spy_benchmark()
        inception_value = benchmark_df['Total'].iloc[0]
        latest_value = benchmark_df['Total'].iloc[-1]

        inception_return = (latest_value - inception_value) / inception_value

        return inception_return

class PortfolioPerformance:
    def __init__(self):
        pass
    
    def total_return(self):
        df = pd.read_csv(os.path.join(output_folder, 'portfolio_total.csv'))
        total_return = (df['Total_Portfolio_Value'].iloc[-1] - df['Total_Portfolio_Value'].iloc[0]) / df['Total_Portfolio_Value'].iloc[0]
        return total_return 

    def daily_average_return(self):
        df = pd.read_csv(os.path.join(output_folder, 'portfolio_total.csv'))
        daily_returns = df['pct_change'].dropna()
        average_return = daily_returns.mean()
        return average_return
    
    def annualized_average_return(self):
        df = pd.read_csv(os.path.join(output_folder, 'portfolio_total.csv'))
        daily_returns = df['pct_change'].dropna()
        average_daily_return = daily_returns.mean()
        annualized_avg_return = (1+average_daily_return) ** 252 - 1
        return annualized_avg_return
    
    def calculate_period_performance(self):
        df = pd.read_csv(os.path.join(output_folder, 'portfolio_total.csv'))
        df['Date'] = pd.to_datetime(df['Date'])

        latest_date = df['Date'].max()
        one_day = latest_date - timedelta(days=1)
        one_week = latest_date - timedelta(days=7)
        one_month = latest_date - timedelta(days=30)
        ytd = pd.Timestamp(year=latest_date.year, month=1, day=1)
        one_year = latest_date - timedelta(days=365)
        inception = df['Date'].min()

        def closest_date(target_date, side='left'):
            target_date = pd.to_datetime(target_date)
            if side == 'left':
                valid_dates = df[df['Date'] <= target_date]['Date']
                return valid_dates.max()
            elif side == 'right':
                valid_dates = df[df['Date'] >= target_date]['Date']
                return valid_dates.min()

        closest_1d = closest_date(one_day)
        closest_1w = closest_date(one_week)
        closest_1m = closest_date(one_month)
        closest_ytd = closest_date(ytd, side='right')
        closest_1y = closest_date(one_year)
        closest_inc = closest_date(inception)

        latest_value = df[df['Date'] == latest_date]['Total_Portfolio_Value'].values[0]
        one_day_value = df[df['Date'] == closest_1d]['Total_Portfolio_Value'].values[0]
        one_week_value = df[df['Date'] == closest_1w]['Total_Portfolio_Value'].values[0]
        one_month_value = df[df['Date'] == closest_1m]['Total_Portfolio_Value'].values[0]
        ytd_value = df[df['Date'] == closest_ytd]['Total_Portfolio_Value'].values[0]
        one_year_value = df[df['Date'] == closest_1y]['Total_Portfolio_Value'].values[0]
        inception_value = df[df['Date'] == closest_inc]['Total_Portfolio_Value'].values[0]

        one_day_return = (latest_value / one_day_value) - 1
        one_week_return = (latest_value / one_week_value) - 1
        one_month_return = (latest_value / one_month_value) - 1
        ytd_return = (latest_value / ytd_value) - 1
        one_year_return = (latest_value / one_year_value) - 1
        inception_return = (latest_value / inception_value) - 1

        return {
            "1d": one_day_return,
            "1w": one_week_return,
            "1m": one_month_return,
            "YTD": ytd_return,
            "1y": one_year_return,
            "Inception": inception_return
        }
    
    def get_fixed_income_info(self, tickers: list):
        df = pd.read_csv(os.path.join(output_folder, 'market_values.csv'))
        df_xrates = pd.read_csv(os.path.join(output_folder, 'exchange_rates.csv'))

        usd_tickers = []

        for t in tickers:
            try:
                currency = yf.Ticker(t).info['currency']
            except:
                currency = 'CAD'

            if currency == 'USD':
                df[t] = df[t] * df_xrates['USD'].iloc[-1]
                usd_tickers.append(t)

        current_mkt_vals = {ticker: df[ticker].iloc[-1] for ticker in tickers}
        total_mkt_vals = sum(current_mkt_vals.values())
        fi_market_shares = {ticker: current_mkt_vals[ticker] / total_mkt_vals for ticker in tickers}

        usd_total_mkt_val = sum([current_mkt_vals[ticker] for ticker in usd_tickers])
        USD_FI_mkt_shares = {ticker: current_mkt_vals[ticker] / usd_total_mkt_val for ticker in usd_tickers}

        # combine all these dictionaries into a dataframe
        data = {
            'Ticker': tickers,
            'Market Value': [current_mkt_vals[ticker] for ticker in tickers],
            'Total Market Share': [fi_market_shares[ticker] for ticker in tickers],
            'USD Market Share': [USD_FI_mkt_shares[ticker] if ticker in usd_tickers else 0 for ticker in tickers]
        }

        return pd.DataFrame(data)

class RiskMetrics:
    def __init__(self):
        pass

    def daily_variance(self):
        df = pd.read_csv(os.path.join(output_folder, 'portfolio_total.csv'))
        daily_returns = df['pct_change'].dropna()
        daily_variance = daily_returns.var()

        return daily_variance

    def annualized_variance(self):
        df = pd.read_csv(os.path.join(output_folder, 'portfolio_total.csv'))
        annualized_variance = self.daily_variance() * 252
        # print(f"Annualized Variance: {annualized_variance:.4f}")
        return annualized_variance

    def annualized_volatility(self):
        annualized_volatility = self.annualized_variance() ** 0.5
        # print(f"Annualized Volatility: {annualized_volatility:.4f}")
        return annualized_volatility

    def daily_volatility(self):
        df = pd.read_csv(os.path.join(output_folder, 'portfolio_total.csv'))
        # daily_return = df['Total_Portfolio_Value'].pct_change()
        daily_return = df['pct_change'].dropna()
        daily_volatility = daily_return.std()

        # print(f"Daily Volatility: {daily_volatility:.4f}")
        return daily_volatility

    def daily_downside_variance(self):
        df = pd.read_csv(os.path.join(output_folder, 'portfolio_total.csv'))
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
        df = pd.read_csv(os.path.join(output_folder, 'portfolio_total.csv'))
        daily_return = df['pct_change'].dropna()
        
        return daily_return.min()

class Ratios:
    def __init__(self):
        pass

    def sharpe_ratio(self, risk_free_rate):
        df = pd.read_csv(os.path.join(output_folder, 'portfolio_total.csv'))
        daily_return = df['pct_change'].dropna()
        daily_sharpe_ratio = (daily_return.mean() - risk_free_rate/252) / daily_return.std()
        annualized_sharpe_ratio = daily_sharpe_ratio * (252 ** 0.5)

        return daily_sharpe_ratio, annualized_sharpe_ratio

    def sortino_ratio(self, risk_free_rate):
        df = pd.read_csv(os.path.join(output_folder, 'portfolio_total.csv'))
        daily_return = df['pct_change'].dropna()
        downside_returns = daily_return[daily_return < 0]
        daily_sortino_ratio = (daily_return.mean() - risk_free_rate/252) / downside_returns.std()
        annualized_sortino_ratio = daily_sortino_ratio * (252 ** 0.5)

        return daily_sortino_ratio, annualized_sortino_ratio
    
    def treynor_ratio(self, risk_free_return):
        market_comparison = MarketComparison()
        return market_comparison.portfolio_risk_premium(risk_free_return) / market_comparison.beta()

    def information_ratio(self, benchmark='custom'):
        # df = pd.read_csv('output/portfolio_total.csv')
        # daily_portfolio_return = df['pct_change'].dropna()
        # daily_benchmark_return = benchmark_df['pct_change'].dropna()
        benchmark_class = Benchmark()
        _, annual_benchmark_return = benchmark_class.benchmark_average_return(benchmark)
        portfolio_performance = PortfolioPerformance()
        # excess_returns = daily_portfolio_return - daily_benchmark_return
        excess_returns = portfolio_performance.annualized_average_return() - annual_benchmark_return
        # print("annualized_average_return of portfolio: ", annualized_average_return())
        # print("annual_benchmark_return: ", annual_benchmark_return)

        tracking_error = excess_returns.std() # this doesn't make sense rn since they're just scalars
        information_ratio = excess_returns.mean() / tracking_error

        return information_ratio

class MarketComparison:
    def __init__(self):
        pass

    def beta(self, benchmark='custom'):
        benchmark_class = Benchmark()
        if benchmark == 'custom':
            benchmark_df = pd.read_csv(os.path.join(output_folder, 'custom_benchmark.csv'))
        else:
            benchmark_df = benchmark_class.get_spy_benchmark()
        
        df = pd.read_csv(os.path.join(output_folder, 'portfolio_total.csv'))
        daily_portfolio_return = df['pct_change'].dropna()
        daily_benchmark_var, _ = benchmark_class.benchmark_variance(benchmark)
        covariance = daily_portfolio_return.cov(benchmark_df['pct_change'])
        beta = covariance / daily_benchmark_var

        return beta
        

    def alpha(self, risk_free_rate, benchmark='custom'): 
        benchmark_class = Benchmark()
        annual_benchmark_return = benchmark_class.benchmark_average_return(benchmark)[1]
        portfolio_performance = PortfolioPerformance()
        alpha = (portfolio_performance.annualized_average_return() - risk_free_rate) - self.beta() * (annual_benchmark_return - risk_free_rate)

        return alpha
        
    def portfolio_risk_premium(self, risk_free_return):
        portfolio_performance = PortfolioPerformance()
        return portfolio_performance.annualized_average_return() - risk_free_return

    def risk_adjusted_return(self, risk_free_return):
        risk_metrics = RiskMetrics()
        benchmark = Benchmark()
        benchmark_vol = benchmark.benchmark_volatility()[1]
        portfolio_volatility = risk_metrics.annualized_volatility()
        portfolio_risk_prem = self.portfolio_risk_premium(risk_free_return)
        risk_adjusted_return = portfolio_risk_prem * benchmark_vol / portfolio_volatility + risk_free_return
        
        return risk_adjusted_return



def main():
    market_values_file = os.path.join(output_folder, "market_values.csv")
    cash_file = os.path.join(output_folder, "cash.csv") 
    dividend_file = os.path.join(output_folder, "dividend_values.csv") 
    output_file = os.path.join(output_folder, "portfolio_total.csv") 
    THREE_MTH_TREASURY_RATE = 0.0436 # 3-month treasury rate
    FIVE_PERCENT = 0.05

    data_processor = DataProcessor()
    benchmark = Benchmark()
    portfolio_performance = PortfolioPerformance()
    risk_metrics = RiskMetrics()
    ratios = Ratios()
    market_comparison = MarketComparison()

    # run these once only after running portfolio.py once
    data_processor.aggregate_data(market_values_file, cash_file, dividend_file, output_file)
    benchmark.create_custom_benchmark()
    period_metrics = portfolio_performance.calculate_period_performance()

    portfolio_performance.get_fixed_income_info(['XBB.TO', 'AGG', 'SPSB', 'XIU.TO'])

    print(f"Total Return including dividends,{portfolio_performance.total_return()*100:.2f}%\n")
    print(f"Daily Average Return,{portfolio_performance.daily_average_return()*100:.4f}%\n")
    print(f"Annualized Average Return,{portfolio_performance.annualized_average_return()*100:.2f}%\n")
    print(f"Daily Variance,{risk_metrics.daily_variance()*100:.4f}%\n")
    print(f"Annualized Variance,{risk_metrics.annualized_variance()*100:.2f}%\n")
    print(f"Daily Volatility,{risk_metrics.daily_volatility()*100:.4f}%\n")
    print(f"Annualized Volatility,{risk_metrics.annualized_volatility()*100:.2f}%\n")
    print(f"Daily Downside Variance,{risk_metrics.daily_downside_variance()*100:.4f}%\n")
    print(f"Annualized Downside Variance,{risk_metrics.annualized_downside_variance()*100:.2f}%\n")
    print(f"Daily Downside Volatility,{risk_metrics.daily_downside_volatility()*100:.4f}%\n")
    print(f"Annualized Downside Volatility,{risk_metrics.annualized_downside_volatility()*100:.2f}%\n")
    print(f"Sharpe Ratio (Annualized),{ratios.sharpe_ratio(THREE_MTH_TREASURY_RATE)[1]:.2f}\n")
    print(f"Sortino Ratio (Annualized),{ratios.sortino_ratio(THREE_MTH_TREASURY_RATE)[1]:.2f}\n")
    print(f"Maximum Drawdown,{risk_metrics.maximum_drawdown()*100:.2f}%\n")

    print(f"Custom Benchmark Variance (Daily),{benchmark.benchmark_variance()[0]*100:.4f}%\n")
    print(f"SPY Benchmark Variance (Daily),{benchmark.benchmark_variance(benchmark='SPY')[0]*100:.4f}%\n")
    print(f"Custom Benchmark Variance (Annualized),{benchmark.benchmark_variance()[1]*100:.2f}%\n")
    print(f"SPY Benchmark Variance (Annualized),{benchmark.benchmark_variance(benchmark='SPY')[1]*100:.2f}%\n")

    print(f"Custom Benchmark Volatility (Daily),{benchmark.benchmark_volatility()[0]*100:.4f}%\n")
    print(f"SPY Benchmark Volatility (Daily),{benchmark.benchmark_volatility(benchmark='SPY')[0]*100:.4f}%\n")
    print(f"Custom Benchmark Volatility (Annualized),{benchmark.benchmark_volatility()[1]*100:.2f}%\n")
    print(f"SPY Benchmark Volatility (Annualized),{benchmark.benchmark_volatility(benchmark='SPY')[1]*100:.2f}%\n")

    print(f"Custom Benchmark Average Return (Daily),{benchmark.benchmark_average_return()[0]*100:.4f}%\n")
    print(f"SPY Benchmark Average Return (Daily),{benchmark.benchmark_average_return(benchmark='SPY')[0]*100:.4f}%\n")
    print(f"Custom Benchmark Average Return (Annualized),{benchmark.benchmark_average_return()[1]*100:.2f}%\n")
    print(f"SPY Benchmark Average Return (Annualized),{benchmark.benchmark_average_return(benchmark='SPY')[1]*100:.2f}%\n")

    print(f"Portfolio Beta,{market_comparison.beta():.4f}\n")
    print(f"Portfolio Alpha against custom benchmark,{100*market_comparison.alpha(THREE_MTH_TREASURY_RATE):.4f}%\n")
    print(f"Portfolio Alpha against SPY benchmark,{100*market_comparison.alpha(THREE_MTH_TREASURY_RATE, benchmark='SPY'):.4f}%\n")

    print(f"Portfolio Risk Premium,{market_comparison.portfolio_risk_premium(THREE_MTH_TREASURY_RATE)*100:.2f}%\n")
    print(f"Risk Adjusted Return (three month treasury rate),{market_comparison.risk_adjusted_return(THREE_MTH_TREASURY_RATE)*100:.2f}%\n")
    print(f"Treynor Ratio (three month treasury rate),{ratios.treynor_ratio(THREE_MTH_TREASURY_RATE):.2f}\n")
    # print(f"Information Ratio (Custom Benchmark),{information_ratio():.2f}\n")
    print("--- Portfolio Returns ---\n")
    print(f"1 Day Return,{period_metrics['1d'] * 100:.2f}%\n")
    print(f"1 Week Return,{period_metrics['1w'] * 100:.2f}%\n")
    print(f"1 Month Return,{period_metrics['1m'] * 100:.2f}%\n")
    print(f"Year-to-Date Return,{period_metrics['YTD'] * 100:.2f}%\n")
    print(f"1 Year Return,{period_metrics['1y'] * 100:.2f}%\n")
    print(f"Inception,{period_metrics['Inception'] * 100:.2f}%\n")

    # output all these calculations to a csv file
    with open(os.path.join(output_folder, 'performance_metrics.csv'), 'w') as f:
        f.write("Metric,Value\n")
        f.write(f"Total Return including dividends,{portfolio_performance.total_return()*100:.2f}%\n")
        f.write(f"Daily Average Return,{portfolio_performance.daily_average_return()*100:.4f}%\n")
        f.write(f"Annualized Average Return,{portfolio_performance.annualized_average_return()*100:.2f}%\n")
        f.write(f"Daily Variance,{risk_metrics.daily_variance()*100:.4f}%\n")
        f.write(f"Annualized Variance,{risk_metrics.annualized_variance()*100:.2f}%\n")
        f.write(f"Daily Volatility,{risk_metrics.daily_volatility()*100:.4f}%\n")
        f.write(f"Annualized Volatility,{risk_metrics.annualized_volatility()*100:.2f}%\n")
        f.write(f"Daily Downside Variance,{risk_metrics.daily_downside_variance()*100:.4f}%\n")
        f.write(f"Annualized Downside Variance,{risk_metrics.annualized_downside_variance()*100:.2f}%\n")
        f.write(f"Daily Downside Volatility,{risk_metrics.daily_downside_volatility()*100:.4f}%\n")
        f.write(f"Annualized Downside Volatility,{risk_metrics.annualized_downside_volatility()*100:.2f}%\n")
        f.write(f"Sharpe Ratio (Annualized),{ratios.sharpe_ratio(THREE_MTH_TREASURY_RATE)[1]:.2f}\n")
        f.write(f"Sortino Ratio (Annualized),{ratios.sortino_ratio(THREE_MTH_TREASURY_RATE)[1]:.2f}\n")
        f.write(f"Maximum Drawdown,{risk_metrics.maximum_drawdown()*100:.2f}%\n")

        f.write(f"Custom Benchmark Variance (Daily),{benchmark.benchmark_variance()[0]*100:.4f}%\n")
        f.write(f"SPY Benchmark Variance (Daily),{benchmark.benchmark_variance(benchmark='SPY')[0]*100:.4f}%\n")
        f.write(f"Custom Benchmark Variance (Annualized),{benchmark.benchmark_variance()[1]*100:.2f}%\n")
        f.write(f"SPY Benchmark Variance (Annualized),{benchmark.benchmark_variance(benchmark='SPY')[1]*100:.2f}%\n")

        f.write(f"Custom Benchmark Volatility (Daily),{benchmark.benchmark_volatility()[0]*100:.4f}%\n")
        f.write(f"SPY Benchmark Volatility (Daily),{benchmark.benchmark_volatility(benchmark='SPY')[0]*100:.4f}%\n")
        f.write(f"Custom Benchmark Volatility (Annualized),{benchmark.benchmark_volatility()[1]*100:.2f}%\n")
        f.write(f"SPY Benchmark Volatility (Annualized),{benchmark.benchmark_volatility(benchmark='SPY')[1]*100:.2f}%\n")

        f.write(f"Custom Benchmark Average Return (Daily),{benchmark.benchmark_average_return()[0]*100:.4f}%\n")
        f.write(f"SPY Benchmark Average Return (Daily),{benchmark.benchmark_average_return(benchmark='SPY')[0]*100:.4f}%\n")
        f.write(f"Custom Benchmark Average Return (Annualized),{benchmark.benchmark_average_return()[1]*100:.2f}%\n")
        f.write(f"SPY Benchmark Average Return (Annualized),{benchmark.benchmark_average_return(benchmark='SPY')[1]*100:.2f}%\n")
    
        f.write(f"Portfolio Beta,{market_comparison.beta():.4f}\n")
        f.write(f"Portfolio Alpha against custom benchmark,{100*market_comparison.alpha(THREE_MTH_TREASURY_RATE):.4f}%\n")
        f.write(f"Portfolio Alpha against SPY benchmark,{100*market_comparison.alpha(THREE_MTH_TREASURY_RATE, benchmark='SPY'):.4f}%\n")

        f.write(f"Portfolio Risk Premium,{market_comparison.portfolio_risk_premium(THREE_MTH_TREASURY_RATE)*100:.2f}%\n")
        f.write(f"Risk Adjusted Return (three month treasury rate),{market_comparison.risk_adjusted_return(THREE_MTH_TREASURY_RATE)*100:.2f}%\n")
        f.write(f"Treynor Ratio (three month treasury rate),{ratios.treynor_ratio(THREE_MTH_TREASURY_RATE):.2f}\n")
        # f.write(f"Information Ratio (Custom Benchmark),{information_ratio():.2f}\n")
        f.write("--- Portfolio Returns ---\n")
        f.write(f"1 Day Return,{period_metrics['1d'] * 100:.2f}%\n")
        f.write(f"1 Week Return,{period_metrics['1w'] * 100:.2f}%\n")
        f.write(f"1 Month Return,{period_metrics['1m'] * 100:.2f}%\n")
        f.write(f"Year-to-Date Return,{period_metrics['YTD'] * 100:.2f}%\n")
        f.write(f"1 Year Return,{period_metrics['1y'] * 100:.2f}%\n")
        f.write(f"Inception,{period_metrics['Inception'] * 100:.2f}%\n")

    data_processor.plot_portfolio_value()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 PerformanceTracker.py <folder_prefix>")
    folder_prefix = sys.argv[1]
    output_folder = os.path.join("data", folder_prefix, "output")
    os.makedirs(output_folder, exist_ok=True)
    main()

    # notes: % changes are only to 2 decimals in portfolio_total.csv
    # definitely something wrong here, possibly because of that.