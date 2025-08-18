from typing import List
import pandas as pd
import yfinance as yf
from .portfolio_base import PortfolioBase


class BenchmarkPortfolio(PortfolioBase):
    def __init__(self, start_date: str, end_date: str, starting_cash: float, folder_prefix: str = "benchmark"):
        super().__init__(start_date, end_date, starting_cash, folder_prefix)
        self.weights = {
            'XIU.TO': 0.30,
            'SPY': 0.30,
            'AGG': 0.20,
            'XBB.TO': 0.20,
        }
        self.tickers: List[str] = list(self.weights.keys())
        # Other state inherited and initialized by base

    def get_tickers(self) -> List[str]:
        return self.tickers

    def load_trades(self) -> pd.DataFrame | None:
        # Benchmark has no trades; ensure tickers remain as predefined
        self.trades = None
        return None

    # Use base build_prices

    def build_holdings(self) -> pd.DataFrame:
        # Derive shares based on starting cash and initial prices
        initial_prices = self.prices.iloc[0]
        usd_rate = self.exchange_rates.iloc[0]['USD']
        shares = {}
        for ticker, weight in self.weights.items():
            if ticker in ['SPY', 'AGG']:
                # USD-denominated, convert to CAD-equivalent when sizing
                shares[ticker] = weight * self.starting_cash / (initial_prices[ticker] * usd_rate)
            else:
                shares[ticker] = weight * self.starting_cash / initial_prices[ticker]
        holdings = pd.DataFrame(index=self.valid_dates)
        for ticker in self.tickers:
            holdings[ticker] = shares[ticker]
        self.holdings = holdings
        return holdings

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
        # Benchmark is fully invested; track dividends into cash
        cash = pd.DataFrame(index=self.valid_dates)
        cash['CAD_Cash'] = 0.0
        cash['USD_Cash'] = 0.0
        cash['Total_CAD'] = 0.0
        current_cad_cash = 0.0
        current_usd_cash = 0.0
        for i, date in enumerate(self.valid_dates):
            if i != 0:
                cash.loc[date] = cash.loc[self.valid_dates[i - 1]]
                current_cad_cash = cash.loc[date, 'CAD_Cash']
                current_usd_cash = cash.loc[date, 'USD_Cash']
            if self.dividend_income is not None and date in self.dividend_income.index:
                for ticker in self.tickers:
                    amount = self.dividend_income.at[date, ticker] if ticker in self.dividend_income.columns else 0.0
                    if pd.isna(amount) or amount == 0.0:
                        continue
                    try:
                        currency = yf.Ticker(ticker).info.get('currency', 'CAD')
                    except Exception:
                        currency = 'CAD'
                    if currency == 'CAD':
                        current_cad_cash += amount
                    elif currency == 'USD':
                        current_usd_cash += amount
                cash.at[date, 'CAD_Cash'] = current_cad_cash
                cash.at[date, 'USD_Cash'] = current_usd_cash
                total_cad = current_cad_cash + (current_usd_cash * self.exchange_rates.loc[date, 'USD'])
                cash.at[date, 'Total_CAD'] = total_cad
        self.cash = cash
        return cash

    def build_portfolio_total(self) -> pd.DataFrame:
        portfolio_total = pd.DataFrame(index=self.valid_dates)
        portfolio_total['Total_Market_Value'] = self.cad_market_values.sum(axis=1)
        portfolio_total['Total_Portfolio_Value'] = portfolio_total['Total_Market_Value'] + self.cash['Total_CAD']
        self.portfolio_total = portfolio_total
        return portfolio_total


