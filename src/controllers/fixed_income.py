"""
Fixed income analysis module.

This module provides analysis tools for fixed income securities.
It handles:
- Market value calculations
- Currency conversion
- Market share calculations
- USD-specific analysis

The module accepts injected market values and exchange rates DataFrames
instead of hard-coding CSV reads, allowing it to work within the controller pipeline.
"""

import pandas as pd
import yfinance as yf
import logging

logger = logging.getLogger(__name__)


class FixedIncomeAnalyzer:
    def __init__(self, market_values: pd.DataFrame = None, exchange_rates: pd.DataFrame = None):
        """
        Initialize FixedIncomeAnalyzer with injected data.
        
        Args:
            market_values: DataFrame with tickers as columns, dates as index (already in CAD)
            exchange_rates: DataFrame with 'USD' column for USD→CAD conversion rates
        """
        self.market_values = market_values.copy() if market_values is not None and not market_values.empty else pd.DataFrame()
        self.exchange_rates = exchange_rates.copy() if exchange_rates is not None and not exchange_rates.empty else pd.DataFrame()

    def get_fixed_income_info(self, tickers: list):
        """
        Analyze fixed income securities.
        
        Args:
            tickers: List of fixed income ticker symbols
            
        Returns:
            DataFrame with ticker, market value, and market share info
        """
        if not tickers:
            logger.warning("No tickers provided for fixed income analysis")
            return pd.DataFrame()
            
        if self.market_values.empty:
            logger.warning("No market values data available for fixed income analysis")
            return pd.DataFrame()

        usd_tickers = []

        # Detect currency for each ticker and convert USD to CAD if needed
        for t in tickers:
            try:
                currency = yf.Ticker(t).info.get('currency', 'CAD')
            except Exception as e:
                logger.warning(f"Could not detect currency for {t}: {e}. Defaulting to CAD.")
                currency = 'CAD'

            # If USD ticker, note it
            if currency == 'USD':
                usd_tickers.append(t)

        # Get latest market values for each ticker
        current_mkt_vals = {}
        for ticker in tickers:
            if ticker in self.market_values.columns:
                try:
                    val = float(self.market_values[ticker].dropna().iloc[-1])
                    current_mkt_vals[ticker] = val if val > 0 else 0.0
                except (ValueError, IndexError):
                    logger.warning(f"Could not extract market value for {ticker}")
                    current_mkt_vals[ticker] = 0.0
            else:
                logger.warning(f"Ticker {ticker} not found in market values DataFrame")
                current_mkt_vals[ticker] = 0.0

        # Calculate totals
        total_mkt_vals = sum(current_mkt_vals.values())
        usd_total_mkt_val = sum([current_mkt_vals[t] for t in usd_tickers if t in current_mkt_vals])

        # Calculate market shares (avoid division by zero)
        fi_mkt_shares = {
            ticker: (current_mkt_vals[ticker] / total_mkt_vals * 100 if total_mkt_vals > 0 else 0.0)
            for ticker in tickers
        }
        
        usd_fi_mkt_shares = {
            ticker: (current_mkt_vals[ticker] / usd_total_mkt_val * 100 if usd_total_mkt_val > 0 else 0.0)
            for ticker in usd_tickers
        }

        # Create result DataFrame
        data = {
            'Ticker': tickers,
            'Market Value (CAD)': [current_mkt_vals[ticker] for ticker in tickers],
            'Total FI Share %': [fi_mkt_shares[ticker] for ticker in tickers],
            'USD FI Share %': [usd_fi_mkt_shares.get(ticker, 0.0) for ticker in tickers],
            'Currency': ['USD' if t in usd_tickers else 'CAD' for t in tickers]
        }

        result_df = pd.DataFrame(data)
        result_df.set_index('Ticker', inplace=True)

        logger.info(f"Fixed income analysis complete: {len(tickers)} tickers, total market value: ${total_mkt_vals:,.2f}")
        return result_df 