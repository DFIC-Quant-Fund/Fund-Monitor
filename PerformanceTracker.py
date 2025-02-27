from datetime import timedelta
import os
import pandas as pd
import sys
import matplotlib.pyplot as plt
import yfinance as yf

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

def aggregate_data(market_values_file, cash_file, dividends_file, output_file):
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

def get_spy_benchmark():
    prices = pd.read_csv('output/prices.csv')
    dividend_df = pd.read_csv('output/dividends.csv')[['Date', 'SPY']]

    # upon further thought, I guess dividends are baked into the price?
    dividend_df['Date'] = pd.to_datetime(dividend_df['Date'])
    dividend_df = dividend_df.set_index('Date')
    dividend_df['SPY'].fillna(0)

    # create a new dataframe with only the date and SPY columns
    benchmark_df = prices[['Date', 'SPY']].copy()
    benchmark_df['Date'] = pd.to_datetime(benchmark_df['Date'])
    benchmark_df = benchmark_df.sort_values('Date')

    # use exchange_rates.csv to convert USD to CAD in the SPY column
    exchange_rates = pd.read_csv('output/exchange_rates.csv')
    exchange_rates['Date'] = pd.to_datetime(exchange_rates['Date'])
    exchange_rates = exchange_rates.sort_values('Date')
    exchange_rates.set_index('Date', inplace=True)

    benchmark_df.set_index('Date', inplace=True)
    benchmark_df['SPY'] = (benchmark_df['SPY'] + dividend_df['SPY'].cumsum()) * exchange_rates['USD']
    # benchmark_df['SPY'] = (benchmark_df['SPY']) * exchange_rates['USD']
    benchmark_df['pct_change'] = benchmark_df['SPY'].pct_change()

    # can write this to csv if we want but don't rly need it so I left it for now
    return benchmark_df

def create_custom_benchmark():
    STARTING_CASH = 101644.99
    exchange_rates = pd.read_csv('output/exchange_rates.csv')
    prices = pd.read_csv('output/prices.csv')
    prices['Date'] = pd.to_datetime(prices['Date'])
    dividends = pd.read_csv('output/dividends.csv')[['Date', 'XIU.TO', 'SPY', 'AGG', 'XBB.TO']]

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
    custom_benchmark.to_csv('output/custom_benchmark.csv', index=True)


def total_return():
    df = pd.read_csv('output/portfolio_total.csv')
    total_return = (df['Total_Portfolio_Value'].iloc[-1] - df['Total_Portfolio_Value'].iloc[0]) / df['Total_Portfolio_Value'].iloc[0]

    return total_return

# def daily_compounded_return():
#     df = pd.read_csv('output/portfolio_total.csv')
#     daily_changes = df['pct_change']
#     daily_compounded_return = (1 + daily_changes).prod() - 1

#     return daily_compounded_return

# def annualized_compounded_return():
#     annualized_return = (1 + daily_compounded_return())**252 - 1

#     return annualized_return

def daily_average_return():
    df = pd.read_csv('output/portfolio_total.csv')
    daily_returns = df['pct_change'].dropna()
    average_return = daily_returns.mean()

    return average_return

def annualized_average_return():
    df = pd.read_csv('output/portfolio_total.csv')
    daily_returns = df['pct_change'].dropna()
    average_daily_return = daily_returns.mean()
    annualized_avg_return = (1+average_daily_return) ** 252 - 1

    return annualized_avg_return

def daily_variance():
    df = pd.read_csv('output/portfolio_total.csv')
    daily_returns = df['pct_change'].dropna()
    daily_variance = daily_returns.var()

    return daily_variance

def annualized_variance():
    df = pd.read_csv('output/portfolio_total.csv')
    annualized_variance = daily_variance() * 252
    # print(f"Annualized Variance: {annualized_variance:.4f}")
    return annualized_variance

def daily_volatility():
    df = pd.read_csv('output/portfolio_total.csv')
    # daily_return = df['Total_Portfolio_Value'].pct_change()
    daily_return = df['pct_change'].dropna()
    daily_volatility = daily_return.std()

    # print(f"Daily Volatility: {daily_volatility:.4f}")
    return daily_volatility

