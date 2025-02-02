import pandas as pd
import yfinance as yf
import Trade

class Portfolio:
    def __init__(self):
        self.current_holdings = {}  # Ticker -> Shares
        self.historical_transactions = []  # List of Trade objects

    def add_transaction(self, trade):
        # Update current holdings
        if trade.ticker in self.current_holdings:
            self.current_holdings[trade.ticker] += trade.quantity
        else:
            self.current_holdings[trade.ticker] = trade.quantity

        # Add trade to historical transactions
        self.historical_transactions.append(trade)

    def get_portfolio_value(self, date):
        value = 0
        for ticker, shares in self.current_holdings.items():
            if shares > 0:  # Only calculate value for tickers with positive holdings
                # Fetch historical price for the ticker on the given date
                historical_data = yf.download(ticker, start=date, end=date)
                if not historical_data.empty:
                    price = historical_data['Close'].iloc[0]
                    value += shares * price
        return value