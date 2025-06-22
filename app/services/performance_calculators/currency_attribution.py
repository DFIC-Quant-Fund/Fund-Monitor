import pandas as pd
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Establishes a connection to the database."""
    connection = mysql.connector.connect(
        host=os.getenv('DB_HOSTNAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT'),
        database="Fund"
    )
    return connection

def get_first_trading_day(connection, start_date):
    """Gets the first trading day on or after a given date."""
    query = """
    SELECT MIN(trading_date) 
    FROM TradingCalendar 
    WHERE trading_date >= %s
    """
    df = pd.read_sql(query, connection, params=(start_date,))
    return df.iloc[0,0]

def get_last_trading_day(connection, end_date):
    """Gets the last trading day on or before a given date."""
    query = """
    SELECT MAX(trading_date) 
    FROM TradingCalendar 
    WHERE trading_date <= %s
    """
    df = pd.read_sql(query, connection, params=(end_date,))
    return df.iloc[0,0]

def calculate_currency_attribution(portfolio: str, start_date: str, end_date: str):
    """
    Calculates portfolio returns and currency attribution for a given period.

    Args:
        portfolio (str): The name of the portfolio to analyze.
        start_date (str): The start date of the analysis period (YYYY-MM-DD).
        end_date (str): The end date of the analysis period (YYYY-MM-DD).

    Returns:
        A pandas DataFrame with the attribution analysis.
    """
    
    conn = get_db_connection()
    
    actual_start_date = get_first_trading_day(conn, start_date)
    actual_end_date = get_last_trading_day(conn, end_date)

    # 1. Fetch initial holdings
    holdings_query = """
    SELECT ticker, shares_held, price AS start_price, security_currency, market_value
    FROM MaterializedHoldings
    WHERE portfolio = %s AND trading_date = %s AND shares_held > 0
    """
    initial_holdings_df = pd.read_sql(holdings_query, conn, params=(portfolio, actual_start_date))

    # 2. Fetch end prices
    end_prices_query = """
    SELECT ticker, price AS end_price
    FROM MaterializedHoldings
    WHERE portfolio = %s AND trading_date = %s
    """
    end_prices_df = pd.read_sql(end_prices_query, conn, params=(portfolio, actual_end_date))

    # 3. Fetch currency rates
    currency_query = "SELECT date, CAD, USD, EUR FROM Currencies WHERE date IN (%s, %s)"
    currency_df = pd.read_sql(currency_query, conn, params=(actual_start_date, actual_end_date), index_col='date')
    
    conn.close()

    # 4. Combine data
    data_df = pd.merge(initial_holdings_df, end_prices_df, on='ticker')
    
    # Portfolio total market value at the start
    total_market_value_start = data_df['market_value'].sum()
    data_df['weight'] = data_df['market_value'] / total_market_value_start
    
    # 5. Handle currency conversions
    # FX rates are CAD per Local. We want USD per Local.
    # USD per CAD = 1 / (CAD per USD)
    usd_per_cad_start = 1 / currency_df.loc[actual_start_date, 'USD']
    usd_per_cad_end = 1 / currency_df.loc[actual_end_date, 'USD']

    def get_fx_rate(row, date_type):
        currency = row['security_currency']
        date = actual_start_date if date_type == 'start' else actual_end_date
        
        if currency == 'USD':
            return 1.0
        if currency == 'CAD':
            return usd_per_cad_start if date_type == 'start' else usd_per_cad_end
        if currency == 'EUR':
            # USD per EUR = (CAD per EUR) * (USD per CAD)
            cad_per_eur = currency_df.loc[date, 'EUR']
            usd_per_cad = usd_per_cad_start if date_type == 'start' else usd_per_cad_end
            return cad_per_eur * usd_per_cad
        return 1.0

    data_df['fx_start'] = data_df.apply(lambda row: get_fx_rate(row, 'start'), axis=1)
    data_df['fx_end'] = data_df.apply(lambda row: get_fx_rate(row, 'end'), axis=1)

    # 6. Calculate returns
    data_df['local_return'] = (data_df['end_price'] / data_df['start_price']) - 1
    data_df['fx_return'] = (data_df['fx_end'] / data_df['fx_start']) - 1
    
    # Total return in USD
    start_price_usd = data_df['start_price'] * data_df['fx_start']
    end_price_usd = data_df['end_price'] * data_df['fx_end']
    data_df['total_return'] = (end_price_usd / start_price_usd) - 1

    # 7. Calculate attribution
    data_df['asset_selection_contrib'] = data_df['weight'] * data_df['local_return']
    data_df['currency_contrib'] = data_df['weight'] * data_df['fx_return']
    data_df['interaction_contrib'] = data_df['weight'] * data_df['local_return'] * data_df['fx_return']
    
    # 8. Summarize
    total_asset_selection = data_df['asset_selection_contrib'].sum()
    total_currency = data_df['currency_contrib'].sum()
    total_interaction = data_df['interaction_contrib'].sum()
    portfolio_total_return = (total_asset_selection + total_currency + total_interaction)

    summary = pd.DataFrame({
        'Effect': ['Asset Selection (Stock Picking)', 'Currency Effect (USD Strength)', 'Interaction Effect', 'Total Portfolio Return'],
        'Contribution': [total_asset_selection, total_currency, total_interaction, portfolio_total_return]
    })
    
    return summary

if __name__ == '__main__':
    # This part will be used to test the functions and show the results.
    
    # Analysis for 2024
    attribution_2024 = calculate_currency_attribution('dfic_core', '2024-01-01', '2024-12-31')
    print("Currency Attribution for 2024:")
    print(attribution_2024.to_string(formatters={'Contribution': '{:.2%}'.format}))
    
    # Analysis for 2025 YTD
    from datetime import datetime
    today_str = datetime.today().strftime('%Y-%m-%d')
    attribution_2025 = calculate_currency_attribution('dfic_core', '2025-01-01', today_str)
    print("\nCurrency Attribution for 2025 YTD:")
    print(attribution_2025.to_string(formatters={'Contribution': '{:.2%}'.format})) 