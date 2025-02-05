import pandas as pd
import matplotlib.pyplot as plt

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

def aggregate_data(market_values_file, cash_file, output_file):
    market_values = pd.read_csv(market_values_file)
    cash_value = pd.read_csv(cash_file)
    market_values['Date'] = pd.to_datetime(market_values['Date'])
    cash_value['Date'] = pd.to_datetime(cash_value['Date'])
    numeric_columns = market_values.columns.drop('Date')
    market_values[numeric_columns] = market_values[numeric_columns].apply(pd.to_numeric, errors='coerce')
    cash_value['Cash'] = cash_value['Cash'].apply(pd.to_numeric, errors='coerce')

    market_values['Total_Portfolio_Value'] = market_values[numeric_columns].sum(axis=1) + cash_value['Cash']
    output_df = market_values[['Date', 'Total_Portfolio_Value']].copy()
    output_df = output_df.sort_values('Date')
    output_df['pct_change'] = output_df['Total_Portfolio_Value'].pct_change()

    output_df.to_csv(output_file, index=False, float_format='%.6f')


def total_return():
    df = pd.read_csv('output/portfolio_total.csv')
    total_return = (df['Total_Portfolio_Value'].iloc[-1] - df['Total_Portfolio_Value'].iloc[0]) / df['Total_Portfolio_Value'].iloc[0]
    # print(f"Total Return including dividends: {total_return*100:.2f}%")
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
    output_file = "output/portfolio_total.csv"
    aggregate_data(market_values_file, cash_file, output_file)

if __name__ == '__main__':
    # main()
    # plot_portfolio_value()

    print(f"Total Return including dividends: {total_return()*100:.2f}%")
    
    # revisit these.
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


# notes: % changes are only to 2 decimals in portfolio_total.csv
# definitely something wrong here, possibly because of that.