def annualized_volatility():
    annualized_volatility = annualized_variance() ** 0.5
    # print(f"Annualized Volatility: {annualized_volatility:.4f}")

    return annualized_volatility

def daily_downside_variance():
    df = pd.read_csv('output/portfolio_total.csv')
    daily_return = df['pct_change'].dropna()
    downside_returns = daily_return[daily_return < 0]
    downside_variance = downside_returns.var()
    # print(f"Daily Downside Variance: {downside_variance:.4f}")
    return downside_variance

def annualized_downside_variance():
    annualized_downside_variance = daily_downside_variance() * 252
    # print(f"Annualized Downside Variance: {annualized_downside_variance:.4f}")
    return annualized_downside_variance

def daily_downside_volatility():
    daily_downside_volatility = daily_downside_variance() ** 0.5
    # print(f"Daily Downside Volatility: {daily_downside_volatility:.4f}")
    return daily_downside_volatility

def annualized_downside_volatility():
    annualized_downside_volatility = annualized_downside_variance() ** 0.5
    # print(f"Annualized Downside Volatility: {annualized_downside_volatility:.4f}")
    return annualized_downside_volatility

def sharpe_ratio(risk_free_rate):
    df = pd.read_csv('output/portfolio_total.csv')
    daily_return = df['pct_change'].dropna()
    daily_sharpe_ratio = (daily_return.mean() - risk_free_rate/252) / daily_return.std()
    annualized_sharpe_ratio = daily_sharpe_ratio * (252 ** 0.5)

    return daily_sharpe_ratio, annualized_sharpe_ratio

def sortino_ratio(risk_free_rate):
    df = pd.read_csv('output/portfolio_total.csv')
    daily_return = df['pct_change'].dropna()
    downside_returns = daily_return[daily_return < 0]
    daily_sortino_ratio = (daily_return.mean() - risk_free_rate/252) / downside_returns.std()
    annualized_sortino_ratio = daily_sortino_ratio * (252 ** 0.5)

    return daily_sortino_ratio, annualized_sortino_ratio

def maximum_drawdown():
    # calculate the maximum drawdown
    df = pd.read_csv('output/portfolio_total.csv')
    daily_return = df['pct_change'].dropna()
    
    return daily_return.min()

    
def benchmark_variance(benchmark='custom'):
    if benchmark == 'custom':
        benchmark_df = pd.read_csv('output/custom_benchmark.csv')
    else:
        benchmark_df = get_spy_benchmark()
    
    daily_benchmark_variance = benchmark_df['pct_change'].dropna().var()
    annualized_benchmark_variance = daily_benchmark_variance * 252
    return daily_benchmark_variance, annualized_benchmark_variance
    

def benchmark_volatility(benchmark='custom'):
    if benchmark == 'custom':
        benchmark_df = pd.read_csv('output/custom_benchmark.csv')
    else:
        benchmark_df = get_spy_benchmark()
    
    daily_benchmark_volatility = benchmark_df['pct_change'].dropna().std()
    annualized_benchmark_volatility = daily_benchmark_volatility * (252 ** 0.5)

    return daily_benchmark_volatility, annualized_benchmark_volatility

def benchmark_average_return(benchmark='custom'):
    if benchmark == 'custom':
        benchmark_df = pd.read_csv('output/custom_benchmark.csv')
    else:
        benchmark_df = get_spy_benchmark()
    
    daily_benchmark_return = benchmark_df['pct_change'].dropna().mean()
    annualized_benchmark_return = (1+daily_benchmark_return) ** 252 - 1

    return daily_benchmark_return, annualized_benchmark_return

def beta(benchmark='custom'):
    if benchmark == 'custom':
        benchmark_df = pd.read_csv('output/custom_benchmark.csv')
    else:
        benchmark_df = get_spy_benchmark()
    
    df = pd.read_csv('output/portfolio_total.csv')
    daily_portfolio_return = df['pct_change'].dropna()

    daily_benchmark_var, _ = benchmark_variance(benchmark)
    covariance = daily_portfolio_return.cov(benchmark_df['pct_change'])
    beta = covariance / daily_benchmark_var

    return beta
    

