# %% [markdown]
# # Imports and Configs

# %%
import mysql.connector
import os
import pandas as pd
import yfinance as yf
import yaml
from dotenv import load_dotenv
import time
try:
    # yfinance can use curl_cffi which raises this specific error
    from curl_cffi.requests import HTTPError
except ImportError:
    # Fallback if curl_cffi is not used or installed
    from requests.exceptions import HTTPError

load_dotenv()

# %%
# Set up SQL database connection

connection = mysql.connector.connect(
    host=os.getenv('DB_HOSTNAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    port=os.getenv('DB_PORT'),
    database="Fund"
)

cursor = connection.cursor()

# %% [markdown]
# # Securities

# %%
# Create Securities SQL Table
def create_securities_table():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Securities (
        ticker VARCHAR(10) NOT NULL,
        portfolio VARCHAR(50) NOT NULL,
        name VARCHAR(100),
        type VARCHAR(20) NOT NULL,
        geography VARCHAR(50),
        sector VARCHAR(50),
        fund VARCHAR(50),
        currency CHAR(3) NOT NULL,
        PRIMARY KEY (ticker, portfolio) 
    );
    """)
    connection.commit()
    print("Securities table created")

# %%
# Backfill Securities Table
def backfill_securities_table(portfolio, securities):
    for security in securities:
        ticker = security['ticker']
        print(f"Fetching info for {ticker}...")
        
        retries = 3
        info = None
        for i in range(retries):
            try:
                # Add a small delay before each attempt
                time.sleep((i+1) * 2) 
                info = yf.Ticker(ticker).info
                
                # Check if we got meaningful data
                if info and info.get('longName'):
                    print(f"Successfully fetched info for {ticker}.")
                    break # Succeeded, exit retry loop
                else:
                    raise ValueError("Empty or incomplete info dictionary returned.")

            except (HTTPError, ValueError, KeyError) as e:
                print(f"Attempt {i+1}/{retries} failed for {ticker}: {e}")
                if i == retries - 1:
                    print(f"All retries failed for {ticker}. Skipping.")
        
        if not info or not info.get('longName'):
            continue # Skip to the next security

        try:
            fund = security['fund']
            sector = security['sector'] 
            name = info['longName']
            geography = security['geography'] 
            type_disp = info.get('typeDisp') or info.get('quoteType')
            currency = info['currency']

            cursor.execute("""
            INSERT INTO Securities (ticker, name, type, geography, sector, fund, currency, portfolio)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            ticker = VALUES(ticker),
            name = VALUES(name),
            type = VALUES(type),
            geography = VALUES(geography),
            sector = VALUES(sector),
            fund = VALUES(fund),
            currency = VALUES(currency),
            portfolio = VALUES(portfolio);
            """, (ticker, name, type_disp, geography, sector, fund, currency, portfolio))
            connection.commit()
        except Exception as e:
            print(f"Error inserting {ticker} into database: {e}")

    print("Securities table backfilled")

# %%
# Drop Securities SQL Table
def drop_securities_table():
    cursor.execute("DROP TABLE IF EXISTS Securities")
    connection.commit()
    print("Securities table dropped")

# %% [markdown]
# # Transactions

# %%
# Create Transactions SQL Table

def create_transactions_table():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Transactions (
        transaction_id INTEGER PRIMARY KEY AUTO_INCREMENT,
        ticker VARCHAR(10) NOT NULL,
        date DATE NOT NULL,
        action ENUM('BUY', 'SELL') NOT NULL,
        shares INTEGER NOT NULL CHECK (shares > 0),
        price DECIMAL(20,10) NOT NULL CHECK (price > 0),
        currency CHAR(3) NOT NULL,
        portfolio VARCHAR(50) NOT NULL,
        FOREIGN KEY (ticker, portfolio) REFERENCES Securities(ticker, portfolio),
        UNIQUE (date, ticker, action, portfolio)
    );
    """)
    connection.commit()
    print("Transactions table created")

# %%
# Backfill Transactions Table

