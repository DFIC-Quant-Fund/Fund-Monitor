import os
import sys
import pandas as pd
import yfinance as yf

starting_cash = 101644.99
start_date = '2022-05-01'
# end_date = '2025-02-02'
end_date = pd.Timestamp.now().strftime('%Y-%m-%d')

trades_file = 'trades.csv'
prices_file = 'prices.csv'
dividends_file = 'dividends.csv'
holdings_file = 'holdings.csv'
cash_file = 'cash.csv'

market_values_file = 'market_values.csv'
dividend_values_file = 'dividend_values.csv'
exchange_rates_file = 'exchange_rates.csv'
exchange_rate_table_file = 'exchange_rate_table.csv'

class Portfolio:
    def __init__(self, start_date, end_date, starting_cash, folder_prefix):
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

        self.market_values = None
        self.dividend_values = None
        self.exchange_rates = None
        self.exchange_rate_table = None

        self.get_valid_dates()
        self.load_trades_data()

    def load_exchange_rates(self):
        self.exchange_rates = pd.DataFrame(index=self.valid_dates)

        exchange_rates = {
            "CAD": pd.Series(1.0, index=self.exchange_rates.index),
            "USD": yf.Ticker('CAD=X').history(start=self.start_date, end=self.end_date)['Close']
        }

        # Normalize dates
        for key, value in exchange_rates.items():
            exchange_rates[key].index = pd.to_datetime(value.index).tz_localize(None)
            self.exchange_rates[key] = exchange_rates[key]

        pd.DataFrame(self.exchange_rates).to_csv(os.path.join(self.output_folder, exchange_rates_file), index_label='Date')

    def load_trades_data(self):
        self.trades = pd.read_csv(os.path.join(self.input_folder, trades_file))
        self.trades['Date'] = pd.to_datetime(self.trades['Date'])
        self.trades.set_index('Date', inplace=True)
        self.tickers = sorted(self.trades['Ticker'].unique())

    def load_prices_data(self):
        self.prices = pd.DataFrame(index=self.valid_dates)

        for ticker in self.tickers:
            prices = yf.Ticker(ticker).history(start=self.start_date, end=self.end_date)['Close']
            prices.index = pd.to_datetime(prices.index).tz_localize(None)
            self.prices[ticker] = self.prices.index.map(lambda x: prices.get(x, None))

        # Forward fill missing prices (i.e. CAD stock on holiday but US market open and vice versa)
        self.prices = self.prices.ffill()

        pd.DataFrame(self.prices).to_csv(os.path.join(self.output_folder, prices_file), index_label='Date')

    def load_dividends_data(self):
        self.dividends = pd.DataFrame(index=self.valid_dates)

        for ticker in self.tickers:
            divs = yf.Ticker(ticker).dividends.loc[self.start_date:self.end_date]
            divs.index = pd.to_datetime(divs.index).tz_localize(None)
            self.dividends[ticker] = self.dividends.index.map(lambda x: divs.get(x, 0.0))

        pd.DataFrame(self.dividends).to_csv(os.path.join(self.output_folder, dividends_file), index_label='Date')

    def load_holdings_data(self):
        self.holdings = pd.DataFrame(index=self.valid_dates)
        self.cash = pd.DataFrame(index=self.valid_dates)

        self.cash.at[self.valid_dates[0], 'Cash'] = self.starting_cash
        for ticker in self.tickers: self.holdings[ticker] = 0.0

        for i, date in enumerate(self.valid_dates):
            
            if i != 0:
                self.holdings.loc[date] = self.holdings.loc[self.valid_dates[i - 1]]
                self.cash.loc[date] = self.cash.loc[self.valid_dates[i - 1]]

            if date in self.trades.index:
                print(f"Trades on {date}")
                print(f"{self.trades.loc[date]}")

                for _, row in self.trades.loc[date].iterrows():
                    quantity = row['Quantity']
                    currency = row['Currency']
                    ticker = row['Ticker']
                    price = row['Price']
                    self.holdings.at[date, ticker] = self.holdings.loc[date, ticker] + quantity
                    self.current_cash_balance -= quantity * price * self.exchange_rates.loc[date, currency]
                    self.cash.at[date, 'Cash'] = self.current_cash_balance
            else:
                print(f"No trades on {date}")

        pd.DataFrame(self.cash).to_csv(os.path.join(self.output_folder, cash_file), index_label='Date')
        pd.DataFrame(self.holdings).to_csv(os.path.join(self.output_folder, holdings_file), index_label='Date')

    def load_exchange_rate_table(self):
        self.exchange_rate_table = pd.DataFrame(index=self.valid_dates)

        for ticker in self.tickers:
            try:
                currency = yf.Ticker(ticker).info['currency']
            except:
                currency = 'CAD'
            print(f"Currency for {ticker}: {currency}")
            self.exchange_rate_table[ticker] = self.exchange_rates[currency] 

        pd.DataFrame(self.exchange_rate_table).to_csv(os.path.join(self.output_folder, exchange_rate_table_file), index_label='Date')

    def calculate_market_values(self):
        holdings_data = self.holdings[self.tickers]
        price_data = self.prices[self.tickers]
        exchange_rate_table_data = self.exchange_rate_table[self.tickers]

        self.market_values = price_data * holdings_data * exchange_rate_table_data

        pd.DataFrame(self.market_values).to_csv(os.path.join(self.output_folder, market_values_file), index_label='Date')

    def calculate_dividend_values(self):
        holdings_data = self.holdings[self.tickers]
        dividend_data = self.dividends[self.tickers]
        exchange_rate_table_data = self.exchange_rate_table[self.tickers]

        self.dividend_values = dividend_data * holdings_data * exchange_rate_table_data

        pd.DataFrame(self.dividend_values).to_csv(os.path.join(self.output_folder, dividend_values_file), index_label='Date')

    def calculate_final_values(self):
        market_values_total = self.market_values.loc[self.valid_dates[-1]].sum()
        cash_total = self.cash.loc[self.valid_dates[-1]].sum()
        dividends_total = self.dividend_values.sum().sum()

        print()
        print(f"Start Date: {self.start_date}")
        print(f"End Date: {self.end_date}")
        print()
        print(f"Starting Cash: {starting_cash:.2f}")
        print()
        print(f"Cash: {cash_total:.2f}")
        print(f"Market Value: {market_values_total:.2f}")
        print(f"Total Value: {(market_values_total + cash_total):.2f}")
        print(f"Profit/Loss: {((market_values_total + cash_total) / starting_cash - 1) * 100:.2f}%")
        print()
        print(f"Dividends: {dividends_total:.2f}")
        print(f"Total Value with Dividends: {(market_values_total + cash_total + dividends_total):.2f}")
        print(f"Profit/Loss with Dividends: {((market_values_total + cash_total + dividends_total) / starting_cash - 1) * 100:.2f}%")
        print()

    def get_valid_dates(self):
        sp500 = yf.Ticker('^GSPC').history(start=self.start_date, end=self.end_date)
        tsx = yf.Ticker('^GSPTSE').history(start=self.start_date, end=self.end_date)

        sp500.index = pd.to_datetime(sp500.index).tz_localize(None)
        tsx.index = pd.to_datetime(tsx.index).tz_localize(None)

        self.valid_dates = sp500.index.union(tsx.index)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 Portfolio.py <folder_prefix>")
    folder_prefix = sys.argv[1]
    portfolio = Portfolio(start_date, end_date, starting_cash, folder_prefix)

    portfolio.load_exchange_rates()
    portfolio.load_trades_data()
    portfolio.load_exchange_rate_table()

    portfolio.load_prices_data()
    portfolio.load_dividends_data()
    portfolio.load_holdings_data()

    portfolio.calculate_market_values()
    portfolio.calculate_dividend_values()

    portfolio.calculate_final_values()