def alpha(risk_free_rate, benchmark='custom'): 
    annual_benchmark_return = benchmark_average_return(benchmark)[1]
    print("benchmark: ", benchmark)
    print("annual_benchmark_return ", annual_benchmark_return)

    alpha = (annualized_average_return() - risk_free_rate) - beta() * (annual_benchmark_return - risk_free_rate)

    return alpha
    
def portfolio_risk_premium(risk_free_return):
    return annualized_average_return() - risk_free_return

def risk_adjusted_return(risk_free_return):
    benchmark_vol = benchmark_volatility()[1]
    portfolio_volatility = annualized_volatility()
    portfolio_risk_prem = portfolio_risk_premium(risk_free_return)

    risk_adjusted_return = portfolio_risk_prem * benchmark_vol / portfolio_volatility + risk_free_return
    
    return risk_adjusted_return

def treynor_ratio(risk_free_return):
    return portfolio_risk_premium(risk_free_return) / beta()

def information_ratio(benchmark='custom'):
    # df = pd.read_csv('output/portfolio_total.csv')
    # daily_portfolio_return = df['pct_change'].dropna()
    # daily_benchmark_return = benchmark_df['pct_change'].dropna()
    _, annual_benchmark_return = benchmark_average_return(benchmark)

    # excess_returns = daily_portfolio_return - daily_benchmark_return
    excess_returns = annualized_average_return() - annual_benchmark_return

    # print("annualized_average_return of portfolio: ", annualized_average_return())
    # print("annual_benchmark_return: ", annual_benchmark_return)

    tracking_error = excess_returns.std() # this doesn't make sense rn since they're just scalars
    information_ratio = excess_returns.mean() / tracking_error

    return information_ratio

def plot_portfolio_value():
    df = pd.read_csv('output/portfolio_total.csv')
    df['Date'] = pd.to_datetime(df['Date'])
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(df['Date'],df['Total_Portfolio_Value'],color='black',linewidth=2,label='Portfolio Value')
    ax.set_title('Portfolio Value (CAD)', fontsize=16, fontweight='bold')
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Amount (CAD)', fontsize=12)
    ax.legend(loc='lower right')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('output/portfolio_plot.png')
def calculate_period_performance():
    df = pd.read_csv('output/portfolio_total.csv')
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