def backfill_transactions_table(portfolio, transactions):
    for transaction in transactions:
        print(f"{transaction['ticker']}", end=' ', flush=True)
        ticker = transaction['ticker']
        date = transaction['date']
        action = transaction['type']
        shares = transaction['quantity']
        price = transaction['price']
        currency = transaction['currency']

        cursor.execute("""
        INSERT INTO Transactions (ticker, portfolio, date, action, shares, price, currency)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
        shares = VALUES(shares), 
        price = VALUES(price), 
        currency = VALUES(currency)
        """, (ticker, portfolio, date, action, shares, price, currency))
        connection.commit()
    print()
    print("Transactions table backfilled")

# %%
# Drop Transactions SQL Table
def drop_transactions_table():
    cursor.execute("DROP TABLE IF EXISTS Transactions")
    connection.commit()
    print("Transactions table dropped")

# %% [markdown]
# # Currencies

# %%
def create_currencies_table():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Currencies (
        date DATE NOT NULL PRIMARY KEY,
        CAD DECIMAL(20,10)  DEFAULT 1.0,
        USD DECIMAL(20,10)  DEFAULT 1.0,
        EUR DECIMAL(20,10)  DEFAULT 1.0
    );
    """)
    connection.commit()
    print("Currencies table created")

# %%

# Backfill Currencies Table with corrected logic
def backfill_currencies_table(currencies):
    for currency in currencies:
        ticker = currency['ticker']
        data = yf.Ticker(ticker).history(start=start_date, end=end_date)['Close']
        data.index = data.index.date
        
        if currency['currency'] == 'USD':
            cursor.executemany("""
            INSERT INTO Currencies (date, CAD, USD, EUR)
            VALUES (%s, 1, %s, NULL)
            ON DUPLICATE KEY UPDATE
            USD = VALUES(USD);
            """, [(date, 1/rate) for date, rate in data.items()])
        elif currency['currency'] == 'EUR':
            cursor.executemany("""
            INSERT INTO Currencies (date, CAD, USD, EUR)
            VALUES (%s, 1, NULL, %s)
            ON DUPLICATE KEY UPDATE
            EUR = VALUES(EUR);
            """, [(date, 1/rate) for date, rate in data.items()])
        
        connection.commit()
        
    print("Currencies table backfilled")

# %%
# Drop Currencies SQL Table

def drop_currencies_table():
    cursor.execute("DROP TABLE IF EXISTS Currencies")
    connection.commit()
    print("Currencies table dropped")

# %% [markdown]
# # Dates (old)

# %%
def create_dates_table_old():
    # Create Dates SQL Table

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Dates (
        date DATE PRIMARY KEY
    );
    """)
    connection.commit()

# %%
def backfill_dates_table_old():

    # Backfill Dates Table

    sp500 = yf.Ticker('^GSPC').history(start=start_date, end=end_date)
    tsx = yf.Ticker('^GSPTSE').history(start=start_date, end=end_date)

    sp500.index = pd.to_datetime(sp500.index).tz_localize(None)
    tsx.index = pd.to_datetime(tsx.index).tz_localize(None)

    valid_dates = sp500.index.union(tsx.index)
    valid_dates = [date.date() for date in valid_dates]

    cursor.executemany("""
        INSERT INTO Dates (date)
        VALUES (%s)
        ON DUPLICATE KEY UPDATE date = VALUES(date);
    """, [(date,) for date in valid_dates])
    connection.commit()

# %%
# Drop Dates SQL Table  
def drop_dates_table_old():
    cursor.execute("DROP TABLE IF EXISTS Dates")
    connection.commit()

# %% [markdown]
# # Trading Calendar

