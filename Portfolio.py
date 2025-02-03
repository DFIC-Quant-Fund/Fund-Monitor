import os
import pandas as pd
import yfinance as yf

starting_cash = 101644.99
start_date = '2022-05-01'
end_date = '2025-01-17'

input_folder = 'input'
output_folder = 'output'
os.makedirs(output_folder, exist_ok=True)

trades_file = 'trades.csv'
prices_file = 'prices.csv'
dividends_file = 'dividends.csv'
holdings_file = 'holdings.csv'

market_values_file = 'market_values.csv'
dividend_values_file = 'dividend_values.csv'
exchange_rates_file = 'exchange_rates.csv'
exchange_rate_table_file = 'exchange_rate_table.csv'

class Portfolio:
    def __init__(self, start_date, end_date, starting_cash):
        self.start_date = start_date
        self.end_date = end_date
        self.cash = starting_cash

        self.tickers = None

        self.trades = None
        self.prices = None
        self.dividends = None
        self.holdings = None

        self.market_values = None
        self.dividend_values = None
        self.exchange_rates = None

    def load_exchange_rates(self):
        self.exchange_rates = pd.DataFrame(index=pd.date_range(self.start_date, self.end_date))

        exchange_rates = {
            "CAD": pd.Series(1.0, index=self.exchange_rates.index),
            "USD": yf.Ticker('CAD=X').history(start=self.start_date, end=self.end_date)['Close']
        }

        # Normalize dates
        for key, value in exchange_rates.items():
            exchange_rates[key].index = pd.to_datetime(value.index).tz_localize(None)
            self.exchange_rates[key] = exchange_rates[key]

        pd.DataFrame(self.exchange_rates).to_csv(os.path.join(output_folder, exchange_rates_file), index_label='Date')

    def load_trades_data(self):
        self.trades = pd.read_csv(os.path.join(input_folder, trades_file))
        self.trades['Date'] = pd.to_datetime(self.trades['Date'])
        self.trades.set_index('Date', inplace=True)
        self.tickers = sorted(self.trades['Ticker'].unique())

    def load_prices_data(self):
        self.prices = pd.DataFrame(index=pd.date_range(self.start_date, self.end_date))

        for ticker in self.tickers:
            prices = yf.Ticker(ticker).history(start=self.start_date, end=self.end_date)['Close']
            prices.index = pd.to_datetime(prices.index).tz_localize(None)
            self.prices[ticker] = self.prices.index.map(lambda x: prices.get(x, 0.0))

        # One line option (will skip weekends and holidays since markets are closed)
        # self.prices = yf.download(self.tickers, start=self.start_date, end=self.end_date)['Close']

    def load_dividends_data(self):
        self.dividends = pd.DataFrame(index=pd.date_range(self.start_date, self.end_date))

        for ticker in self.tickers:
            divs = yf.Ticker(ticker).dividends.loc[self.start_date:self.end_date]
            divs.index = pd.to_datetime(divs.index).tz_localize(None)
            self.dividends[ticker] = self.dividends.index.map(lambda x: divs.get(x, 0.0))

    def load_holdings_data(self):
        self.holdings = pd.DataFrame(index=pd.date_range(self.start_date, self.end_date))

        for ticker in self.tickers:
            self.holdings[ticker] = 0.0

        for date in pd.date_range(self.start_date, self.end_date)[1:]:
            self.holdings.loc[date] = self.holdings.loc[date - pd.Timedelta(days=1)]

            if date in self.trades.index:
                print(f"Trades on {date}")
                print(f"{self.trades.loc[date]}")

                for index, row in self.trades.loc[date].iterrows():
                    ticker = row['Ticker']
                    amount = row['Amount']
                    try:
                        currency = yf.Ticker(ticker).info['currency']
                    except:
                        currency = 'CAD'
                    self.holdings.at[date, ticker] = self.holdings.loc[date, ticker] + amount
                    self.cash -= amount * row['Price'] * self.exchange_rates.loc[date, currency]
            else:
                print(f"No trades on {date}")

    def load_exchange_rate_table(self):
        self.exchange_rate_table = pd.DataFrame(index=pd.date_range(self.start_date, self.end_date))

        for ticker in self.tickers:
            try:
                currency = yf.Ticker(ticker).info['currency']
            except:
                currency = 'CAD'
            print(f"Currency for {ticker}: {currency}")
            self.exchange_rate_table[ticker] = self.exchange_rates[currency] 

        pd.DataFrame(self.exchange_rate_table).to_csv(os.path.join(output_folder, exchange_rate_table_file), index_label='Date')

    def calculate_market_values(self):
        holdings_data = self.holdings[self.tickers]
        price_data = self.prices[self.tickers]
        exchange_rate_table_data = self.exchange_rate_table[self.tickers]

        self.market_values = price_data * holdings_data * exchange_rate_table_data

        value = self.market_values.loc['2025-01-16'].sum()

        print(f"Market Value: {value}, Cash: {self.cash}")
        print(f"Total Value: {value + self.cash}")

        pd.DataFrame(self.market_values).to_csv(os.path.join(output_folder, market_values_file), index_label='Date')

    def calculate_dividend_values(self):
        holdings_data = self.holdings[self.tickers]
        dividend_data = self.dividends[self.tickers]
        exchange_rate_table_data = self.exchange_rate_table[self.tickers]

        self.dividend_values = dividend_data * holdings_data * exchange_rate_table_data

        value = self.dividend_values.sum().sum()

        print(f"Dividend Value: {value}")

        pd.DataFrame(self.dividend_values).to_csv(os.path.join(output_folder, dividend_values_file), index_label='Date')

    def save_price_data(self):
        pd.DataFrame(self.prices).to_csv(os.path.join(output_folder, prices_file), index_label='Date')

    def save_dividend_data(self):
        pd.DataFrame(self.dividends).to_csv(os.path.join(output_folder, dividends_file), index_label='Date')

    def save_holdings_data(self):
        pd.DataFrame(self.holdings).to_csv(os.path.join(output_folder, holdings_file), index_label='Date')

if __name__ == '__main__':
    portfolio = Portfolio(start_date, end_date, starting_cash)

    portfolio.load_exchange_rates()

    portfolio.load_trades_data()

    portfolio.load_exchange_rate_table()

    print(f"Starting Cash: {portfolio.cash}")

    portfolio.load_prices_data()
    portfolio.load_dividends_data()
    portfolio.load_holdings_data()

    print(portfolio.prices.head())
    print(portfolio.dividends.head())
    print(portfolio.holdings.head())

    portfolio.save_price_data()
    portfolio.save_dividend_data()
    portfolio.save_holdings_data()

    print(f"Final Cash: {portfolio.cash}")

    portfolio.calculate_market_values()
    portfolio.calculate_dividend_values()
