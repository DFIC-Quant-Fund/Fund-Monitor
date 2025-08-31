"""
Fixed income analysis module.

This module provides analysis tools for fixed income securities.
It handles:
- Market value calculations
- Currency conversion
- Market share calculations
- USD-specific analysis

The module requires access to market values and exchange rate data.
"""

import pandas as pd
import yfinance as yf


class FixedIncomeAnalyzer:
    def __init__(self):
        self.market_values = pd.read_csv("data/core/output/cad_market_values.csv")
        self.exchange_rates = pd.read_csv("data/core/output/exchange_rates.csv")

    def get_fixed_income_info(self, tickers: list):
        usd_tickers = []

        # Convert USD values to CAD
        for t in tickers:
            try:
                currency = yf.Ticker(t).info['currency']
            except (KeyError, AttributeError, Exception):
                currency = 'CAD'

            if currency == 'USD':
                self.market_values[t] = self.market_values[t] * self.exchange_rates['USD'].iloc[-1]
                usd_tickers.append(t)

        # Calculate market values and shares
        current_mkt_vals = {ticker: self.market_values[ticker].iloc[-1] for ticker in tickers}
        total_mkt_vals = sum(current_mkt_vals.values())
        fi_mkt_shares = {ticker: current_mkt_vals[ticker] / total_mkt_vals for ticker in tickers}

        # Calculate USD-specific metrics
        usd_total_mkt_val = sum([current_mkt_vals[ticker] for ticker in usd_tickers])
        usd_fi_mkt_shares = {ticker: current_mkt_vals[ticker] / usd_total_mkt_val for ticker in usd_tickers}

        # Create result DataFrame
        data = {
            'Ticker': tickers,
            'Market Value': [current_mkt_vals[ticker] for ticker in tickers],
            'Total Market Share': [fi_mkt_shares[ticker] for ticker in tickers],
            'USD Market Share': [usd_fi_mkt_shares[ticker] if ticker in usd_tickers else 0 for ticker in tickers]
        }

        result_df = pd.DataFrame(data)
        result_df.set_index('Ticker', inplace=True)

        return result_df 