# %%
def create_trading_calendar_table():

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS TradingCalendar (
        trading_date DATE PRIMARY KEY,
        is_us_trading_day BOOLEAN NOT NULL,
        is_ca_trading_day BOOLEAN NOT NULL
    );
    """)
    connection.commit()
    print("Trading calendar table created")

# %%
# Backfill Dates Table

def backfill_trading_calendar_table():

    sp500 = yf.Ticker('^GSPC').history(start=start_date, end=end_date)
    tsx = yf.Ticker('^GSPTSE').history(start=start_date, end=end_date)

    sp500.index = pd.to_datetime(sp500.index).tz_localize(None)
    tsx.index = pd.to_datetime(tsx.index).tz_localize(None)

    valid_US = set(date.date() for date in sp500.index)
    valid_CA = set(date.date() for date in tsx.index)

    valid_dates = sp500.index.union(tsx.index)
    
    # Prepare all data at once
    calendar_data = [
        (date.date(), date.date() in valid_US, date.date() in valid_CA)
        for date in valid_dates
    ]
    
    # Single executemany with all records
    cursor.executemany("""
    INSERT INTO TradingCalendar (trading_date, is_us_trading_day, is_ca_trading_day)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE 
        is_us_trading_day = VALUES(is_us_trading_day),
        is_ca_trading_day = VALUES(is_ca_trading_day);
    """, calendar_data)
    
    # Single commit at the end
    connection.commit()
    
    print("Trading calendar table backfilled")


# %%
# Drop Dates SQL Table

def drop_trading_calendar_table():
    cursor.execute("DROP TABLE IF EXISTS TradingCalendar")
    connection.commit()
    print("Trading calendar table dropped")
    

# %% [markdown]
# # Prices

# %%
def create_prices_table():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Prices (
        ticker VARCHAR(10) NOT NULL,
        portfolio VARCHAR(50) NOT NULL,
        trading_date DATE NOT NULL,
        price DECIMAL(20,10) NULL CHECK (price IS NULL OR price > 0),
        currency CHAR(3) NOT NULL,
        PRIMARY KEY (ticker, portfolio, trading_date),
        FOREIGN KEY (ticker, portfolio) REFERENCES Securities(ticker, portfolio)
    );
    """)
    connection.commit()
    print("Prices table created")

# %% [markdown]
# ### Will leave price gaps for holidays

# %%
def backfill_prices_table():

    # Get all unique ticker/portfolio combinations from Securities
    cursor.execute("""
        SELECT DISTINCT ticker, portfolio
        FROM Securities
    """)
    security_portfolios = cursor.fetchall()

    print("Backfilling prices for:", end=' ')
    for ticker, portfolio in security_portfolios:

        print(f"{ticker} ({portfolio})", end=' ', flush=True)
        
        # Get transaction dates for this ticker/portfolio combination
        cursor.execute("""
            SELECT date, action, shares
            FROM Transactions
            WHERE ticker = %s AND portfolio = %s
            ORDER BY date
        """, (ticker, portfolio))
        transactions = cursor.fetchall()

        # Calculate holding periods
        holding_periods = []
        current_position = 0
        period_start = None

        for date, action, shares in transactions:
            position_change = shares if action == 'BUY' else -shares
            old_position = current_position
            current_position += position_change
            
            if old_position == 0 and current_position > 0:
                period_start = date
            elif old_position > 0 and current_position == 0:
                holding_periods.append([period_start, date])
                period_start = None

        # Handle open position
        if current_position > 0:
            holding_periods.append([period_start, pd.to_datetime('today').date() + pd.Timedelta(days=1)])

        try:
            # Get currency for the ticker
            cursor.execute("""
                SELECT currency 
                FROM Securities 
                WHERE ticker = %s AND portfolio = %s
            """, (ticker, portfolio))
            currency = cursor.fetchone()[0]
            
            # Process each holding period
            for start_date, end_date in holding_periods:
                # Get all trading days for this period
                cursor.execute("""
                    SELECT trading_date 
                    FROM TradingCalendar
                    WHERE trading_date BETWEEN %s AND %s
                    ORDER BY trading_date
                """, (start_date, end_date))
                
                trading_days = [row[0] for row in cursor.fetchall()]
                
                if not trading_days:
                    continue
                    
# check this ------------------------------------------------------------------------------

                data = yf.Ticker(ticker).history(start=start_date, end=end_date, auto_adjust=False)
                data.index = data.index.date
                
                # Prepare price data including NULL prices for missing days
                price_data = []
                for trade_date in trading_days:
                    if trade_date in data.index:
                        price = float(data.loc[trade_date, 'Close'])
                    else:
                        price = None
                    
                    price_data.append((
                        ticker,
                        portfolio,
                        trade_date,
                        price,
                        currency
                    ))
                
                # Insert with NULL handling
                cursor.executemany("""
                    INSERT INTO Prices (ticker, portfolio, trading_date, price, currency)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        price = VALUES(price),
                        currency = VALUES(currency)
                """, price_data)
                
                connection.commit()
            
        except Exception as e:
            print(f"Error processing {ticker} in {portfolio}: {str(e)}")
            connection.rollback()

    print("")
    print("Prices table backfilled")

