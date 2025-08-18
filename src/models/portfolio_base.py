import os
from typing import List
import pandas as pd
import yfinance as yf


class PortfolioBase:
    def __init__(self, start_date: str, end_date: str, starting_cash: float, folder_prefix: str):
        self.start_date = start_date
        self.end_date = end_date
        self.starting_cash = starting_cash
        self.folder_prefix = folder_prefix

        self.input_folder = os.path.join("data", folder_prefix, "input")
        self.output_folder = os.path.join("data", folder_prefix, "output")
        os.makedirs(self.output_folder, exist_ok=True)

        self.valid_dates: pd.DatetimeIndex | None = None

        # Common state used by default implementations
        self.trades: pd.DataFrame | None = None
        self.tickers: List[str] = []
        self.exchange_rates: pd.DataFrame | None = None
        self.prices: pd.DataFrame | None = None
        self.holdings: pd.DataFrame | None = None
        self.dividend_per_share: pd.DataFrame | None = None
        self.dividend_income: pd.DataFrame | None = None
        self.cash: pd.DataFrame | None = None
        self.cad_market_values: pd.DataFrame | None = None
        self.portfolio_total: pd.DataFrame | None = None

    # Defaults that subclasses can override as needed
    def get_tickers(self) -> List[str]:
        return self.tickers

    def build_exchange_rates(self) -> pd.DataFrame:
        self.exchange_rates = pd.DataFrame(index=self.valid_dates)
        self.exchange_rates["CAD"] = 1.0
        self.exchange_rates["USD"] = yf.Ticker('CAD=X').history(start=self.start_date, end=self.end_date)['Close']
        self.exchange_rates.index = pd.to_datetime(self.exchange_rates.index)
        self.exchange_rates = self.exchange_rates.ffill()
        return self.exchange_rates

    def load_trades(self) -> pd.DataFrame | None:
        trades_path = os.path.join(self.input_folder, 'trades.csv')
        if os.path.exists(trades_path):
            self.trades = pd.read_csv(trades_path)
            self.trades['Date'] = pd.to_datetime(self.trades['Date'])
            self.trades.set_index('Date', inplace=True)
            self.tickers = sorted(self.trades['Ticker'].unique())
            return self.trades
        # No trades file: keep existing tickers (subclasses may predefine them)
        self.trades = None
        return None

    def build_prices(self) -> pd.DataFrame:
        self.prices = pd.DataFrame(index=self.valid_dates)
        for ticker in self.tickers:
            prices = yf.Ticker(ticker).history(start=self.start_date, end=self.end_date)['Close']
            prices.index = pd.to_datetime(prices.index).tz_localize(None)
            self.prices[ticker] = self.prices.index.map(lambda x: prices.get(x, None))
        self.prices = self.prices.ffill()
        return self.prices

    def build_holdings(self) -> pd.DataFrame:
        self.holdings = pd.DataFrame(index=self.valid_dates)
        for ticker in self.tickers:
            self.holdings[ticker] = 0.0
        if self.trades is None:
            return self.holdings
        for i, date in enumerate(self.valid_dates):
            if i != 0:
                self.holdings.loc[date] = self.holdings.loc[self.valid_dates[i - 1]]
            if date in self.trades.index:
                for _, row in self.trades.loc[date].iterrows():
                    self.holdings.at[date, row['Ticker']] = self.holdings.loc[date, row['Ticker']] + row['Quantity']
        return self.holdings

    def build_cad_market_values(self) -> pd.DataFrame:
        holdings = self.holdings[self.tickers]
        prices = self.prices[self.tickers]
        market_values_cad = pd.DataFrame(index=self.valid_dates)
        for ticker in self.tickers:
            try:
                currency = yf.Ticker(ticker).info.get('currency', 'CAD')
            except Exception:
                currency = 'CAD'
            market_values_cad[ticker] = prices[ticker] * holdings[ticker] * self.exchange_rates[currency]
        self.cad_market_values = market_values_cad
        return self.cad_market_values

    def build_dividend_per_share(self) -> pd.DataFrame:
        self.dividend_per_share = pd.DataFrame(index=self.valid_dates)
        for ticker in self.tickers:
            divs = yf.Ticker(ticker).dividends.loc[self.start_date:self.end_date]
            divs.index = pd.to_datetime(divs.index).tz_localize(None)
            self.dividend_per_share[ticker] = self.dividend_per_share.index.map(lambda x: divs.get(x, 0.0))
        nonzero_div_per_share = self.dividend_per_share[(self.dividend_per_share != 0).any(axis=1)]
        return nonzero_div_per_share

    def build_dividend_income(self) -> pd.DataFrame:
        holdings = self.holdings[self.tickers]
        dividend = self.dividend_per_share[self.tickers]
        dividend_income = pd.DataFrame(index=self.valid_dates)
        for ticker in self.tickers:
            dividend_income[ticker] = dividend[ticker] * holdings[ticker]
        self.dividend_income = dividend_income
        nonzero_div_income = self.dividend_income[(self.dividend_income != 0).any(axis=1)]
        return nonzero_div_income

    def build_cash(self) -> pd.DataFrame:
        cash = pd.DataFrame(index=self.valid_dates)
        cash['CAD_Cash'] = 0.0
        cash['USD_Cash'] = 0.0
        cash['Total_CAD'] = 0.0
        cash.at[self.valid_dates[0], 'CAD_Cash'] = self.starting_cash
        cash.at[self.valid_dates[0], 'Total_CAD'] = self.starting_cash
        current_cad_cash = self.starting_cash
        current_usd_cash = 0.0
        if self.trades is not None:
            for i, date in enumerate(self.valid_dates):
                if i != 0:
                    cash.loc[date] = cash.loc[self.valid_dates[i - 1]]
                    current_cad_cash = cash.loc[date, 'CAD_Cash']
                    current_usd_cash = cash.loc[date, 'USD_Cash']
                if date in self.trades.index:
                    for _, row in self.trades.loc[date].iterrows():
                        quantity = row['Quantity']
                        currency = row['Currency']
                        price = row['Price']
                        trade_value = abs(quantity * price)
                        if quantity > 0:
                            if currency == 'CAD':
                                current_cad_cash -= trade_value
                            elif currency == 'USD':
                                current_usd_cash -= trade_value
                        elif quantity < 0:
                            if currency == 'CAD':
                                current_cad_cash += trade_value
                            elif currency == 'USD':
                                current_usd_cash += trade_value
                        cash.at[date, 'CAD_Cash'] = current_cad_cash
                        cash.at[date, 'USD_Cash'] = current_usd_cash
                        total_cad = current_cad_cash + (current_usd_cash * self.exchange_rates.loc[date, 'USD'])
                        cash.at[date, 'Total_CAD'] = total_cad
        self.cash = cash
        return cash

    def build_portfolio_total(self) -> pd.DataFrame:
        portfolio_total = pd.DataFrame(index=self.valid_dates)
        total_market_value = self.cad_market_values.sum(axis=1)
        portfolio_total['Total_Market_Value'] = total_market_value
        portfolio_total['Total_Portfolio_Value'] = total_market_value + self.cash['Total_CAD']
        self.portfolio_total = portfolio_total
        return portfolio_total

