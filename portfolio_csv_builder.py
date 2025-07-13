import os
import sys
import pandas as pd
import yfinance as yf
from datetime import timedelta


'''
FILE PURPOSE: GOAL IS TO SET UP METRICS AND FILL PRIMARY OUTPUT TABLES 
Done for all days from start of fund till current 
Rakes into account active trades made (e.g. for holdings file)
Run every day (first thing run in github actions) 
'''

starting_cash = 101644.99
start_date = '2022-05-01'
# end_date = '2025-02-02'
end_date = (pd.Timestamp.now() + timedelta(days=1)).strftime('%Y-%m-%d') # yfinance end_dates are exclusive for download and history functions

# file names as variables 
trades_file = 'trades.csv'
prices_file = 'prices.csv'
holdings_file = 'holdings.csv'
cash_file = 'cash.csv'

market_values_file = 'market_values.csv'
exchange_rates_file = 'exchange_rates.csv'

dividend_per_share_file = 'dividend_per_share.csv'
cad_dividend_income_file = 'cad_dividend_income.csv'

class Portfolio:
    def __init__(self, start_date, end_date, starting_cash, folder_prefix):
        # initlaize basic information 
        self.start_date = start_date
        self.end_date = end_date
        self.starting_cash = starting_cash
        self.current_cash_balance = starting_cash

        self.input_folder = os.path.join("data", folder_prefix, "input")
        self.output_folder = os.path.join("data", folder_prefix, "output")
        os.makedirs(self.output_folder, exist_ok=True)

        self.tickers = None
        self.valid_dates = None

        self.trades = None
        self.prices = None
        self.dividends = None
        self.holdings = None
        self.cash = None

        self.cad_market_values = None
        self.exchange_rates = None

        self.dividend_per_share = None
        self.cad_dividend_income = None

        # call valid dates function to get dates that both TSX and American exchanges open 
        self.get_valid_dates()
        # all tickers invested in from trades csv 
        self.load_trades()

    def create_table_exchange_rates(self):
        # exchange rates from web and shave them for all start and end dates 
        self.exchange_rates = pd.DataFrame(index=self.valid_dates)

        exchange_rates = {
            "CAD": pd.Series(1.0, index=self.exchange_rates.index),
            "USD": yf.Ticker('CAD=X').history(start=self.start_date, end=self.end_date)['Close']
        }

        # Normalize dates
        for key, value in exchange_rates.items():
            exchange_rates[key].index = pd.to_datetime(value.index).tz_localize(None)
            self.exchange_rates[key] = exchange_rates[key]

        # Fill missing values with forward fill
        self.exchange_rates = self.exchange_rates.ffill()

        pd.DataFrame(self.exchange_rates).to_csv(os.path.join(self.output_folder, exchange_rates_file), index_label='Date')

    def load_trades(self):
        self.trades = pd.read_csv(os.path.join(self.input_folder, trades_file))
        self.trades['Date'] = pd.to_datetime(self.trades['Date'])
        self.trades.set_index('Date', inplace=True)
        self.tickers = sorted(self.trades['Ticker'].unique())

    def create_table_prices(self):
        self.prices = pd.DataFrame(index=self.valid_dates)

        for ticker in self.tickers:
            prices = yf.Ticker(ticker).history(start=self.start_date, end=self.end_date)['Close']
            prices.index = pd.to_datetime(prices.index).tz_localize(None)
            self.prices[ticker] = self.prices.index.map(lambda x: prices.get(x, None))

        # Forward fill missing prices (i.e. CAD stock on holiday but US market open and vice versa)
        self.prices = self.prices.ffill()

        pd.DataFrame(self.prices).to_csv(os.path.join(self.output_folder, prices_file), index_label='Date')

    def create_table_dividend_per_share(self):
        self.dividends = pd.DataFrame(index=self.valid_dates)

        for ticker in self.tickers:
            divs = yf.Ticker(ticker).dividends.loc[self.start_date:self.end_date]
            divs.index = pd.to_datetime(divs.index).tz_localize(None)
            self.dividends[ticker] = self.dividends.index.map(lambda x: divs.get(x, 0.0))

        pd.DataFrame(self.dividends).to_csv(os.path.join(self.output_folder, dividend_per_share_file), index_label='Date')

    def create_table_holdings(self):
        # function: amount of stocks we are holding on a certain date 

        self.holdings = pd.DataFrame(index=self.valid_dates)
        for ticker in self.tickers: self.holdings[ticker] = 0.0

        for i, date in enumerate(self.valid_dates):
            
            if i != 0:
                self.holdings.loc[date] = self.holdings.loc[self.valid_dates[i - 1]]

            if date in self.trades.index:
                print(f"Trades on {date}")
                print(f"{self.trades.loc[date]}")

                for _, row in self.trades.loc[date].iterrows():
                    quantity = row['Quantity']
                    ticker = row['Ticker']
                    self.holdings.at[date, ticker] = self.holdings.loc[date, ticker] + quantity
            else:
                print(f"No trades on {date}")

        pd.DataFrame(self.holdings).to_csv(os.path.join(self.output_folder, holdings_file), index_label='Date')

    def create_table_cash(self):
        # function: track cash balance over time

        self.cash = pd.DataFrame(index=self.valid_dates)
        self.cash['CAD_Cash'] = 0.0
        self.cash['USD_Cash'] = 0.0
        self.cash['Total_CAD'] = 0.0
        
        # Initialize starting cash (assumed to be in CAD)
        self.cash.at[self.valid_dates[0], 'CAD_Cash'] = self.starting_cash
        self.cash.at[self.valid_dates[0], 'Total_CAD'] = self.starting_cash
        
        # Track current balances
        current_cad_cash = self.starting_cash
        current_usd_cash = 0.0

        for i, date in enumerate(self.valid_dates):
            
            if i != 0:
                self.cash.loc[date] = self.cash.loc[self.valid_dates[i - 1]]
                current_cad_cash = self.cash.loc[date, 'CAD_Cash']
                current_usd_cash = self.cash.loc[date, 'USD_Cash']

            if date in self.trades.index:
                for _, row in self.trades.loc[date].iterrows():
                    quantity = row['Quantity']
                    currency = row['Currency']
                    price = row['Price']
                    trade_value = quantity * price
                    
                    if currency == 'CAD':
                        # For CAD trades, use CAD cash directly
                        current_cad_cash -= trade_value
                    elif currency == 'USD':
                        # For USD trades, use USD cash first, convert CAD if needed
                        if current_usd_cash >= trade_value:
                            # We have enough USD cash
                            current_usd_cash -= trade_value
                        else:
                            # Need to convert some CAD to USD
                            usd_needed = trade_value - current_usd_cash
                            cad_to_convert = usd_needed / self.exchange_rates.loc[date, 'USD']
                            
                            # Use all available USD cash
                            current_usd_cash = 0
                            # Convert CAD to USD and deduct from CAD balance
                            current_cad_cash -= cad_to_convert
                    
                    # Update cash balances
                    self.cash.at[date, 'CAD_Cash'] = current_cad_cash
                    self.cash.at[date, 'USD_Cash'] = current_usd_cash
                    
                    # Calculate total in CAD
                    total_cad = current_cad_cash + (current_usd_cash * self.exchange_rates.loc[date, 'USD'])
                    self.cash.at[date, 'Total_CAD'] = total_cad

        pd.DataFrame(self.cash).to_csv(os.path.join(self.output_folder, cash_file), index_label='Date')


    def create_table_cad_market_values(self):
        holdings = self.holdings[self.tickers]
        prices = self.prices[self.tickers]
        
        # Convert to CAD directly using exchange rates
        market_values_cad = pd.DataFrame(index=self.valid_dates)
        for ticker in self.tickers:
            try:
                currency = yf.Ticker(ticker).info['currency']
            except:
                currency = 'CAD'
            market_values_cad[ticker] = prices[ticker] * holdings[ticker] * self.exchange_rates[currency]

        self.cad_market_values = market_values_cad
        pd.DataFrame(self.cad_market_values).to_csv(os.path.join(self.output_folder, market_values_file), index_label='Date')

    def create_table_dividend_per_share(self):
        self.dividend_per_share = pd.DataFrame(index=self.valid_dates)
        for ticker in self.tickers:
            divs = yf.Ticker(ticker).dividends.loc[self.start_date:self.end_date]
            divs.index = pd.to_datetime(divs.index).tz_localize(None)
            self.dividend_per_share[ticker] = self.dividend_per_share.index.map(lambda x: divs.get(x, 0.0))
        pd.DataFrame(self.dividend_per_share).to_csv(os.path.join(self.output_folder, dividend_per_share_file), index_label='Date')

    def create_table_cad_dividend_income(self):
        holdings = self.holdings[self.tickers]
        dividend = self.dividend_per_share[self.tickers]
        cad_dividend_income = pd.DataFrame(index=self.valid_dates)
        for ticker in self.tickers:
            try:
                currency = yf.Ticker(ticker).info['currency']
            except:
                currency = 'CAD'
            cad_dividend_income[ticker] = dividend[ticker] * holdings[ticker] * self.exchange_rates[currency]
        self.cad_dividend_income = cad_dividend_income
        pd.DataFrame(self.cad_dividend_income).to_csv(os.path.join(self.output_folder, cad_dividend_income_file), index_label='Date')

    def calculate_final_values(self):
        market_values_total = self.cad_market_values.loc[self.valid_dates[-1]].sum()
        cash_total_cad = self.cash.loc[self.valid_dates[-1], 'Total_CAD']
        dividends_total = self.cad_dividend_income.sum().sum()

        print()
        print(f"Start Date: {self.start_date}")
        print(f"End Date: {(pd.to_datetime(self.end_date) - timedelta(days=1)).strftime('%Y-%m-%d')}")
        print()
        print(f"Starting Cash: {starting_cash:.2f}")
        print()
        print(f"CAD Cash: {self.cash.loc[self.valid_dates[-1], 'CAD_Cash']:.2f}")
        print(f"USD Cash: {self.cash.loc[self.valid_dates[-1], 'USD_Cash']:.2f}")
        print(f"Total Cash (CAD): {cash_total_cad:.2f}")
        print(f"Market Value: {market_values_total:.2f}")
        print(f"Total Value: {(market_values_total + cash_total_cad):.2f}")
        print(f"Profit/Loss: {((market_values_total + cash_total_cad) / starting_cash - 1) * 100:.2f}%")
        print()
        print(f"Dividends: {dividends_total:.2f}")
        print(f"Total Value with Dividends: {(market_values_total + cash_total_cad + dividends_total):.2f}")
        print(f"Profit/Loss with Dividends: {((market_values_total + cash_total_cad + dividends_total) / starting_cash - 1) * 100:.2f}%")
        print()

    def get_valid_dates(self):
        sp500 = yf.Ticker('^GSPC').history(start=self.start_date, end=self.end_date)
        tsx = yf.Ticker('^GSPTSE').history(start=self.start_date, end=self.end_date)

        sp500.index = pd.to_datetime(sp500.index).tz_localize(None)
        tsx.index = pd.to_datetime(tsx.index).tz_localize(None)

        self.valid_dates = sp500.index.union(tsx.index)

if __name__ == '__main__':
    # only runs if arguments are at least 2 - need to know where to put input and output data 
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 Portfolio.py <folder_prefix>")
    folder_prefix = sys.argv[1]
    # initlialze instance of portfolio main function  - all parameters are global variables 
    portfolio = Portfolio(start_date, end_date, starting_cash, folder_prefix)

    # load functions after intial set up - fills all output CSVs 
    portfolio.create_table_exchange_rates()
    portfolio.load_trades()

    portfolio.create_table_prices()
    portfolio.create_table_holdings()
    portfolio.create_table_cad_market_values()
    portfolio.create_table_cash()

    portfolio.create_table_dividend_per_share()
    portfolio.create_table_cad_dividend_income()

    portfolio.calculate_final_values()