# %% [markdown]
# ### frontfills holiday prices missing from previous backfill
# 

# %%
def frontfill_prices_table():
    cursor.execute("""
        SELECT DISTINCT ticker, portfolio
        FROM Prices 
        WHERE price IS NULL
    """)
    securities_with_nulls = cursor.fetchall()

    print("Frontfilling prices for:", end=' ')

    for ticker, portfolio in securities_with_nulls:
        print(f"{ticker} ({portfolio})", end=' ', flush=True)
        
        cursor.execute("""
            WITH LastKnownPrice AS (
                SELECT 
                    p1.ticker,
                    p1.portfolio,
                    p1.trading_date,
                    (
                        SELECT p2.price 
                        FROM Prices p2 
                        WHERE p2.ticker = p1.ticker 
                            AND p2.portfolio = p1.portfolio
                            AND p2.trading_date < p1.trading_date 
                            AND p2.price IS NOT NULL 
                        ORDER BY p2.trading_date DESC 
                        LIMIT 1
                    ) as last_price
                FROM Prices p1
                WHERE p1.ticker = %s 
                    AND p1.portfolio = %s 
                    AND p1.price IS NULL
            )
            UPDATE Prices p
            JOIN LastKnownPrice lkp ON p.ticker = lkp.ticker 
                AND p.portfolio = lkp.portfolio 
                AND p.trading_date = lkp.trading_date
            SET p.price = lkp.last_price
            WHERE p.price IS NULL;
        """, (ticker, portfolio))
        
        connection.commit()

    print("Prices table frontfilled")

# %%
# Drop Dates SQL Table
def drop_prices_table():
    cursor.execute("DROP TABLE IF EXISTS Prices")
    connection.commit()
    print("Prices table dropped")

# %% [markdown]
# # Dividends

# %%
def create_dividends_table():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Dividends (
        ticker VARCHAR(10) NOT NULL,
        date DATE NOT NULL,
        portfolio VARCHAR(50) NOT NULL,
        amount DECIMAL(20,10) NOT NULL CHECK (amount > 0),
        currency CHAR(3) NOT NULL,
        PRIMARY KEY (ticker, date, portfolio),
        FOREIGN KEY (ticker, portfolio) REFERENCES Securities(ticker, portfolio)
    );
    """)
    connection.commit()
    print("Dividends table created")

# %%
# TODO: Only backfill dividends for dates where the security is in the portfolio (currently backfills entire history)

def backfill_dividends_table():
    cursor.execute("""
        SELECT DISTINCT ticker, portfolio
        FROM Securities
    """)
    security_portfolios = cursor.fetchall()

    print("Backfilling dividends for:", end=' ')
    for ticker, portfolio in security_portfolios:
        print(f"{ticker} ({portfolio})", end=' ', flush=True)
        
        # Get dividend data
        data = yf.Ticker(ticker)
        currency = yf.Ticker(ticker).info['currency']
        dividends = data.dividends
        
        # Prepare dividend data
        dividend_data = [
            (ticker, date.date(), portfolio, amount, currency)
            for date, amount in dividends.items()
            if amount > 0
        ]
        
        # Insert with NULL handling
        cursor.executemany("""
            INSERT INTO Dividends (ticker, date, portfolio, amount, currency)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                amount = VALUES(amount)
        """, dividend_data)
        
        connection.commit()

# %%
def drop_dividends_table():
    cursor.execute("DROP TABLE IF EXISTS Dividends")
    connection.commit()
    print("Dividends table dropped")

# %% [markdown]
# # Generate Cash Holdings Table

# %%
def create_cash_balances_table():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS CashBalances (
        date DATE PRIMARY KEY,
        cash_cad DECIMAL(20, 10) NOT NULL DEFAULT 0,
        cash_usd DECIMAL(20, 10) NOT NULL DEFAULT 0,
        cash_agg_cad DECIMAL(20, 10) NOT NULL DEFAULT 0
    );
    """)
    connection.commit()
    print("CashBalances table created")

def drop_cash_balances_table():
    cursor.execute("DROP TABLE IF EXISTS CashBalances")
    connection.commit()
    print("CashBalances table dropped")

