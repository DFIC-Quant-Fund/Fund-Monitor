import pandas as pd
import numpy as np
import MetricCalculator as mcalc


# Load the specific sheet
file_path = 'DFIC_Fund_Tracker.xlsx'
sheet_name = 'Historical Portfolio Values'

# Load only columns AN to BM
df = pd.read_excel(file_path, sheet_name=sheet_name, usecols="AN:BM", skiprows=3)
df.rename(columns={'Dates.3': 'Date'}, inplace=True)
df.drop(['Unnamed: 55', 'Unnamed: 60'], axis=1, inplace=True) # drop empty columns
df.fillna(0, inplace=True) # replace NaN values with 0

df['Date'] = pd.to_datetime(df['Date'], format='%Y/%m/%d', errors='coerce')




# print(df.head())

RISK_FREE_RATE = 0.0436

mc = mcalc.MetricCalculator()

# Calculate the metrics
compounded_return, annualized_return = mc.compounded_portfolio_return(df)
avg_daily_return, avg_annualized_return = mc.average_portfolio_return(df)
daily_variance, annualized_variance = mc.portfolio_variance(df)
daily_volatility, annualized_volatility = mc.portfolio_volatility(df)
max_drawdown = mc.maximum_drawdown(df)
sharpe_daily, sharpe_annualized = mc.sharpe_ratio(df, risk_free_rate=RISK_FREE_RATE)
# You'll need market data for Beta and Alpha calculations
# market_returns = pd.Series()  # Add your market return data here
# beta_value = beta(df, market_returns)
# alpha_value = alpha(df, market_returns)
# sortino_daily, sortino_annualized = sortino_ratio(df)

# Print the results
print(f"Compounded Portfolio Return: {compounded_return}")
print(f"Annualized Portfolio Return: {annualized_return}")
print(f"Average Daily Return: {avg_daily_return}")
print(f"Annualized Average Return: {avg_annualized_return}")
print(f"Daily Volatility: {daily_volatility}")
print(f"Annualized Volatility: {annualized_volatility}")
print(f"Maximum Drawdown: {max_drawdown}")
print(f"Sharpe Ratio (Daily): {sharpe_daily}")
print(f"Sharpe Ratio (Annualized): {sharpe_annualized}")
# print(f"Beta: {beta_value}")
# print(f"Alpha: {alpha_value}")
# print(f"Sortino Ratio (Daily): {sortino_daily}")
# print(f"Sortino Ratio (Annualized): {sortino_annualized}")




# def extract_sheet_to_csv(file_path, sheet_name, output_csv_path):
#     # Load the specific sheet
#     data = pd.read_excel(file_path, sheet_name=sheet_name)
    
#     # Save to CSV
#     data.to_csv(output_csv_path, index=False)
#     print(f"Data from sheet '{sheet_name}' saved to {output_csv_path}")
    


# file_path = "DFIC_Fund_Tracker.xlsx"
# sheet_name = "Historical Portfolio Values"
# output_csv_path = "data.csv"
# extract_sheet_to_csv(file_path, sheet_name, output_csv_path)

# # Load the CSV file
# csv_data = pd.read_csv(output_csv_path)

# # Inspect the data
# print(csv_data.head())

