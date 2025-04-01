# %% [markdown]
# # Imports and Configs

# %%
import mysql.connector
import os
import pandas as pd
import yfinance as yf
import yaml
from dotenv import load_dotenv

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
        data = yf.Ticker(ticker)
        fund = security['fund']
        sector = security['sector'] 
        name = data.info['longName']
        geography = security['geography'] 
        type = data.info['typeDisp']
        currency = data.info['currency']

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
        """, (ticker, name, type, geography, sector, fund, currency, portfolio))
        connection.commit()

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
# # Dividends (WIP)

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
# # Generate Holdings Table

# %%
def create_holdings_view():
    cursor.execute("""
    CREATE OR REPLACE VIEW Holdings AS
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

        -- Shares held calculation
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

        -- Market value calculation
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

        -- Dividend market value calculation (only when shares were held)
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

        -- Total market value = market + dividend
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
    JOIN Securities s ON s.ticker = p.ticker AND s.portfolio = p.portfolio;
    """)
    connection.commit()
    print("Holdings view created")


# %%
def drop_holdings_view():
    cursor.execute("DROP VIEW IF EXISTS Holdings")
    connection.commit()
    print("Holdings view dropped")


# %% [markdown]
# # Runner

# %%
drop_prices_table()
drop_transactions_table()
drop_dividends_table()
drop_securities_table()
drop_currencies_table()
drop_trading_calendar_table()
drop_holdings_view()

# %%
create_securities_table()
create_transactions_table()
create_currencies_table()
create_trading_calendar_table()
create_prices_table()
create_dividends_table()

# Import config
with open("../config.yaml", "r") as f:
    config = yaml.safe_load(f)
    start_date = config['start_date']

end_date = pd.to_datetime('today').date() + pd.Timedelta(days=1)

# Import benchmark config
with open("../portfolios/dfic_benchmark.yaml", "r") as f:
    config = yaml.safe_load(f)
    securities = config['securities']
    currencies = config['currencies']
    transactions = config['transactions']
    portfolio = config['portfolio']['name']

backfill_securities_table(portfolio, securities)
backfill_transactions_table(portfolio, transactions)

# Import core config
with open("../portfolios/dfic_core.yaml", "r") as f:
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

create_holdings_view()

# %%
if 'cursor' in locals():
    cursor.close()
if 'connection' in locals():
    connection.close()
    print("Database connection closed")


