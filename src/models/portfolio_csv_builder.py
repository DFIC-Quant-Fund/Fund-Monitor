import os
import sys
import pandas as pd
import yfinance as yf
from datetime import timedelta
import math

# Add project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import logging - works both as module and standalone script
try:
    from src.config.logging_config import get_logger
except ImportError:
    # Fallback for standalone execution
    from config.logging_config import get_logger

# Set up logger for this module
logger = get_logger(__name__)


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
# end_date = '2025-05-30'

# file names as variables 
trades_file = 'trades.csv'
prices_file = 'prices.csv'
holdings_file = 'daily_holdings.csv'
holdings_summary_file = 'holdings.csv'
cash_file = 'cash.csv'
portfolio_total_file = 'portfolio_total.csv'

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
        self.conversions = None
        self.prices = None
        self.holdings = None
        self.cash = None

        self.market_values = None
        self.exchange_rates = None

        self.dividend_per_share = None
        self.dividend_income = None

        # Currency-classified data structures (populated by private helper)
        self.cad_tickers = []
        self.usd_tickers = []
        self.ticker_currency = {}
        self.holdings_cad = None
        self.holdings_usd = None

        self.total_cad_dividends = 0.0
        self.total_usd_dividends = 0.0

        # Clean up existing CSV files before building new ones
        self.cleanup_existing_csv_files()
        
        # call valid dates function to get dates that both TSX and American exchanges open 
        self.get_valid_dates()
        # all tickers invested in from trades csv 
        self.load_trades()
        self.load_conversions()

    def cleanup_existing_csv_files(self):
        """Clean up existing CSV files before building new ones to ensure fresh data"""
        csv_files = [
            exchange_rates_file,
            prices_file,
            holdings_file,
            holdings_summary_file,
            cash_file,
            market_values_file,
            dividend_per_share_file,
            dividend_income_file,
            portfolio_total_file
        ]
        
        for csv_file in csv_files:
            file_path = os.path.join(self.output_folder, csv_file)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Removed existing file: {csv_file}")
                except Exception as e:
                    logger.warning(f"Could not remove {csv_file}: {e}")

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

        # Build and cache ticker -> currency map and precompute CAD/USD lists
        self.ticker_currency = {}
        cad_tickers = []
        usd_tickers = []
        for ticker in self.tickers:
            currency = yf.Ticker(ticker).info.get('currency', 'CAD')

            self.ticker_currency[ticker] = currency
            if currency == 'USD':
                usd_tickers.append(ticker)
            else:
                cad_tickers.append(ticker)
        self.cad_tickers = cad_tickers
        self.usd_tickers = usd_tickers

    def load_conversions(self):
        conversions_path = os.path.join(self.input_folder, 'conversions.csv')
        if os.path.exists(conversions_path):
            df = pd.read_csv(conversions_path)
            if not df.empty:
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                # Normalize column names exactly as expected
                expected_cols = ['Currency_From', 'Currency_To', 'Amount', 'Rate']
                missing = [c for c in expected_cols if c not in df.columns]
                if missing:
                    raise ValueError(f"Missing columns in conversions.csv: {missing}")
                self.conversions = df
                logger.info(f"Loaded conversions.csv with {len(df)} rows")
            else:
                self.conversions = pd.DataFrame(columns=['Currency_From', 'Currency_To', 'Amount', 'Rate'])
        else:
            # No conversions provided
            self.conversions = pd.DataFrame(columns=['Currency_From', 'Currency_To', 'Amount', 'Rate'])

    def create_table_prices(self):
        self.prices = pd.DataFrame(index=self.valid_dates)

        for ticker in self.tickers:
            # This is getting close price adjusted for stock splits but NOT dividends
            prices = yf.Ticker(ticker).history(start=self.start_date, end=self.end_date, actions=True, auto_adjust=False)['Close']

            if prices.empty:
                logger.error(f"No data found for {ticker}. Trying ticker variants.")
                ticker_variants = [f"{ticker}.TO"]

                for variant in ticker_variants:
                    prices = yf.Ticker(variant).history(start=self.start_date, end=self.end_date, actions=True, auto_adjust=False)['Close']

                    if not prices.empty:
                        print(f"Found valid variant: {variant}")
                        break

                if prices.empty:
                    raise Exception(
                        f"Ticker '{ticker}' could not be found (including variants: {', '.join(ticker_variants)}). "
                        "Please update core.yaml or double-check ticker spelling."
                    )

            prices.index = pd.to_datetime(prices.index).tz_localize(None)
            self.prices[ticker] = self.prices.index.map(lambda x: prices.get(x, None))

        # Forward fill missing prices (i.e. CAD stock on holiday but US market open and vice versa)
        self.prices = self.prices.ffill()

        pd.DataFrame(self.prices).to_csv(os.path.join(self.output_folder, prices_file), index_label='Date')


    def _fetch_split_events(self):
        """Fetch stock split events for tickers within the date range.

        Returns a nested dict: {ticker: {date: factor}} where factor is the split
        ratio (e.g., 2.0 for 2-for-1, 0.5 for 1-for-2). Dates are timezone-naive
        to match self.valid_dates.
        """
        split_events = {}
        for ticker in self.tickers:
            try:
                splits_series = yf.Ticker(ticker).splits
                if splits_series is None or len(splits_series) == 0:
                    split_events[ticker] = {}
                    continue
                splits_series.index = pd.to_datetime(splits_series.index).tz_localize(None)
                splits_series = splits_series.loc[self.start_date:self.end_date]
                splits_series = splits_series[splits_series != 0]
                split_events[ticker] = {idx: float(val) for idx, val in splits_series.items()}
            except Exception as e:
                logger.warning(f"Could not fetch splits for {ticker}: {e}")
                split_events[ticker] = {}
        return split_events

    def create_table_daily_holdings(self):
        # function: amount of stocks we are holding on a certain date 

        self.holdings = pd.DataFrame(index=self.valid_dates)
        for ticker in self.tickers: 
            self.holdings[ticker] = 0.0

        # Pre-fetch split events once for all tickers
        split_events = self._fetch_split_events()

        for i, date in enumerate(self.valid_dates):
            if i != 0:
                self.holdings.loc[date] = self.holdings.loc[self.valid_dates[i - 1]]

            # Apply stock splits before processing any trades of the day
            for ticker in self.tickers:
                factor = split_events.get(ticker, {}).get(date, None)
                if factor is not None:
                    shares_before = self.holdings.loc[date, ticker]
                    if pd.notna(shares_before) and shares_before != 0.0:
                        shares_after = shares_before * factor
                        self.holdings.at[date, ticker] = shares_after
                        logger.info(
                            f"Applied stock split for {ticker} on {date.strftime('%Y-%m-%d')} "
                            f"factor {factor:.6g}: {shares_before} -> {shares_after}"
                        )

            if date in self.trades.index:
                logger.debug(f"Trades on {date}")
                logger.debug(f"{self.trades.loc[date]}")

                rows_for_date = self.trades.loc[date]

                # Ensure rows_for_date is a DataFrame
                # (if there is only one row, it will be a Series)
                if isinstance(rows_for_date, pd.Series):
                    rows_for_date = rows_for_date.to_frame().T
                for _, row in rows_for_date.iterrows():
                    quantity = row['Quantity']
                    ticker = row['Ticker']
                    self.holdings.at[date, ticker] = self.holdings.loc[date, ticker] + quantity

        pd.DataFrame(self.holdings).to_csv(os.path.join(self.output_folder, holdings_file), index_label='Date')

    def create_table_cash(self): 
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
            # forward fill cash balances
            if i != 0:
                self.cash.loc[date] = self.cash.loc[self.valid_dates[i - 1]]
                current_cad_cash = self.cash.loc[date, 'CAD_Cash']
                current_usd_cash = self.cash.loc[date, 'USD_Cash']

            # Process trades for this date
            if date in self.trades.index:
                logger.info(f"--- Processing trades on {date.strftime('%Y-%m-%d')} ---")
                logger.debug(f"Starting balances - CAD: ${current_cad_cash:.2f}, USD: ${current_usd_cash:.2f}")
                
                rows_for_date = self.trades.loc[date]
                if isinstance(rows_for_date, pd.Series):
                    rows_for_date = rows_for_date.to_frame().T
                for _, row in rows_for_date.iterrows():
                    quantity = row['Quantity']
                    currency = row['Currency']
                    price = row['Price']
                    ticker = row['Ticker']
                    trade_value = abs(quantity * price)
                    er = self.exchange_rates.loc[date, 'USD']

                    logger.debug(f"Trade: {ticker} - {quantity} shares @ ${price:.2f} {currency}")
                    logger.debug(f"Trade value: ${trade_value:.2f} {currency}")

                    # if quantity > 0: # Buy
                    #     # if currency == 'CAD':
                    #     #     current_cad_cash -= trade_value
                    #     # elif currency == 'USD':
                    #     #     if current_usd_cash < trade_value:
                    #     #         current_cad_cash -= trade_value * er
                    #     #     else:
                    #     #         current_usd_cash -= trade_value
                    self._handle_trade(quantity, trade_value, currency, current_cad_cash, current_usd_cash, date)
                    #     else:
                    #         raise ValueError(f"Unsupported currency: {currency}")
                    #     logger.debug("Buy: Decreased cash for purchase.")
                    # else:
                    #     # Sell: Add proceeds to correct cash balance
                    #     if currency == 'CAD':
                    #         current_cad_cash += trade_value
                    #         logger.debug(f"Sell: Increased CAD cash by ${trade_value:.2f}")
                    #     elif currency == 'USD':
                    #         current_usd_cash += trade_value
                    #         logger.debug(f"Sell: Increased USD cash by ${trade_value:.2f}")
                    #     else:
                    #         raise ValueError(f"Unsupported currency: {currency}")

                    # Update cash balances
                    self.cash.at[date, 'CAD_Cash'] = current_cad_cash
                    self.cash.at[date, 'USD_Cash'] = current_usd_cash
                    # Calculate total in CAD
                    total_cad = current_cad_cash + (current_usd_cash * er)
                    self.cash.at[date, 'Total_CAD'] = total_cad
                    # logger.debug(f"After trade - CAD: ${current_cad_cash:.2f}, USD: ${current_usd_cash:.2f}, Total CAD: ${total_cad:.2f}")

        # Process all dividends
        cad_dividends, usd_dividends = self._get_dividend_income()
        logger.debug(f"Total CAD dividends: ${cad_dividends:.2f}")
        logger.debug(f"Total USD dividends: ${usd_dividends:.2f}")
       
        # Process explicit currency conversions for this date
        current_cad_cash, current_usd_cash, total_cash_cad = self._apply_explicit_currency_conversions(
            date, current_cad_cash, current_usd_cash
        )
        logger.debug(f"After conversions - CAD: ${current_cad_cash:.2f}, USD: ${current_usd_cash:.2f}, Total CAD: ${total_cash_cad:.2f}")
        
        pd.DataFrame(self.cash).to_csv(os.path.join(self.output_folder, cash_file), index_label='Date')

        sys.exit(0)

    def _handle_trade(self, quantity, trade_value, currency, current_cad_cash, current_usd_cash, date):
        """
        Helper function to handle trades.
        Assumption: we always have enough total cash to make a trade.
        """
        er = self.exchange_rates.loc[date, 'USD']
        if quantity > 0: # Buy
            if currency == 'CAD':
                if current_cad_cash < trade_value:
                    # need to convert USD to CAD
                    cad_needed = abs(trade_value - current_cad_cash)
                    cad_to_convert = cad_needed * er
                    current_cad_cash -= cad_to_convert
                    current_usd_cash -= cad_needed
                else:
                    current_cad_cash -= trade_value
            elif currency == 'USD':
                if current_usd_cash < trade_value:
                    # need to convert CAD to USD
                    cad_to_convert = trade_value - current_usd_cash

                else:
                    current_usd_cash -= trade_value
        else: # Sell
            self._handle_sell(quantity, trade_value, currency, current_cad_cash, current_usd_cash, date)

    # def _convert_currency_for_trade(self, trade_value, trade_currency, current_cad_cash, current_usd_cash, date):
    #     """
    #     Helper function to handle currency conversion for trades.
        
    #     Args:
    #         trade_value: Amount of the trade
    #         trade_currency: Currency of the trade ('CAD' or 'USD')
    #         current_cad_cash: Current CAD cash balance
    #         current_usd_cash: Current USD cash balance
    #         date: Date of the trade for exchange rate lookup
            
    #     Returns:
    #         tuple: (new_cad_cash, new_usd_cash, conversion_details)
    #     """
    #     if trade_currency == 'CAD':
    #         # For CAD trades, use CAD cash first, convert USD if needed
    #         if current_cad_cash >= trade_value:
    #             # We have enough CAD cash
    #             logger.debug(f"CAD trade - using existing CAD cash (${current_cad_cash:.2f} available)")
    #             return current_cad_cash - trade_value, current_usd_cash, "used_cad_cash"
    #         else:
    #             # Need to convert some USD to CAD
    #             cad_needed = trade_value - current_cad_cash
    #             usd_to_convert = cad_needed / self.exchange_rates.loc[date, 'USD']
    #             exchange_rate = self.exchange_rates.loc[date, 'USD']
                
    #             logger.debug(f"CAD trade - need ${cad_needed:.2f} more CAD")
    #             logger.debug(f"Converting ${usd_to_convert:.2f} USD to CAD (rate: {exchange_rate:.4f})")
    #             logger.debug(f"Using all available CAD cash: ${current_cad_cash:.2f}")
                
    #             # Use all available CAD cash and convert USD
    #             new_cad_cash = 0
    #             new_usd_cash = current_usd_cash - usd_to_convert
    #             return new_cad_cash, new_usd_cash, "converted_usd_to_cad"
    #     elif trade_currency == 'USD':
    #         # For USD trades, use USD cash first, convert CAD if needed
    #         if current_usd_cash >= trade_value:
    #             # We have enough USD cash
    #             logger.debug(f"USD trade - using existing USD cash (${current_usd_cash:.2f} available)")
    #             return current_cad_cash, current_usd_cash - trade_value, "used_usd_cash"
    #         else:
    #             # Need to convert some CAD to USD
    #             usd_needed = trade_value - current_usd_cash
    #             cad_to_convert = usd_needed * self.exchange_rates.loc[date, 'USD']
    #             exchange_rate = self.exchange_rates.loc[date, 'USD']
                
    #             logger.debug(f"  USD trade - need ${usd_needed:.2f} more USD")
    #             logger.debug(f"  Converting ${cad_to_convert:.2f} CAD to USD (rate: {exchange_rate:.4f})")
    #             logger.debug(f"  Using all available USD cash: ${current_usd_cash:.2f}")
                
    #             # Use all available USD cash and convert CAD
    #             new_cad_cash = current_cad_cash - cad_to_convert
    #             new_usd_cash = 0
    #             return new_cad_cash, new_usd_cash, "converted_cad_to_usd"

    # def _apply_dividends_for_date(self, date, current_cad_cash, current_usd_cash):
    #     """
    #     Apply dividend cash flows for a given date to the running CAD/USD cash balances.
    #     Updates self.cash for the date after each dividend and returns updated balances.
    #     """

    #     er = self.exchange_rates.loc[date, 'USD']
    #     total_cash_cad = current_cad_cash + (current_usd_cash * er)
    #     if self.dividend_income is None or date not in self.dividend_income.index:
    #         return current_cad_cash, current_usd_cash, total_cash_cad

    #     logger.info(f"--- Processing dividends on {date.strftime('%Y-%m-%d')} ---")
    #     logger.debug(f"Starting balances - CAD: ${current_cad_cash:.2f}, USD: ${current_usd_cash:.2f}")
        
    #     for ticker in self.tickers:
    #         dividend_amount = self.dividend_income.at[date, ticker]
    #         if pd.isna(dividend_amount) or dividend_amount == 0.0:
    #             continue
    #         currency = self.ticker_currency[ticker]
    #         logger.debug(f"Dividend: {ticker} - ${dividend_amount:.2f} {currency}")
    #         # Add dividend to appropriate currency balance
    #         if currency == 'CAD':
    #             self.total_cad_dividends += dividend_amount
    #             logger.debug(f"Added ${dividend_amount:.2f} to CAD cash")
    #         elif currency == 'USD':
    #             self.total_usd_dividends += dividend_amount
    #             logger.debug(f"Added ${dividend_amount:.2f} to USD cash")
    #         else:
    #             raise ValueError(f"Unsupported currency: {currency}")

    #         # Update cash balances after each dividend
    #         current_cad_cash += self.total_cad_dividends
    #         current_usd_cash += self.total_usd_dividends

    #         total_cash_cad = current_cad_cash + (current_usd_cash * er)
    #         self.cash.at[date, 'CAD_Cash'] = current_cad_cash
    #         self.cash.at[date, 'USD_Cash'] = current_usd_cash
    #         self.cash.at[date, 'Total_CAD'] = total_cash_cad
    #         logger.debug(f"After dividend - CAD: ${current_cad_cash:.2f}, USD: ${current_usd_cash:.2f}, Total CAD: ${total_cash_cad:.2f}")

    #     return current_cad_cash, current_usd_cash, total_cash_cad

    def _get_dividend_income(self):
        """
        Get the total dividend income for all tickers
        """
        cad_dividends = 0.0
        usd_dividends = 0.0
        dividends = pd.read_csv('data/core/output/dividend_income.csv')
        dividends['Date'] = pd.to_datetime(dividends['Date'])
        dividends.set_index('Date', inplace=True)

        for _, row in dividends.iterrows():
            for ticker in dividends.columns:
                currency = self.ticker_currency[ticker]
                if currency == 'CAD':
                    cad_dividends += row[ticker]
                elif currency == 'USD':
                    usd_dividends += row[ticker]
        return cad_dividends, usd_dividends

    def _apply_explicit_currency_conversions(self, date, current_cad_cash, current_usd_cash):
        """
        Apply explicit currency conversions for a given date to the running CAD/USD cash balances.
        Updates self.cash for the date after each conversion and returns the updated balances.
        """
        er = self.exchange_rates.loc[date, 'USD']
        total_cash_cad = current_cad_cash + (current_usd_cash * er)
        if self.conversions is None or self.conversions.empty or date not in self.conversions.index:
            return current_cad_cash, current_usd_cash, total_cash_cad

        rows_for_date = self.conversions.loc[date]
        if isinstance(rows_for_date, pd.Series):
            rows_for_date = rows_for_date.to_frame().T

        for _, row in rows_for_date.iterrows():
            c_from = row['Currency_From']
            c_to = row['Currency_To']
            amount = float(row['Amount'])
            rate = float(row['Rate'])

            logger.info(f"Applying conversion on {date.strftime('%Y-%m-%d')}: {amount:.2f} {c_from} -> {c_to} at {rate:.6g}")

            if c_from == 'CAD' and c_to == 'USD':
                current_cad_cash -= amount
                current_usd_cash += amount * rate
            elif c_from == 'USD' and c_to == 'CAD':
                current_usd_cash -= amount
                current_cad_cash += amount * rate
            else:
                # Future currencies can be added here
                raise ValueError(f"Unsupported currency conversion: {c_from}->{c_to}")

            # Update balances after each conversion
            self.cash.at[date, 'CAD_Cash'] = current_cad_cash
            self.cash.at[date, 'USD_Cash'] = current_usd_cash
            total_cash_cad = current_cad_cash + (current_usd_cash * er)
            self.cash.at[date, 'Total_CAD'] = total_cash_cad

        return current_cad_cash, current_usd_cash, total_cash_cad

    def create_table_market_values(self):
        holdings = self.holdings[self.tickers]
        prices = self.prices[self.tickers]
        
        # Convert to CAD directly using exchange rates
        market_values = pd.DataFrame(index=self.valid_dates)
        for ticker in self.tickers:
            # try:
            #     currency = yf.Ticker(ticker).info['currency']
            # except (KeyError, AttributeError, Exception):
            #     currency = 'CAD'
            market_values[ticker] = prices[ticker] * holdings[ticker]

        self.market_values = market_values
        pd.DataFrame(self.market_values).to_csv(os.path.join(self.output_folder, market_values_file), index_label='Date')

    def create_table_holdings(self):
        """
        Build per-ticker holdings summary with:
        - shares
        - avg_purchase_price (weighted by split-adjusted share quantity across all buy trades)
        - market_value (current price * shares)
        - market_value_cad (converted to CAD using latest USD rate when needed)
        - book_value (avg_purchase_price * shares)
        - pnl (market_value - book_value)
        - pnl_percent (pnl / book_value)
        - current_price (latest price)
        - holding_weight (market_value_cad / latest Total_Holdings_CAD from portfolio_total.csv)
        """
        if self.holdings is None or self.holdings.empty:
            raise ValueError("Holdings are not computed. Call create_table_holdings() first.")
        if self.prices is None or self.prices.empty:
            raise ValueError("Prices are not computed. Call create_table_prices() first.")

        latest_date = self.holdings.index.max()
        shares_series = self.holdings.loc[latest_date].copy()
        # Keep only tickers we currently hold (> 0 shares)
        shares_series = shares_series[shares_series > 0]
        if shares_series.empty:
            # Nothing to write; create empty file with headers
            empty_df = pd.DataFrame(columns=['ticker','shares','avg_purchase_price','market_value','book_value','pnl','pnl_percent'])
            empty_df.to_csv(os.path.join(self.output_folder, holdings_summary_file), index=False)
            return

        # Weighted average purchase price from buy trades (Quantity > 0), adjusted for stock splits
        buys = self.trades[self.trades['Quantity'] > 0].copy() if self.trades is not None else pd.DataFrame(columns=['Ticker','Quantity','Price'])
        if not buys.empty:
            # Reset index to access trade dates
            buys = buys.reset_index()  # 'Date' column appears
            # Fetch split events once and compute cumulative factor from trade date to latest_date
            split_events = self._fetch_split_events()

            def cumulative_split_factor(ticker, buy_date, end_date):
                events = split_events.get(ticker, {})
                if not events:
                    return 1.0
                factor = 1.0
                for event_date, event_factor in events.items():
                    # Apply splits strictly after the buy date up to and including end_date
                    if buy_date < event_date <= end_date:
                        try:
                            factor *= float(event_factor)
                        except Exception:
                            continue
                return factor

            buys['adj_factor'] = buys.apply(lambda r: cumulative_split_factor(r['Ticker'], r['Date'], latest_date), axis=1)
            buys['weighted_cost'] = buys['Quantity'] * buys['Price']
            buys['adj_shares'] = buys['Quantity'] * buys['adj_factor']

            grouped = buys.groupby('Ticker').agg(weighted_cost=('weighted_cost', 'sum'),
                                                 adj_shares=('adj_shares', 'sum'))
            # Avoid division by zero
            grouped['avg_purchase_price'] = grouped.apply(lambda r: (r['weighted_cost'] / r['adj_shares']) if r['adj_shares'] not in (0, 0.0) else float('nan'), axis=1)
            avg_price_by_ticker = grouped[['avg_purchase_price']]
        else:
            avg_price_by_ticker = pd.DataFrame(columns=['avg_purchase_price'])

        # Current prices and market values at latest_date
        latest_prices = self.prices.loc[latest_date].copy()
        # Align price series to held tickers
        latest_prices = latest_prices.reindex(shares_series.index)

        result = pd.DataFrame({
            'ticker': shares_series.index,
            'shares': shares_series.values
        })

        result = result.merge(avg_price_by_ticker, left_on='ticker', right_index=True, how='left')
        result['avg_purchase_price'] = result['avg_purchase_price'].astype(float)

        # Current price, market value and book value
        result['current_price'] = result['ticker'].map(lambda t: float(latest_prices.get(t, float('nan'))))
        result['market_value'] = result['current_price'] * result['shares']
        result['book_value'] = result['avg_purchase_price'].fillna(0.0) * result['shares']

        # PnL metrics
        result['pnl'] = result['market_value'] - result['book_value']
        result['pnl_percent'] = result.apply(lambda r: (r['pnl'] / r['book_value']) if r['book_value'] not in (0, 0.0) else 0.0, axis=1)

        # Sort by market value descending
        result = result.sort_values('market_value', ascending=False)

        # Add currency per ticker using existing map (fallback to CAD)
        # Ensure ticker_currency is populated
        self._ensure_ticker_currency_map()
        result['currency'] = result['ticker'].map(lambda t: self.ticker_currency.get(t))

        # Compute CAD market value and precomputed weight using portfolio_total.csv latest Total_Holdings_CAD
        latest_usd_rate = float(self.exchange_rates['USD'].dropna().iloc[-1])
        result['market_value_cad'] = result.apply(
            lambda r: float(r['market_value']) * latest_usd_rate if r.get('currency') == 'USD' else float(r['market_value']),
            axis=1
        )
        # Load latest Total_Holdings_CAD from portfolio_total.csv
        total_path = os.path.join(self.output_folder, portfolio_total_file)

        if os.path.exists(total_path):
            totals_df = pd.read_csv(total_path)
            totals_df['Date'] = pd.to_datetime(totals_df['Date'])
            latest_row = totals_df.sort_values('Date').iloc[-1]
            denom_total_holdings_cad = float(latest_row['Total_Holdings_CAD'])

        result['holding_weight'] = result.apply(
            lambda r: (float(r['market_value_cad']) / denom_total_holdings_cad * 100.0) if denom_total_holdings_cad > 0 else 0.0,
            axis=1
        )

        # Add cumulative dividends to date per ticker (native currency of the ticker)
        if self.dividend_income is not None and not self.dividend_income.empty:
            # Ensure datetime index
            div_df = self.dividend_income.copy()
            div_df.index = pd.to_datetime(div_df.index)
            # Sum up to latest_date across all rows for each ticker
            div_upto = div_df.loc[div_df.index <= latest_date]
            dividends_cumulative = div_upto.sum(numeric_only=True)
            result['dividends_to_date'] = result['ticker'].map(lambda t: float(dividends_cumulative.get(t, 0.0)))
        else:
            result['dividends_to_date'] = 0.0

        # Persist
        result.to_csv(os.path.join(self.output_folder, holdings_summary_file), index=False)

    def _build_currency_holdings(self):
        """
        Build CAD- and USD-only holdings DataFrames using precomputed ticker lists.

        Relies on:
        - self.cad_tickers / self.usd_tickers (populated in load_trades)
        - self.holdings (constructed in create_table_holdings)

        Produces:
        - self.holdings_cad, self.holdings_usd
        """
        cad_tickers = self.cad_tickers or []
        usd_tickers = self.usd_tickers or []

        if self.holdings is not None and not self.holdings.empty:
            self.holdings_cad = self.holdings[cad_tickers] if len(cad_tickers) > 0 else pd.DataFrame(index=self.valid_dates)
            self.holdings_usd = self.holdings[usd_tickers] if len(usd_tickers) > 0 else pd.DataFrame(index=self.valid_dates)
        else:
            self.holdings_cad = pd.DataFrame(index=self.valid_dates)
            self.holdings_usd = pd.DataFrame(index=self.valid_dates)

    def _ensure_ticker_currency_map(self):
        """
        Build a cached map of ticker -> currency using yfinance.
        """
        if self.ticker_currency and all(t in self.ticker_currency for t in (self.tickers or [])):
            return
        ticker_currency = {}
        for ticker in (self.tickers or []):
            try:
                ticker_currency[ticker] = yf.Ticker(ticker).info.get('currency', 'CAD')
            except Exception:
                ticker_currency[ticker] = 'CAD'
        self.ticker_currency = ticker_currency

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

    def create_table_portfolio_total(self):
        self.portfolio_total = pd.DataFrame(index=self.valid_dates)

        # Ensure currency map (CAD vs USD tickers)
        self._ensure_ticker_currency_map()
        cad_tickers = [t for t in (self.tickers or []) if self.ticker_currency.get(t, 'CAD') != 'USD']
        usd_tickers = [t for t in (self.tickers or []) if self.ticker_currency.get(t, 'CAD') == 'USD']

        # Totals by currency (native units)
        cad_holdings_mv = self.market_values[cad_tickers].sum(axis=1) if len(cad_tickers) > 0 else pd.Series(0.0, index=self.valid_dates)
        usd_holdings_mv = self.market_values[usd_tickers].sum(axis=1) if len(usd_tickers) > 0 else pd.Series(0.0, index=self.valid_dates)

        # Use the most recent USD→CAD exchange rate for all conversions
        latest_usd_rate = float(self.exchange_rates['USD'].dropna().iloc[-1]) if self.exchange_rates is not None else 1.0

        # Cash breakdown
        cad_cash = self.cash['CAD_Cash']
        usd_cash = self.cash['USD_Cash']
        total_cash_cad = cad_cash + (usd_cash * latest_usd_rate)

        # Holdings and portfolio totals in CAD using the most recent FX rate
        total_holdings_cad = cad_holdings_mv + (usd_holdings_mv * latest_usd_rate)
        total_portfolio_value = total_cash_cad + total_holdings_cad

        # Assign requested columns
        self.portfolio_total['CAD_Holdings_MV'] = cad_holdings_mv
        self.portfolio_total['USD_Holdings_MV'] = usd_holdings_mv
        self.portfolio_total['CAD_Cash'] = cad_cash
        self.portfolio_total['USD_Cash'] = usd_cash
        self.portfolio_total['Total_Cash_CAD'] = total_cash_cad
        self.portfolio_total['Total_Holdings_CAD'] = total_holdings_cad
        self.portfolio_total['Total_Portfolio_Value'] = total_portfolio_value

        pd.DataFrame(self.portfolio_total).to_csv(os.path.join(self.output_folder, portfolio_total_file), index_label='Date')

    # TODO: to remove this because this should be done by a dedicated calculator class/file
    def print_final_values(self):
        market_values_total = self.market_values.loc[self.valid_dates[-1]].sum()
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

        logger.info("")
        logger.info("Portfolio Summary:")
        logger.info(f"Start Date: {self.start_date}")
        logger.info(f"End Date: {(pd.to_datetime(self.end_date) - timedelta(days=1)).strftime('%Y-%m-%d')}")
        logger.info("")
        logger.info(f"Starting Cash: {STARTING_CASH:.2f}")
        logger.info("")
        logger.info(f"CAD Cash (including dividends): {self.cash.loc[self.valid_dates[-1], 'CAD_Cash']:.2f}")
        logger.info(f"USD Cash (including dividends): {self.cash.loc[self.valid_dates[-1], 'USD_Cash']:.2f}")
        logger.info(f"CAD Dividends: {cad_dividends:.2f}")
        logger.info(f"USD Dividends: {usd_dividends:.2f}")
        logger.info(f"Total Dividends (CAD): {total_dividends_cad:.2f}")
        logger.info(f"Total Cash (CAD, including dividends): {cash_total_cad:.2f}")
        logger.info(f"Market Value of holdings: {market_values_total:.2f}")
        logger.info(f"Total Value of portfolio: {(market_values_total + cash_total_cad):.2f}")
        logger.info(f"Total Return: {((market_values_total + cash_total_cad) / STARTING_CASH - 1) * 100:.2f}%")

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
    portfolio.create_table_daily_holdings()
    portfolio.create_table_market_values()
    portfolio.create_table_dividend_per_share()
    portfolio.create_table_dividend_income()
    portfolio.create_table_cash()
    portfolio.create_table_portfolio_total()
    portfolio.create_table_holdings()
    portfolio.print_final_values()
