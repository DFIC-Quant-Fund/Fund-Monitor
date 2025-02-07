import pandas as pd
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
    df = pd.read_csv('output/prices.csv')
    # create a new dataframe with only the date and SPY columns
    benchmark_df = df[['Date', 'SPY']].copy()
    benchmark_df['Date'] = pd.to_datetime(benchmark_df['Date'])
    benchmark_df = benchmark_df.sort_values('Date')
    # use exchange_rates.csv to convert USD to CAD in the SPY column
    exchange_rates = pd.read_csv('output/exchange_rates.csv')
    exchange_rates['Date'] = pd.to_datetime(exchange_rates['Date'])
    exchange_rates = exchange_rates.sort_values('Date')
    exchange_rates.set_index('Date', inplace=True)
    benchmark_df.set_index('Date', inplace=True)
    benchmark_df['SPY'] = benchmark_df['SPY'] * exchange_rates['USD']
    benchmark_df['pct_change'] = benchmark_df['SPY'].pct_change()

    return benchmark_df

def get_custom_benchmark():
    STARTING_CASH = 101644.99
    start_date = '2022-05-01'
    end_date = pd.Timestamp.now().strftime('%Y-%m-%d')
    exchange_rates = pd.read_csv('output/exchange_rates.csv')
    prices = pd.read_csv('output/prices.csv')
    prices['Date'] = pd.to_datetime(prices['Date'])

    initial_exchange_rate = exchange_rates['USD'].iloc[0]

    # assuming we can buy fractional shares for now I guess or else use //
    # and leave remainder as cash
    xiu_initial_shares = 0.3*STARTING_CASH/prices['XIU.TO'].iloc[0]
    spy_initial_shares = 0.3*STARTING_CASH/(prices['SPY'].iloc[0] * initial_exchange_rate)
    agg_initial_shares = 0.2*STARTING_CASH/(prices['AGG'].iloc[0] * initial_exchange_rate)
    xbb_initial_shares = 0.2*STARTING_CASH/prices['XBB.TO'].iloc[0]

    xiu_value = xiu_initial_shares * prices['XIU.TO']
    spy_value = (spy_initial_shares * prices['SPY'] * exchange_rates['USD']).rename('SPY')
    agg_value = (agg_initial_shares * prices['AGG'] * exchange_rates['USD']).rename('AGG')
    xbb_value = xbb_initial_shares * prices['XBB.TO']

    # combine the above four value variables into one dataframe with the date index
    custom_benchmark = pd.concat([xiu_value, spy_value, agg_value, xbb_value], axis=1)
    custom_benchmark['Total'] = custom_benchmark.sum(axis=1)
    custom_benchmark['Date'] = prices['Date']
    custom_benchmark.set_index('Date', inplace=True)

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
    daily_returns = df['pct_change']
    average_return = daily_returns.mean()

    return average_return

def annualized_average_return():
    df = pd.read_csv('output/portfolio_total.csv')
    daily_returns = df['pct_change']
    average_daily_return = daily_returns.mean()
    annualized_avg_return = (1+average_daily_return) ** 252 - 1

    return annualized_avg_return

def daily_variance():
    df = pd.read_csv('output/portfolio_total.csv')
    daily_returns = df['pct_change']
    # daily_return = df['Total_Portfolio_Value'].pct_change() # does this work?
    daily_variance = daily_returns.var()
    # print(f"Daily Variance: {daily_variance:.4f}")
    return daily_variance

def annualized_variance():
    df = pd.read_csv('output/portfolio_total.csv')
    annualized_variance = daily_variance() * 252
    # print(f"Annualized Variance: {annualized_variance:.4f}")
    return annualized_variance

def daily_volatility():
    df = pd.read_csv('output/portfolio_total.csv')
    # daily_return = df['Total_Portfolio_Value'].pct_change()
    daily_return = df['pct_change']
    daily_volatility = daily_return.std()

    # print(f"Daily Volatility: {daily_volatility:.4f}")
    return daily_volatility

