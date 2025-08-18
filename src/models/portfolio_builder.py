import os
import shutil
import pandas as pd
import yfinance as yf
from datetime import timedelta

from .portfolio_base import PortfolioBase


class PortfolioCsvBuilder:
    def __init__(self, portfolio: PortfolioBase):
        self.portfolio = portfolio

    def _write(self, df: pd.DataFrame, filename: str):
        df.to_csv(os.path.join(self.portfolio.output_folder, filename), index_label='Date')

    def build_all(self):
        # Cleanup entire output folder to ensure fresh build (drop schema equivalent)
        try:
            for entry in os.listdir(self.portfolio.output_folder):
                path = os.path.join(self.portfolio.output_folder, entry)
                if os.path.isfile(path):
                    try:
                        os.remove(path)
                    except Exception as e:
                        print(f"Error removing file {entry}: {e}")
                elif os.path.isdir(path):
                    # Remove any subdirectories like .cache
                    try:
                        shutil.rmtree(path)
                    except Exception as e:
                        print(f"Error removing directory {entry}: {e}")
        except FileNotFoundError:
            # Ensure the folder exists
            os.makedirs(self.portfolio.output_folder, exist_ok=True)
        
        sp500 = yf.Ticker('^GSPC').history(start=self.portfolio.start_date, end=self.portfolio.end_date)
        tsx = yf.Ticker('^GSPTSE').history(start=self.portfolio.start_date, end=self.portfolio.end_date)
        sp500.index = pd.to_datetime(sp500.index).tz_localize(None)
        tsx.index = pd.to_datetime(tsx.index).tz_localize(None)
        self.portfolio.valid_dates = sp500.index.union(tsx.index)

        ex = self.portfolio.build_exchange_rates(); self._write(ex, 'exchange_rates.csv')
        self.portfolio.load_trades()
        pr = self.portfolio.build_prices(); self._write(pr, 'prices.csv')
        hd = self.portfolio.build_holdings(); self._write(hd, 'holdings.csv')
        mv = self.portfolio.build_cad_market_values(); self._write(mv, 'cad_market_values.csv')
        dps = self.portfolio.build_dividend_per_share(); self._write(dps, 'dividend_per_share.csv')
        di = self.portfolio.build_dividend_income(); self._write(di, 'dividend_income.csv')
        cs = self.portfolio.build_cash(); self._write(cs, 'cash.csv')
        pt = self.portfolio.build_portfolio_total(); self._write(pt, 'portfolio_total.csv')