# %%
def backfill_cash_balances_table():
    portfolio = 'core'
    # Get all trading dates
    cursor.execute("SELECT trading_date FROM TradingCalendar ORDER BY trading_date")
    dates = [row[0] for row in cursor.fetchall()]
    if not dates:
        print("No trading dates found.")
        return

    # Get all transactions for the core portfolio, ordered by date
    cursor.execute("""
        SELECT date, action, ticker, shares, price, currency
        FROM Transactions
        WHERE portfolio = %s
        ORDER BY date
    """, (portfolio,))
    transactions = cursor.fetchall()

    # Get all dividends for the core portfolio, ordered by date
    cursor.execute("""
        SELECT date, ticker, amount, currency
        FROM Dividends
        WHERE portfolio = %s
        ORDER BY date
    """, (portfolio,))
    dividends = cursor.fetchall()

    # Get currency rates for each date
    cursor.execute("SELECT date, CAD, USD FROM Currencies")
    currency_rates = {row[0]: {'CAD': row[1], 'USD': row[2]} for row in cursor.fetchall()}

    # Load starting cash from config.yaml
    with open("../../config/config.yaml", "r") as f:
        config = yaml.safe_load(f)
        starting_cash_cad = config.get('starting_cash_cad', 0.0)
        starting_cash_usd = config.get('starting_cash_usd', 0.0)

    # Initialize balances
    cash_cad = starting_cash_cad
    cash_usd = starting_cash_usd
    cash_balances = []
    tx_idx = 0
    div_idx = 0
    for date in dates:
        # Apply all transactions for this date
        while tx_idx < len(transactions) and transactions[tx_idx][0] == date:
            _, action, _, shares, price, currency = transactions[tx_idx]
            amount = shares * price
            usd_rate = currency_rates.get(date, {}).get('USD', 1.0)
            if action == 'BUY':
                if currency == 'CAD':
                    cash_cad -= amount
                elif currency == 'USD':
                    # If not enough USD cash, convert from CAD
                    if cash_usd < amount:
                        usd_needed = amount - cash_usd
                        cad_equiv = usd_needed * usd_rate
                        if cash_cad >= cad_equiv:
                            cash_cad -= cad_equiv
                            cash_usd += usd_needed
                        else:
                            # Not enough CAD to convert, convert as much as possible
                            usd_possible = cash_cad / usd_rate if usd_rate != 0 else 0
                            cash_usd += usd_possible
                            cash_cad = 0
                    cash_usd -= amount
            elif action == 'SELL':
                if currency == 'CAD':
                    cash_cad += amount
                elif currency == 'USD':
                    cash_usd += amount
            tx_idx += 1
        # Apply all dividends for this date
        while div_idx < len(dividends) and dividends[div_idx][0] == date:
            _, _, amount, currency = dividends[div_idx]
            if currency == 'CAD':
                cash_cad += amount
            elif currency == 'USD':
                cash_usd += amount
            div_idx += 1
        # Calculate aggregate cash in CAD
        usd_rate = currency_rates.get(date, {}).get('USD', 1.0)
        cash_agg_cad = cash_cad + (cash_usd * usd_rate)
        cash_balances.append((date, cash_cad, cash_usd, cash_agg_cad))
    # Insert into table
    cursor.executemany("""
        INSERT INTO CashBalances (date, cash_cad, cash_usd, cash_agg_cad)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            cash_cad = VALUES(cash_cad),
            cash_usd = VALUES(cash_usd),
            cash_agg_cad = VALUES(cash_agg_cad)
    """, cash_balances)
    connection.commit()
    print("CashBalances table backfilled")

# %% [markdown]
# # Generate Holdings Table (can delete)

# %%
# def create_holdings_view():
#     cursor.execute("""
#     CREATE OR REPLACE VIEW Holdings AS
#     SELECT
#         p.trading_date,
#         p.ticker,
#         p.portfolio,
#         s.name,
#         s.type,
#         s.geography,
#         s.sector,
#         s.fund,
#         s.currency AS security_currency,

