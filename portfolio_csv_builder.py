import os
import sys
import pandas as pd
import yfinance as yf
from datetime import timedelta


'''
FILE PURPOSE: GOAL IS TO SET UP METRICS AND FILL PRIMARY OUTPUT TABLES 
Done for all days from start of fund till current 
Takes into account active trades made (e.g. for holdings file)
Run every day (first thing run in github actions) 
'''

# TODO: Clean this up
STARTING_CASH = 101644.99
start_date = '2022-05-01'
end_date = (pd.Timestamp.now() + timedelta(days=1)).strftime('%Y-%m-%d') # yfinance end_dates are exclusive for download and history functions

# file names as variables 
trades_file = 'trades.csv'
prices_file = 'prices.csv'
holdings_file = 'holdings.csv'
cash_file = 'cash.csv'

market_values_file = 'market_values.csv'
exchange_rates_file = 'exchange_rates.csv'

dividend_per_share_file = 'dividend_per_share.csv'
dividend_income_file = 'dividend_income.csv'

class Portfolio:
    def __init__(self, start_date, end_date, STARTING_CASH, folder_prefix):
        self.start_date = start_date
        self.end_date = end_date
        self.STARTING_CASH = STARTING_CASH
        self.current_cash_balance = STARTING_CASH

        self.input_folder = os.path.join("data", folder_prefix, "input")
        self.output_folder = os.path.join("data", folder_prefix, "output")
        os.makedirs(self.output_folder, exist_ok=True)

        self.tickers = None
        self.valid_dates = None

        self.trades = None
        self.prices = None
        self.holdings = None
        self.cash = None

        self.cad_market_values = None
        self.exchange_rates = None

        self.dividend_per_share = None
        self.dividend_income = None

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
        # TODO: Make this currency cache a class variable potentially
        ticker_currency = {}
        for ticker in self.tickers:
            try:
                ticker_currency[ticker] = yf.Ticker(ticker).info.get('currency', 'CAD')
            except Exception:
                ticker_currency[ticker] = 'CAD'

        self.cash = pd.DataFrame(index=self.valid_dates)
        self.cash['CAD_Cash'] = 0.0
        self.cash['USD_Cash'] = 0.0
        self.cash['Total_CAD'] = 0.0
        
        # Initialize starting cash (assumed to be in CAD)
        self.cash.at[self.valid_dates[0], 'CAD_Cash'] = self.STARTING_CASH
        self.cash.at[self.valid_dates[0], 'Total_CAD'] = self.STARTING_CASH
        
        # Track current balances
        current_cad_cash = self.STARTING_CASH
        current_usd_cash = 0.0

        for i, date in enumerate(self.valid_dates):
            
            if i != 0:
                self.cash.loc[date] = self.cash.loc[self.valid_dates[i - 1]]
                current_cad_cash = self.cash.loc[date, 'CAD_Cash']
                current_usd_cash = self.cash.loc[date, 'USD_Cash']

            # Process trades for this date
            if date in self.trades.index:
                print(f"\n--- Processing trades on {date.strftime('%Y-%m-%d')} ---")
                print(f"Starting balances - CAD: ${current_cad_cash:.2f}, USD: ${current_usd_cash:.2f}")
                
                for _, row in self.trades.loc[date].iterrows():
                    quantity = row['Quantity']
                    currency = row['Currency']
                    price = row['Price']
                    ticker = row['Ticker']
                    trade_value = abs(quantity * price)

                    print(f"\n  Trade: {ticker} - {quantity} shares @ ${price:.2f} {currency}")
                    print(f"  Trade value: ${trade_value:.2f} {currency}")

                    if quantity > 0:
                        # Buy: Deduct cash using helper
                        current_cad_cash, current_usd_cash, conversion_type = self._convert_currency_for_trade(
                            trade_value, currency, current_cad_cash, current_usd_cash, date
                        )
                        print(f"  Buy: Decreased cash for purchase.")
                    elif quantity < 0:
                        # Sell: Add proceeds to correct cash balance
                        if currency == 'CAD':
                            current_cad_cash += trade_value
                            print(f"  Sell: Increased CAD cash by ${trade_value:.2f}")
                        elif currency == 'USD':
                            current_usd_cash += trade_value
                            print(f"  Sell: Increased USD cash by ${trade_value:.2f}")
                        else:
                            # If unknown currency, default to CAD
                            current_cad_cash += trade_value
                            print(f"  Sell: Unknown currency, increased CAD cash by ${trade_value:.2f}")

                    # Update cash balances
                    self.cash.at[date, 'CAD_Cash'] = current_cad_cash
                    self.cash.at[date, 'USD_Cash'] = current_usd_cash
                    # Calculate total in CAD
                    total_cad = current_cad_cash + (current_usd_cash * self.exchange_rates.loc[date, 'USD'])
                    self.cash.at[date, 'Total_CAD'] = total_cad
                    print(f"  After trade - CAD: ${current_cad_cash:.2f}, USD: ${current_usd_cash:.2f}, Total CAD: ${total_cad:.2f}")

            # Process dividends for this date
            if self.dividend_income is not None and date in self.dividend_income.index:
                print(f"\n--- Processing dividends on {date.strftime('%Y-%m-%d')} ---")
                print(f"Starting balances - CAD: ${current_cad_cash:.2f}, USD: ${current_usd_cash:.2f}")
                
                for ticker in self.tickers:
                    dividend_amount = self.dividend_income.at[date, ticker] if ticker in self.dividend_income.columns else 0.0
                    if pd.isna(dividend_amount) or dividend_amount == 0.0:
                        continue
                    currency = ticker_currency.get(ticker, 'CAD')
                    print(f"\n  Dividend: {ticker} - ${dividend_amount:.2f} {currency}")
                    # Add dividend to appropriate currency balance
                    if currency == 'CAD':
                        current_cad_cash += dividend_amount
                        print(f"  Added ${dividend_amount:.2f} to CAD cash")
                    elif currency == 'USD':
                        current_usd_cash += dividend_amount
                        print(f"  Added ${dividend_amount:.2f} to USD cash")
                    else:
                        # If unknown currency, default to CAD
                        current_cad_cash += dividend_amount
                        print(f"  Unknown currency, added ${dividend_amount:.2f} to CAD cash")
                    # Update cash balances
                    self.cash.at[date, 'CAD_Cash'] = current_cad_cash
                    self.cash.at[date, 'USD_Cash'] = current_usd_cash
                    # Calculate total in CAD
                    total_cad = current_cad_cash + (current_usd_cash * self.exchange_rates.loc[date, 'USD'])
                    self.cash.at[date, 'Total_CAD'] = total_cad
                    print(f"  After dividend - CAD: ${current_cad_cash:.2f}, USD: ${current_usd_cash:.2f}, Total CAD: ${total_cad:.2f}")

        pd.DataFrame(self.cash).to_csv(os.path.join(self.output_folder, cash_file), index_label='Date')

    def _convert_currency_for_trade(self, trade_value, trade_currency, current_cad_cash, current_usd_cash, date):
        """
        Helper function to handle currency conversion for trades.
        
        Args:
            trade_value: Amount of the trade
            trade_currency: Currency of the trade ('CAD' or 'USD')
            current_cad_cash: Current CAD cash balance
            current_usd_cash: Current USD cash balance
            date: Date of the trade for exchange rate lookup
            
        Returns:
            tuple: (new_cad_cash, new_usd_cash, conversion_details)
        """
        if trade_currency == 'CAD':
            # For CAD trades, use CAD cash first, convert USD if needed
            if current_cad_cash >= trade_value:
                # We have enough CAD cash
                print(f"  CAD trade - using existing CAD cash (${current_cad_cash:.2f} available)")
                return current_cad_cash - trade_value, current_usd_cash, "used_cad_cash"
            else:
                # Need to convert some USD to CAD
                cad_needed = trade_value - current_cad_cash
                usd_to_convert = cad_needed / self.exchange_rates.loc[date, 'USD']
                exchange_rate = self.exchange_rates.loc[date, 'USD']
                
                print(f"  CAD trade - need ${cad_needed:.2f} more CAD")
                print(f"  Converting ${usd_to_convert:.2f} USD to CAD (rate: {exchange_rate:.4f})")
                print(f"  Using all available CAD cash: ${current_cad_cash:.2f}")
                
                # Use all available CAD cash and convert USD
                new_cad_cash = 0
                new_usd_cash = current_usd_cash - usd_to_convert
                return new_cad_cash, new_usd_cash, "converted_usd_to_cad"
        elif trade_currency == 'USD':
            # For USD trades, use USD cash first, convert CAD if needed
            if current_usd_cash >= trade_value:
                # We have enough USD cash
                print(f"  USD trade - using existing USD cash (${current_usd_cash:.2f} available)")
                return current_cad_cash, current_usd_cash - trade_value, "used_usd_cash"
            else:
                # Need to convert some CAD to USD
                usd_needed = trade_value - current_usd_cash
                cad_to_convert = usd_needed * self.exchange_rates.loc[date, 'USD']
                exchange_rate = self.exchange_rates.loc[date, 'USD']
                
                print(f"  USD trade - need ${usd_needed:.2f} more USD")
                print(f"  Converting ${cad_to_convert:.2f} CAD to USD (rate: {exchange_rate:.4f})")
                print(f"  Using all available USD cash: ${current_usd_cash:.2f}")
                
                # Use all available USD cash and convert CAD
                new_cad_cash = current_cad_cash - cad_to_convert
                new_usd_cash = 0
                return new_cad_cash, new_usd_cash, "converted_cad_to_usd"

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
        # Only keep rows with at least one nonzero value
        nonzero_div_per_share = self.dividend_per_share[(self.dividend_per_share != 0).any(axis=1)]
        nonzero_div_per_share.to_csv(os.path.join(self.output_folder, dividend_per_share_file), index_label='Date')

    def create_table_dividend_income(self):
        holdings = self.holdings[self.tickers]
        dividend = self.dividend_per_share[self.tickers]
        dividend_income = pd.DataFrame(index=self.valid_dates)
        for ticker in self.tickers:
            dividend_income[ticker] = dividend[ticker] * holdings[ticker]
        self.dividend_income = dividend_income
        # Only keep rows with at least one nonzero value
        nonzero_div_income = self.dividend_income[(self.dividend_income != 0).any(axis=1)]
        nonzero_div_income.to_csv(os.path.join(self.output_folder, dividend_income_file), index_label='Date')

    # TODO: to remove this because this should be done by a dedicated calculator class/file
    def print_final_values(self):
        market_values_total = self.cad_market_values.loc[self.valid_dates[-1]].sum()
        cash_total_cad = self.cash.loc[self.valid_dates[-1], 'Total_CAD']
        
        # Calculate dividends by currency
        cad_dividends = 0.0
        usd_dividends = 0.0
        if self.dividend_income is not None:
            for ticker in self.tickers:
                try:
                    currency = yf.Ticker(ticker).info.get('currency', 'CAD')
                except Exception:
                    currency = 'CAD'
                
                ticker_dividends = self.dividend_income[ticker].sum()
                if currency == 'USD':
                    usd_dividends += ticker_dividends
                else:
                    # CAD dividends (or unknown currency defaults to CAD)
                    cad_dividends += ticker_dividends
        
        # Convert USD dividends to CAD for total
        avg_exchange_rate = self.exchange_rates['USD'].mean()
        usd_dividends_cad = usd_dividends * avg_exchange_rate
        total_dividends_cad = cad_dividends + usd_dividends_cad

        print()
        print(f"Start Date: {self.start_date}")
        print(f"End Date: {(pd.to_datetime(self.end_date) - timedelta(days=1)).strftime('%Y-%m-%d')}")
        print()
        print(f"Starting Cash: {STARTING_CASH:.2f}")
        print()
        print(f"CAD Cash (including dividends): {self.cash.loc[self.valid_dates[-1], 'CAD_Cash']:.2f}")
        print(f"USD Cash (including dividends): {self.cash.loc[self.valid_dates[-1], 'USD_Cash']:.2f}")
        print(f"CAD Dividends: {cad_dividends:.2f}")
        print(f"USD Dividends: {usd_dividends:.2f}")
        print(f"Total Dividends (CAD): {total_dividends_cad:.2f}")
        print(f"Total Cash (CAD, including dividends): {cash_total_cad:.2f}")
        print(f"Market Value of holdings: {market_values_total:.2f}")
        print(f"Total Value of portfolio: {(market_values_total + cash_total_cad):.2f}")
        print(f"Total Return: {((market_values_total + cash_total_cad) / STARTING_CASH - 1) * 100:.2f}%")

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
    portfolio = Portfolio(start_date, end_date, STARTING_CASH, folder_prefix)

    # load functions after intial set up - fills all output CSVs 
    portfolio.create_table_exchange_rates()
    portfolio.load_trades()

    portfolio.create_table_prices()
    portfolio.create_table_holdings()
    portfolio.create_table_cad_market_values()
    portfolio.create_table_dividend_per_share()
    portfolio.create_table_dividend_income()
    portfolio.create_table_cash()

    portfolio.print_final_values()