def annualized_volatility():
    annualized_volatility = annualized_variance() ** 0.5
    # print(f"Annualized Volatility: {annualized_volatility:.4f}")

    return annualized_volatility

def daily_downside_variance():
    df = pd.read_csv('output/portfolio_total.csv')
    daily_return = df['pct_change']
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

def sharpe_ratio(risk_free_rate=0.0436):
    df = pd.read_csv('output/portfolio_total.csv')
    daily_return = df['pct_change']
    daily_sharpe_ratio = (daily_return.mean() - risk_free_rate/252) / daily_return.std()
    annualized_sharpe_ratio = daily_sharpe_ratio * (252 ** 0.5)

    return daily_sharpe_ratio, annualized_sharpe_ratio

def sortino_ratio(risk_free_rate=0.0436):
    df = pd.read_csv('output/portfolio_total.csv')
    daily_return = df['pct_change']
    downside_returns = daily_return[daily_return < 0]
    daily_sortino_ratio = (daily_return.mean() - risk_free_rate/252) / downside_returns.std()
    annualized_sortino_ratio = daily_sortino_ratio * (252 ** 0.5)

    return daily_sortino_ratio, annualized_sortino_ratio

def maximum_drawdown():
    # calculate the maximum drawdown
    df = pd.read_csv('output/portfolio_total.csv')
    daily_return = df['pct_change']
    
    return daily_return.min()

    
def market_variance():
    # implement both daily and annualized
    pass

def market_volatility():
    # implement both daily and annualized
    pass

def beta():
    pass

def alpha():
    pass

def risk_adjusted_return():
    pass

def treynor_ratio():
    pass

def information_ratio():
    pass

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

def main():
    market_values_file = "output/market_values.csv"
    cash_file = "output/cash.csv"
    dividend_file = "output/dividend_values.csv"
    output_file = "output/portfolio_total.csv"
    RISK_FREE_RATE1 = 0.0436 # 3-month treasury rate
    RISK_FREE_RATE2 = 0.05

    # aggregate_data(market_values_file, cash_file, dividend_file, output_file)

    print(f"Total Return including dividends: {total_return()*100:.2f}%")
    
    # What do these even mean?
    # print(f"Daily Compounded Return: {daily_compounded_return()*100:.4f}%")
    # print(f"Annualized Compounded Return: {annualized_compounded_return()*100:.2f}%")
    
    print(f"Daily Average Return: {daily_average_return()*100:.4f}%")
    print(f"Annualized Average Return: {annualized_average_return()*100:.2f}%")
    print(f"Daily Variance: {daily_variance()*100:.4f}%")
    print(f"Annualized Variance: {annualized_variance()*100:.2f}%")
    print(f"Daily Volatility: {daily_volatility()*100:.4f}%")
    print(f"Annualized Volatility: {annualized_volatility()*100:.2f}%")
    print(f"Daily Downside Variance: {daily_downside_variance()*100:.4f}%")
    print(f"Annualized Downside Variance: {annualized_downside_variance()*100:.2f}%")
    print(f"Daily Downside Volatility: {daily_downside_volatility()*100:.4f}%")
    print(f"Annualized Downside Volatility: {annualized_downside_volatility()*100:.2f}%")
    print(f"Sharpe Ratio (Daily): {sharpe_ratio(RISK_FREE_RATE1)[0]:.4f}")
    print(f"Sharpe Ratio (Annualized): {sharpe_ratio(RISK_FREE_RATE2)[1]:.2f}")
    print(f"Sortino Ratio (Daily): {sortino_ratio(RISK_FREE_RATE1)[0]:.4f}")
    print(f"Sortino Ratio (Annualized): {sortino_ratio(RISK_FREE_RATE2)[1]:.2f}")
    print(f"Maximum Drawdown: {maximum_drawdown()*100:.2f}%")

if __name__ == '__main__':
    # main()
    # plot_portfolio_value()
    get_custom_benchmark()

    # notes: % changes are only to 2 decimals in portfolio_total.csv
    # definitely something wrong here, possibly because of that.