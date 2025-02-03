import pandas as pd
import yfinance as yf

starting_cash = 101644.99
start_date = '2022-05-01'
end_date = '2025-01-01'

dividends_file = 'dividends.csv'
holdings_file = 'holdings.csv'
prices_file = 'prices.csv'
trades_file = 'trades.csv'

class Portfolio:
    def __init__(self, start_date, end_date, starting_cash):
        self.start_date = start_date
        self.end_date = end_date
        self.cash = starting_cash
        self.dividends = None
        self.holdings = None
        self.prices = None
        self.tickers = None
        
    def load_trades(self):
        self.trades = pd.read_csv(trades_file)
        self.trades['Date'] = pd.to_datetime(self.trades['Date'])
        self.trades.set_index('Date', inplace=True)
        self.tickers = sorted(self.trades['Ticker'].unique())

    # def process_days(self):
    #     for date in pd.date_range(self.start_date, self.end_date):
    #         self.process_day(date)

    # def process_day(self, date):
    #     self.holdings[date] = self.holdings[date - pd.Timedelta(days=1)].copy()

    #     if date in self.trades.index:
    #         print(f"Trades on {date}")
    #         print(f"{self.trades.loc[date]}")

    #         for index, row in self.trades.loc[date].iterrows():
    #             ticker = row['Ticker']
    #             amount = row['Amount']
    #             price = row['Price']
    #             self.holdings[index][ticker] = self.holdings[index].get(ticker, 0) + amount
    #             self.cash -= amount * price
    #     else:
    #         print(f"No trades on {date}")

    # def save_holdings(self):
    #     pd.DataFrame(self.holdings).T.to_csv(holdings_file, index_label='Date')

    def load_price_data(self):
        self.prices = pd.DataFrame(index=pd.date_range(self.start_date, self.end_date))

        for ticker in self.tickers:
            prices = yf.Ticker(ticker).history(start=self.start_date, end=self.end_date)['Close']
            prices.index = pd.to_datetime(prices.index).tz_localize(None)
            self.prices[ticker] = self.prices.index.map(lambda x: prices.get(x, 0.0))

        # One line solution (will skip weekends and holidays)
        # self.prices = yf.download(self.tickers, start=self.start_date, end=self.end_date)['Close']

    def load_dividend_data(self):
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
                    self.holdings.at[date, ticker] = self.holdings.loc[date, ticker] + amount
                    self.cash -= amount * row['Price']
            else:
                print(f"No trades on {date}")

    def save_holdings_data(self):
        pd.DataFrame(self.holdings).to_csv(holdings_file, index_label='Date')

    def calculate_market_value(self):
        holdings_data = self.holdings[self.tickers]
        price_data = self.prices[self.tickers]

        self.market_value = price_data * holdings_data

        value = self.market_value.loc['2024-12-31'].sum()

        print(f"Market Value: {value}, Cash: {self.cash}")
        print(f"Total Value: {value + self.cash}")

        pd.DataFrame(self.market_value).to_csv('market_value.csv', index_label='Date')

    def calculate_dividend_value(self):
        holdings_data = self.holdings[self.tickers]
        dividend_data = self.dividends[self.tickers]

        self.dividend_value = dividend_data * holdings_data

        value = self.dividend_value.sum().sum()

        print(f"Dividend Value: {value}")

        pd.DataFrame(self.dividend_value).to_csv('dividend_value.csv', index_label='Date')

    def save_price_data(self):
        pd.DataFrame(self.prices).to_csv(prices_file, index_label='Date')

    def save_dividend_data(self):
        pd.DataFrame(self.dividends).to_csv(dividends_file, index_label='Date')

if __name__ == '__main__':
    portfolio = Portfolio(start_date, end_date, starting_cash)
    portfolio.load_trades()

    # portfolio.process_days()
    # portfolio.save_holdings()

    print(f"Starting Cash: {portfolio.cash}")

    portfolio.load_dividend_data()
    portfolio.load_holdings_data()
    portfolio.load_price_data()

    print(portfolio.prices.head())
    print(portfolio.dividends.head())
    print(portfolio.holdings.head())

    portfolio.save_dividend_data()
    portfolio.save_holdings_data()
    portfolio.save_price_data()

    print(f"Final Cash: {portfolio.cash}")

    portfolio.calculate_market_value()
    portfolio.calculate_dividend_value()
    