#         -- Shares held calculation
#         (
#             SELECT SUM(
#                 CASE 
#                     WHEN t.action = 'BUY' THEN t.shares 
#                     ELSE -t.shares 
#                 END
#             )
#             FROM Transactions t
#             WHERE t.ticker = p.ticker 
#                 AND t.portfolio = p.portfolio
#                 AND t.date <= p.trading_date
#         ) AS shares_held,

#         p.price,

#         -- Market value calculation
#         (
#             (
#                 SELECT SUM(
#                     CASE 
#                         WHEN t.action = 'BUY' THEN t.shares 
#                         ELSE -t.shares 
#                     END
#                 )
#                 FROM Transactions t
#                 WHERE t.ticker = p.ticker 
#                     AND t.portfolio = p.portfolio
#                     AND t.date <= p.trading_date
#             ) * p.price
#         ) AS market_value,

#         -- Dividend market value calculation (only when shares were held)
#         (
#             SELECT COALESCE(SUM(sub.amount * sub.shares), 0)
#             FROM (
#                 SELECT
#                     d1.amount,
#                     (
#                         SELECT SUM(
#                             CASE 
#                                 WHEN t.action = 'BUY' THEN t.shares 
#                                 ELSE -t.shares 
#                             END
#                         )
#                         FROM Transactions t
#                         WHERE t.ticker = d1.ticker
#                             AND t.portfolio = d1.portfolio
#                             AND t.date <= d1.date
#                     ) AS shares
#                 FROM Dividends d1
#                 WHERE d1.ticker = p.ticker
#                     AND d1.portfolio = p.portfolio
#                     AND d1.date <= p.trading_date
#             ) AS sub
#             WHERE sub.shares > 0
#         ) AS dividend_market_value,

#         -- Total market value = market + dividend
#         (
#             (
#                 (
#                     SELECT SUM(
#                         CASE 
#                             WHEN t.action = 'BUY' THEN t.shares 
#                             ELSE -t.shares 
#                         END
#                     )
#                     FROM Transactions t
#                     WHERE t.ticker = p.ticker 
#                         AND t.portfolio = p.portfolio
#                         AND t.date <= p.trading_date
#                 ) * p.price
#             ) +
#             (
#                 SELECT COALESCE(SUM(sub.amount * sub.shares), 0)
#                 FROM (
#                     SELECT
#                         d1.amount,
#                         (
#                             SELECT SUM(
#                                 CASE 
#                                     WHEN t.action = 'BUY' THEN t.shares 
#                                     ELSE -t.shares 
#                                 END
#                             )
#                             FROM Transactions t
#                             WHERE t.ticker = d1.ticker
#                                 AND t.portfolio = d1.portfolio
#                                 AND t.date <= d1.date
#                         ) AS shares
#                     FROM Dividends d1
#                     WHERE d1.ticker = p.ticker
#                         AND d1.portfolio = p.portfolio
#                         AND d1.date <= p.trading_date
#                 ) AS sub
#                 WHERE sub.shares > 0
#             )
#         ) AS total_market_value

#     FROM Prices p
#     JOIN Securities s ON s.ticker = p.ticker AND s.portfolio = p.portfolio;
#     """)
#     connection.commit()
#     print("Holdings view created")


# %%
# def drop_holdings_view():
#     cursor.execute("DROP VIEW IF EXISTS Holdings")
#     connection.commit()
#     print("Holdings view dropped")


# %% [markdown]
# # Materialized Holdings (not view)

# %%
def create_materialized_holdings():
    # First, create the table with the same structure as our view
    cursor.execute("""
    CREATE TABLE MaterializedHoldings (
        trading_date DATE,
        ticker VARCHAR(10),
        portfolio VARCHAR(50),
        name VARCHAR(100),
        type VARCHAR(20),
        geography VARCHAR(50),
        sector VARCHAR(50),
        fund VARCHAR(50),
        security_currency CHAR(3),
        shares_held INTEGER,
        price DECIMAL(20,10),
        market_value DECIMAL(20,10),
        dividend_market_value DECIMAL(20,10),
        total_market_value DECIMAL(20,10),
        PRIMARY KEY (trading_date, ticker, portfolio)
    )
    """)
    connection.commit()
    print("Materialized Holdings table created")