def main():
    market_values_file = "output/market_values.csv"
    cash_file = "output/cash.csv"
    dividend_file = "output/dividend_values.csv"
    output_file = "output/portfolio_total.csv"
    THREE_MTH_TREASURY_RATE = 0.0436 # 3-month treasury rate
    FIVE_PERCENT = 0.05

    # run these once only after running portfolio.py once
    aggregate_data(market_values_file, cash_file, dividend_file, output_file)
    create_custom_benchmark()
    period_metrics = calculate_period_performance()

    print(f"Total Return including dividends,{total_return()*100:.2f}%\n")
    print(f"Daily Average Return,{daily_average_return()*100:.4f}%\n")
    print(f"Annualized Average Return,{annualized_average_return()*100:.2f}%\n")
    print(f"Daily Variance,{daily_variance()*100:.4f}%\n")
    print(f"Annualized Variance,{annualized_variance()*100:.2f}%\n")
    print(f"Daily Volatility,{daily_volatility()*100:.4f}%\n")
    print(f"Annualized Volatility,{annualized_volatility()*100:.2f}%\n")
    print(f"Daily Downside Variance,{daily_downside_variance()*100:.4f}%\n")
    print(f"Annualized Downside Variance,{annualized_downside_variance()*100:.2f}%\n")
    print(f"Daily Downside Volatility,{daily_downside_volatility()*100:.4f}%\n")
    print(f"Annualized Downside Volatility,{annualized_downside_volatility()*100:.2f}%\n")
    print(f"Sharpe Ratio (Annualized),{sharpe_ratio(THREE_MTH_TREASURY_RATE)[1]:.2f}\n")
    print(f"Sortino Ratio (Annualized),{sortino_ratio(THREE_MTH_TREASURY_RATE)[1]:.2f}\n")
    print(f"Maximum Drawdown,{maximum_drawdown()*100:.2f}%\n")

    print(f"Custom Benchmark Variance (Daily),{benchmark_variance()[0]*100:.4f}%\n")
    print(f"SPY Benchmark Variance (Daily),{benchmark_variance(benchmark='SPY')[0]*100:.4f}%\n")
    print(f"Custom Benchmark Variance (Annualized),{benchmark_variance()[1]*100:.2f}%\n")
    print(f"SPY Benchmark Variance (Annualized),{benchmark_variance(benchmark='SPY')[1]*100:.2f}%\n")

    print(f"Custom Benchmark Volatility (Daily),{benchmark_volatility()[0]*100:.4f}%\n")
    print(f"SPY Benchmark Volatility (Daily),{benchmark_volatility(benchmark='SPY')[0]*100:.4f}%\n")
    print(f"Custom Benchmark Volatility (Annualized),{benchmark_volatility()[1]*100:.2f}%\n")
    print(f"SPY Benchmark Volatility (Annualized),{benchmark_volatility(benchmark='SPY')[1]*100:.2f}%\n")

    print(f"Custom Benchmark Average Return (Daily),{benchmark_average_return()[0]*100:.4f}%\n")
    print(f"SPY Benchmark Average Return (Daily),{benchmark_average_return(benchmark='SPY')[0]*100:.4f}%\n")
    print(f"Custom Benchmark Average Return (Annualized),{benchmark_average_return()[1]*100:.2f}%\n")
    print(f"SPY Benchmark Average Return (Annualized),{benchmark_average_return(benchmark='SPY')[1]*100:.2f}%\n")

    print(f"Portfolio Beta,{beta():.4f}\n")
    print(f"Portfolio Alpha against custom benchmark,{100*alpha(THREE_MTH_TREASURY_RATE):.4f}%\n")
    print(f"Portfolio Alpha against SPY benchmark,{100*alpha(THREE_MTH_TREASURY_RATE, benchmark='SPY'):.4f}%\n")

    print(f"Portfolio Risk Premium,{portfolio_risk_premium(THREE_MTH_TREASURY_RATE)*100:.2f}%\n")
    print(f"Risk Adjusted Return (three month treasury rate),{risk_adjusted_return(THREE_MTH_TREASURY_RATE)*100:.2f}%\n")
    print(f"Treynor Ratio (three month treasury rate),{treynor_ratio(THREE_MTH_TREASURY_RATE):.2f}\n")
    # print(f"Information Ratio (Custom Benchmark),{information_ratio():.2f}\n")

    print("--- Portfolio Returns ---\n")
    print(f"1 Day Return,{period_metrics['1d']*100:.2f}%\n")
    print(f"1 Week Return,{period_metrics['1w']*100:.2f}%\n")
    print(f"1 Month Return,{period_metrics['1m']*100:.2f}%\n")
    print(f"Year-to-Date Return,{period_metrics['YTD']*100:.2f}%\n")
    print(f"1 Year Return,{period_metrics['1y']*100:.2f}%\n")
    print(f"Inception,{period_metrics['Inception']*100:.2f}%\n")

    # output all these calculations to a csv file
    with open('output/performance_metrics.csv', 'w') as f:
        f.write("Metric,Value\n")
        f.write(f"Total Return including dividends,{total_return()*100:.2f}%\n")
        f.write(f"Daily Average Return,{daily_average_return()*100:.4f}%\n")
        f.write(f"Annualized Average Return,{annualized_average_return()*100:.2f}%\n")
        f.write(f"Daily Variance,{daily_variance()*100:.4f}%\n")
        f.write(f"Annualized Variance,{annualized_variance()*100:.2f}%\n")
        f.write(f"Daily Volatility,{daily_volatility()*100:.4f}%\n")
        f.write(f"Annualized Volatility,{annualized_volatility()*100:.2f}%\n")
        f.write(f"Daily Downside Variance,{daily_downside_variance()*100:.4f}%\n")
        f.write(f"Annualized Downside Variance,{annualized_downside_variance()*100:.2f}%\n")
        f.write(f"Daily Downside Volatility,{daily_downside_volatility()*100:.4f}%\n")
        f.write(f"Annualized Downside Volatility,{annualized_downside_volatility()*100:.2f}%\n")
        f.write(f"Sharpe Ratio (Annualized),{sharpe_ratio(THREE_MTH_TREASURY_RATE)[1]:.2f}\n")
        f.write(f"Sortino Ratio (Annualized),{sortino_ratio(THREE_MTH_TREASURY_RATE)[1]:.2f}\n")
        f.write(f"Maximum Drawdown,{maximum_drawdown()*100:.2f}%\n")

        f.write(f"Custom Benchmark Variance (Daily),{benchmark_variance()[0]*100:.4f}%\n")
        f.write(f"SPY Benchmark Variance (Daily),{benchmark_variance(benchmark='SPY')[0]*100:.4f}%\n")
        f.write(f"Custom Benchmark Variance (Annualized),{benchmark_variance()[1]*100:.2f}%\n")
        f.write(f"SPY Benchmark Variance (Annualized),{benchmark_variance(benchmark='SPY')[1]*100:.2f}%\n")

        f.write(f"Custom Benchmark Volatility (Daily),{benchmark_volatility()[0]*100:.4f}%\n")
        f.write(f"SPY Benchmark Volatility (Daily),{benchmark_volatility(benchmark='SPY')[0]*100:.4f}%\n")
        f.write(f"Custom Benchmark Volatility (Annualized),{benchmark_volatility()[1]*100:.2f}%\n")
        f.write(f"SPY Benchmark Volatility (Annualized),{benchmark_volatility(benchmark='SPY')[1]*100:.2f}%\n")

        f.write(f"Custom Benchmark Average Return (Daily),{benchmark_average_return()[0]*100:.4f}%\n")
        f.write(f"SPY Benchmark Average Return (Daily),{benchmark_average_return(benchmark='SPY')[0]*100:.4f}%\n")
        f.write(f"Custom Benchmark Average Return (Annualized),{benchmark_average_return()[1]*100:.2f}%\n")
        f.write(f"SPY Benchmark Average Return (Annualized),{benchmark_average_return(benchmark='SPY')[1]*100:.2f}%\n")
    
        f.write(f"Portfolio Beta,{beta():.4f}\n")
        f.write(f"Portfolio Alpha against custom benchmark,{100*alpha(THREE_MTH_TREASURY_RATE):.4f}%\n")
        f.write(f"Portfolio Alpha against SPY benchmark,{100*alpha(THREE_MTH_TREASURY_RATE, benchmark='SPY'):.4f}%\n")

        f.write(f"Portfolio Risk Premium,{portfolio_risk_premium(THREE_MTH_TREASURY_RATE)*100:.2f}%\n")
        f.write(f"Risk Adjusted Return (three month treasury rate),{risk_adjusted_return(THREE_MTH_TREASURY_RATE)*100:.2f}%\n")
        f.write(f"Treynor Ratio (three month treasury rate),{treynor_ratio(THREE_MTH_TREASURY_RATE):.2f}\n")
        # f.write(f"Information Ratio (Custom Benchmark),{information_ratio():.2f}\n")
        f.write("--- Portfolio Returns ---\n")
        f.write(f"1 Day Return,{period_metrics['1d']*100:.2f}%\n")
        f.write(f"1 Week Return,{period_metrics['1w']*100:.2f}%\n")
        f.write(f"1 Month Return,{period_metrics['1m']*100:.2f}%\n")
        f.write(f"Year-to-Date Return,{period_metrics['YTD']*100:.2f}%\n")
        f.write(f"1 Year Return,{period_metrics['1y']*100:.2f}%\n")
        f.write(f"Inception,{period_metrics['Inception']*100:.2f}%\n")


if __name__ == '__main__':
    main()
    plot_portfolio_value()

    # notes: % changes are only to 2 decimals in portfolio_total.csv
    # definitely something wrong here, possibly because of that.