# %%
def refresh_materialized_holdings():
    try:
        # Start transaction
        cursor.execute("START TRANSACTION")
        
        # Truncate the existing data
        cursor.execute("TRUNCATE TABLE MaterializedHoldings")
        
        # Insert fresh data
        cursor.execute("""
        INSERT INTO MaterializedHoldings
        SELECT
            p.trading_date,
            p.ticker,
            p.portfolio,
            s.name,
            s.type,
            s.geography,
            s.sector,
            s.fund,
            s.currency AS security_currency,
            (
                SELECT SUM(
                    CASE 
                        WHEN t.action = 'BUY' THEN t.shares 
                        ELSE -t.shares 
                    END
                )
                FROM Transactions t
                WHERE t.ticker = p.ticker 
                    AND t.portfolio = p.portfolio
                    AND t.date <= p.trading_date
            ) AS shares_held,
            p.price,
            (
                (
                    SELECT SUM(
                        CASE 
                            WHEN t.action = 'BUY' THEN t.shares 
                            ELSE -t.shares 
                        END
                    )
                    FROM Transactions t
                    WHERE t.ticker = p.ticker 
                        AND t.portfolio = p.portfolio
                        AND t.date <= p.trading_date
                ) * p.price
            ) AS market_value,
            (
                SELECT COALESCE(SUM(sub.amount * sub.shares), 0)
                FROM (
                    SELECT
                        d1.amount,
                        (
                            SELECT SUM(
                                CASE 
                                    WHEN t.action = 'BUY' THEN t.shares 
                                    ELSE -t.shares 
                                END
                            )
                            FROM Transactions t
                            WHERE t.ticker = d1.ticker
                                AND t.portfolio = d1.portfolio
                                AND t.date <= d1.date
                        ) AS shares
                    FROM Dividends d1
                    WHERE d1.ticker = p.ticker
                        AND d1.portfolio = p.portfolio
                        AND d1.date <= p.trading_date
                ) AS sub
                WHERE sub.shares > 0
            ) AS dividend_market_value,
            (
                (
                    (
                        SELECT SUM(
                            CASE 
                                WHEN t.action = 'BUY' THEN t.shares 
                                ELSE -t.shares 
                            END
                        )
                        FROM Transactions t
                        WHERE t.ticker = p.ticker 
                            AND t.portfolio = p.portfolio
                            AND t.date <= p.trading_date
                    ) * p.price
                ) +
                (
                    SELECT COALESCE(SUM(sub.amount * sub.shares), 0)
                    FROM (
                        SELECT
                            d1.amount,
                            (
                                SELECT SUM(
                                    CASE 
                                        WHEN t.action = 'BUY' THEN t.shares 
                                        ELSE -t.shares 
                                    END
                                )
                                FROM Transactions t
                                WHERE t.ticker = d1.ticker
                                    AND t.portfolio = d1.portfolio
                                    AND t.date <= d1.date
                            ) AS shares
                        FROM Dividends d1
                        WHERE d1.ticker = p.ticker
                            AND d1.portfolio = p.portfolio
                            AND d1.date <= p.trading_date
                    ) AS sub
                    WHERE sub.shares > 0
                )
            ) AS total_market_value
        FROM Prices p
        JOIN Securities s ON s.ticker = p.ticker AND s.portfolio = p.portfolio
        """)
        
        # Create indexes for better query performance
        # cursor.execute("""
        # CREATE INDEX idx_materialized_holdings_date ON MaterializedHoldings(trading_date);
        # CREATE INDEX idx_materialized_holdings_ticker ON MaterializedHoldings(ticker);
        # CREATE INDEX idx_materialized_holdings_portfolio ON MaterializedHoldings(portfolio);
        # """)
        
        # Commit the transaction
        connection.commit()
        print("Materialized Holdings refreshed successfully")
        
    except Exception as e:
        connection.rollback()
        print(f"Error refreshing materialized view: {str(e)}")

# %%
def drop_materialized_holdings():
    cursor.execute("DROP TABLE IF EXISTS MaterializedHoldings")
    connection.commit()
    print("Materialized Holdings table dropped")

# %% [markdown]
# # Performance Metrics
# (this needs to be adapted to calculate metrics from db data rather than csv before actual usage)

# %%
def drop_performance_metrics_table():
    cursor.execute("DROP TABLE IF EXISTS PerformanceReturns")
    connection.commit()
    print("PerformanceReturns table dropped")

def create_performance_metrics_table():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS PerformanceReturns (
        date DATE NOT NULL,
        portfolio VARCHAR(50) NOT NULL,
        one_day_return FLOAT,
        one_week_return FLOAT,
        one_month_return FLOAT,
        ytd_return FLOAT,
        one_year_return FLOAT,
        inception_return FLOAT,
        PRIMARY KEY (date, portfolio)
    );
    """)
    connection.commit()
    print("PerformanceReturns table created")

# def insert_performance_metrics(metrics_df, date=None, portfolio=None):
#     """
#     Insert a row into PerformanceReturns from a DataFrame row or dict.
#     metrics_df: DataFrame with columns ['Metric', 'Value']
#     date: date for the row (defaults to today if not provided)
#     portfolio: portfolio name (must be provided)
#     """
#     insert_query = """
#     INSERT INTO PerformanceReturns (
#         date,
#         portfolio,
#         one_day_return,
#         one_week_return,
#         one_month_return,
#         ytd_return,
#         one_year_return,
#         inception_return
#     )
#     VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
#     ON DUPLICATE KEY UPDATE
#         one_day_return = VALUES(one_day_return),
#         one_week_return = VALUES(one_week_return),
#         one_month_return = VALUES(one_month_return),
#         ytd_return = VALUES(ytd_return),
#         one_year_return = VALUES(one_year_return),
#         inception_return = VALUES(inception_return)
#     """
#     if date is None:
#         from datetime import datetime
#         date = datetime.now().date()
#     if portfolio is None:
#         raise ValueError("portfolio must be provided")
#     metrics_dict = pd.Series(metrics_df.Value.values, index=metrics_df.Metric).to_dict()
#     values = [
#         date,
#         portfolio,
#         float(metrics_dict['1 Day Return'].strip('%')),
#         float(metrics_dict['1 Week Return'].strip('%')),
#         float(metrics_dict['1 Month Return'].strip('%')),
#         float(metrics_dict['Year-to-Date Return'].strip('%')),
#         float(metrics_dict['1 Year Return'].strip('%')),
#         float(metrics_dict['Inception'].strip('%'))
#     ]
#     cursor.execute(insert_query, values)
#     connection.commit()
#     print(f"Inserted performance metrics for {portfolio} on {date}")

# %% [markdown]
# # Runner

# %%
drop_prices_table()
drop_transactions_table()
drop_dividends_table()
drop_securities_table()
drop_currencies_table()
drop_trading_calendar_table()
drop_cash_balances_table()
# drop_performance_metrics_table()
# drop_holdings_view()

drop_materialized_holdings() #--------------------------------

# %%
create_securities_table()
create_transactions_table()
create_currencies_table()
create_trading_calendar_table()
create_prices_table()
create_dividends_table()
create_cash_balances_table()

create_materialized_holdings() #--------------------------------

# Import config
with open("../../config/config.yaml", "r") as f:
    config = yaml.safe_load(f)
    start_date = config['start_date']

end_date = pd.to_datetime('today').date() + pd.Timedelta(days=1)

# # Import benchmark config
# with open("../../config/portfolio_definitions/dfic_benchmark.yaml", "r") as f:
#     config = yaml.safe_load(f)
#     securities = config['securities']
#     currencies = config['currencies']
#     transactions = config['transactions']
#     portfolio = config['portfolio']['name']

# backfill_securities_table(portfolio, securities)
# backfill_transactions_table(portfolio, transactions)

# Import core config
with open("../../config/portfolio_definitions/dfic_core.yaml", "r") as f:
    config = yaml.safe_load(f)
    securities = config['securities']
    currencies = config['currencies']
    transactions = config['transactions']
    portfolio = config['portfolio']['name']

backfill_securities_table(portfolio, securities)
backfill_transactions_table(portfolio, transactions)

backfill_currencies_table(currencies)

backfill_trading_calendar_table()

backfill_prices_table()
frontfill_prices_table()

backfill_dividends_table()
backfill_cash_balances_table()
# create_holdings_view()
refresh_materialized_holdings()#--------------------------------

# %%
if 'cursor' in locals():
    cursor.close()
if 'connection' in locals():
    connection.close()
    print("Database connection closed")


