import os
import sys
from typing import Dict
import pandas as pd
import yfinance as yf
from datetime import timedelta
import math

# Ensure project root on path for absolute imports when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Robust import that works both as a module and when run directly
try:
    from src.models.security import Security
except ImportError:
    from models.security import Security

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
        self.folder_prefix = folder_prefix

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

        self.securities: Dict[str, Security] = {} # dictionary of ticker -> Security objects

        # Currency-classified data structures (populated by private helper)
        self.cad_tickers = set()
        self.usd_tickers = set()
        self.ticker_currency_map = {}
        self.holdings_cad = None
        self.holdings_usd = None

        # Clean up existing CSV files before building new ones
        self.cleanup_existing_csv_files()
        
        # call valid dates function to get dates that both TSX and American exchanges open 
        self.get_valid_dates()
        # all tickers invested in from trades csv 
        self._load_trades()
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

    def _load_trades(self):
        self.trades = pd.read_csv(os.path.join(self.input_folder, trades_file))
        self.trades['Date'] = pd.to_datetime(self.trades['Date'])
        self.trades.set_index('Date', inplace=True)
        self.tickers = sorted(self.trades['Ticker'].unique())

        for _, row in self.trades.iterrows():
            self.securities[row['Ticker']] = Security(
                ticker=row['Ticker'],
                sector=row['Sector'],
                geography=row['Geography'],
                currency=row['Currency'],
                asset_class=row['Asset_Class']
            )
            self.ticker_currency_map[row['Ticker']] = row['Currency']
            if row['Currency'] == 'USD':
                self.usd_tickers.add(row['Ticker'])
            else:
                self.cad_tickers.add(row['Ticker'])

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

        # If benchmark portfolio rebalance quarterly
        if self.folder_prefix == 'benchmark':
            self._add_quarterly_rebalancing_trades()

    def _calculate_ticker_value_in_cad(self, ticker, quantity, price, date):
        """Helper to calculate ticker value in CAD for a given date.
        
        Args:
            ticker: Ticker symbol
            quantity: Number of shares
            price: Price per share
            date: Date for exchange rate lookup
            
        Returns:
            Value in CAD
        """
        currency = self.ticker_currency_map.get(ticker)
        value = quantity * price
        
        # Get exchange rate for the date
        if date in self.exchange_rates.index:
            usd_rate = float(self.exchange_rates.loc[date, 'USD'])
        else:
             # Use the closest previous date (forward fill logic implies using asof)
             # Since self.exchange_rates is indexed by valid_dates and forward filled,
             # we can look for the last valid index <= date.
             # However, if date is not in index, we need to be careful.
             # self.valid_dates is sorted.
             
             # Find the index position that maintains order
             try:
                 # asof works on the index directly if it's sorted
                 idx = self.exchange_rates.index.get_indexer([date], method='pad')[0]
                 if idx == -1:
                     raise ValueError(f"No exchange rate found on or before {date}")
                 usd_rate = float(self.exchange_rates.iloc[idx]['USD'])
             except Exception as e:
                 raise ValueError(f"Failed to find exchange rate for {date}: {e}")
        
        # Convert to CAD
        if currency == 'USD':
            return value * usd_rate
        else:
            return value

    def _calculate_original_weights(self):
        """Calculate original portfolio weights from initial transactions.
        """
        if self.trades is None or self.trades.empty:
            return {}
        
        first_trade_date = self.trades.index.min()
        initial_trades = self.trades.loc[first_trade_date]
        
        # Handle single trade vs multiple trades
        if isinstance(initial_trades, pd.Series):
            initial_trades = initial_trades.to_frame().T
        
        initial_values = {}
        total_value_cad = 0.0
        
        for _, row in initial_trades.iterrows():
            ticker = row['Ticker']
            quantity = abs(row['Quantity'])  # Use absolute value for buys
            price = row['Price']
            
            value_cad = self._calculate_ticker_value_in_cad(ticker, quantity, price, first_trade_date)
            initial_values[ticker] = value_cad
            total_value_cad += value_cad
        
        weights = {ticker: value / total_value_cad for ticker, value in initial_values.items()}
        logger.info(f"Original benchmark weights calculated: {weights}")
        return weights

    def _get_quarter_end_dates(self):
        """Returns a list of quarter-end dates that fall within valid_dates.
        """
        start = pd.to_datetime(self.start_date)
        end = pd.to_datetime(self.end_date)
        
        quarter_ends = []
        
        quarter_end_months = {1: 3, 
                              2: 6, 
                              3: 9, 
                              4: 12}
        
        if start.month <= 3:
            first_quarter = 1
        elif start.month <= 6:
            first_quarter = 2
        elif start.month <= 9:
            first_quarter = 3
        else:
            first_quarter = 4
        
        # Generate quarter-end dates
        for year in range(start.year, end.year + 1):
            start_quarter = first_quarter if year == start.year else 1
            end_quarter = 4
            
            for quarter in range(start_quarter, end_quarter + 1):
                month = quarter_end_months[quarter]
                day = 31 if month in [3, 12] else 30
                
                try:
                    qe_date = pd.Timestamp(year=year, month=month, day=day)
                    # Only include if it's after start_date and before end_date
                    if start <= qe_date < end:
                        # Find the closest valid trading date (quarter-end or next trading day)
                        valid_qe = self._find_closest_valid_date(qe_date)
                        if valid_qe is not None:
                            quarter_ends.append(valid_qe)
                except ValueError:
                    # Skip invalid dates (e.g., Feb 30)
                    continue
        
        return sorted(set(quarter_ends))

    def _find_closest_valid_date(self, target_date):
        """Find the closest valid trading date to target_date (on or after).
        """
        if self.valid_dates is None or len(self.valid_dates) == 0:
            return None
        
        # Find dates on or after target_date
        valid_after = self.valid_dates[self.valid_dates >= target_date]
        if len(valid_after) > 0:
            return valid_after[0]
        
        return None

    def _simulate_holdings_to_date(self, target_date, additional_trades=None):
        """Simulate holdings up to a given date by processing trades. 
        Returns a dict mapping ticker to quantity held.
        """
        holdings = {ticker: 0.0 for ticker in self.tickers}
        
        # Process all trades up to and including target_date
        trades_up_to_date = self.trades[self.trades.index <= target_date]
        
        # Include additional trades if provided
        if additional_trades is not None and not additional_trades.empty:
            additional_up_to_date = additional_trades[additional_trades.index <= target_date]
            trades_up_to_date = pd.concat([trades_up_to_date, additional_up_to_date]).sort_index()
        
        for date, trade_group in trades_up_to_date.groupby(trades_up_to_date.index):
            if isinstance(trade_group, pd.Series):
                trade_group = trade_group.to_frame().T
            
            for _, row in trade_group.iterrows():
                ticker = row['Ticker']
                quantity = row['Quantity']
                holdings[ticker] = holdings.get(ticker, 0.0) + quantity
        
        return holdings

    def _calculate_portfolio_value_at_date(self, date, holdings_dict):
        """Calculate total portfolio value in CAD at a given date.
        
        Args:
            date: Target date
            holdings_dict: Dict mapping ticker to quantity
            
        Returns:
            Total portfolio value in CAD
        """
        if date not in self.prices.index or date not in self.exchange_rates.index:
            return 0.0
        
        total_value_cad = 0.0
        
        for ticker, quantity in holdings_dict.items():
            if ticker not in self.prices.columns or quantity == 0:
                continue
            
            price = float(self.prices.loc[date, ticker])
            if pd.isna(price):
                continue
            
            # Use shared helper to calculate value in CAD
            value_cad = self._calculate_ticker_value_in_cad(ticker, quantity, price, date)
            total_value_cad += value_cad
        
        return total_value_cad

    def _add_quarterly_rebalancing_trades(self):
        """ Quarterly rebalancing to maintain weighting over time
        1. Calculates original weights from initial transactions
        2. Finds all quarter-end dates
        3. Calculates current weights and creates rebalancing trades
        4. Adds these trades to self.trades
        """
        if self.prices is None or self.prices.empty:
            logger.warning("Cannot add rebalancing trades: prices not yet created")
            return
        
        # Calculate original weights
        original_weights = self._calculate_original_weights()
        if not original_weights:
            logger.warning("Could not calculate original weights for rebalancing")
            return
        
        # Get quarter-end dates
        quarter_ends = self._get_quarter_end_dates()
        if not quarter_ends:
            logger.info("No quarter-end dates found for rebalancing")
            return
        
        logger.info(f"Adding quarterly rebalancing trades for {len(quarter_ends)} quarter-ends")
        
        rebalancing_trades = []
        prev_trades = pd.DataFrame()
        
        for qe_date in quarter_ends:
            
            current_holdings = self._simulate_holdings_to_date(
                qe_date, 
                additional_trades=prev_trades if not prev_trades.empty else None
            )
            
            # Calculate current portfolio value
            portfolio_value_cad = self._calculate_portfolio_value_at_date(qe_date, current_holdings)
            
            if portfolio_value_cad == 0:
                logger.warning(f"Skipping rebalancing on {qe_date}: portfolio value is zero")
                continue
            
            # Calculate target holdings for each ticker based on original weights
            usd_rate = float(self.exchange_rates.loc[qe_date, 'USD'])
            
            for ticker, target_weight in original_weights.items():
                if ticker not in self.prices.columns:
                    continue
                
                price = float(self.prices.loc[qe_date, ticker])
                if pd.isna(price) or price == 0:
                    continue
                
                currency = self.ticker_currency_map.get(ticker, 'CAD')
                
                # Calculate target value in CAD
                target_value_cad = portfolio_value_cad * target_weight
                
                # Convert to native currency
                if currency == 'USD':
                    target_value = target_value_cad / usd_rate
                else:
                    target_value = target_value_cad
                
                # Calculate target quantity
                target_quantity = target_value / price
                
                # Current quantity
                current_quantity = current_holdings.get(ticker, 0.0)
                
                # Calculate rebalancing quantity (difference)
                rebalance_quantity = target_quantity - current_quantity
                
                # Only add trade if difference is significant (more than 0.01 shares)
                if abs(rebalance_quantity) > 0.01:
                    rebalancing_trades.append({
                        'Date': qe_date,
                        'Ticker': ticker,
                        'Currency': currency,
                        'Quantity': rebalance_quantity,
                        'Price': price
                    })
                    logger.info(
                        f"Rebalancing {ticker} on {qe_date.strftime('%Y-%m-%d')}: "
                        f"{current_quantity:.4f} -> {target_quantity:.4f} "
                        f"(delta: {rebalance_quantity:+.4f})"
                    )
            
            # Accumulate rebalancing trades for this quarter-end to include in next simulation
            if rebalancing_trades:
                # Get trades just added for this quarter-end
                current_qe_trades = [t for t in rebalancing_trades if t['Date'] == qe_date]
                if current_qe_trades:
                    qe_df = pd.DataFrame(current_qe_trades)
                    qe_df['Date'] = pd.to_datetime(qe_df['Date'])
                    qe_df.set_index('Date', inplace=True)
                    if prev_trades.empty:
                        prev_trades = qe_df
                    else:
                        prev_trades = pd.concat([prev_trades, qe_df]).sort_index()
        
        # Add rebalancing trades to self.trades
        if rebalancing_trades:
            rebalance_df = pd.DataFrame(rebalancing_trades)
            rebalance_df['Date'] = pd.to_datetime(rebalance_df['Date'])
            rebalance_df.set_index('Date', inplace=True)
            
            # Combine with existing trades and sort
            self.trades = pd.concat([self.trades, rebalance_df]).sort_index()
            logger.info(f"Added {len(rebalancing_trades)} rebalancing trades to benchmark portfolio")

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
                logger.debug(f"Processing trades on {date}")

                rows_for_date = self.trades.loc[date]

                # Ensure rows_for_date is a DataFrame
                # (if there is only one row, it will be a Series)
                if isinstance(rows_for_date, pd.Series):
                    rows_for_date = rows_for_date.to_frame().T
                for _, row in rows_for_date.iterrows():
                    quantity = row['Quantity']
                    ticker = row['Ticker']
                    self.holdings.at[date, ticker] = self.holdings.loc[date, ticker] + quantity

                    if self.holdings.loc[date, ticker] == 0.0:
                        self.securities[ticker].set_status('closed')
                    else:
                        self.securities[ticker].set_status('open')

        pd.DataFrame(self.holdings).to_csv(os.path.join(self.output_folder, holdings_file), index_label='Date')

    def create_table_cash(self):
        # TODO: Make this currency cache a class variable potentially
        ticker_currency_map = {}
        for ticker in self.tickers:
            ticker_currency_map[ticker] = yf.Ticker(ticker).info.get('currency')

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
            
            if i != 0:
                self.cash.loc[date] = self.cash.loc[self.valid_dates[i - 1]]
                current_cad_cash = self.cash.loc[date, 'CAD_Cash']
                current_usd_cash = self.cash.loc[date, 'USD_Cash']

            # First, process explicit currency conversions for this date
            if self.conversions is not None and not self.conversions.empty and date in self.conversions.index:
                rows_for_date = self.conversions.loc[date]
                if isinstance(rows_for_date, pd.Series):
                    rows_for_date = rows_for_date.to_frame().T
                for _, row in rows_for_date.iterrows():
                    c_from = row['Currency_From']
                    c_to = row['Currency_To']
                    amount = float(row['Amount'])
                    rate = float(row['Rate']) if not (isinstance(row['Rate'], float) and math.isnan(row['Rate'])) else None
                    # Fallback to exchange rate table if Rate is NaN
                    if rate is None:
                        if date not in self.exchange_rates.index:
                             # Try to get previous valid rate
                             try:
                                 idx = self.exchange_rates.index.get_indexer([date], method='pad')[0]
                                 if idx == -1:
                                     raise ValueError(f"No exchange rate found on or before {date}")
                                 current_usd_rate = float(self.exchange_rates.iloc[idx]['USD'])
                             except Exception as e:
                                 raise ValueError(f"Failed to find exchange rate for {date}: {e}")
                        else:
                             current_usd_rate = float(self.exchange_rates.loc[date, 'USD'])

                        # Rate defined as units of To per 1 unit of From
                        if c_from == 'USD' and c_to == 'CAD':
                            rate = current_usd_rate
                        elif c_from == 'CAD' and c_to == 'USD':
                            rate = 1.0 / current_usd_rate
                        else:
                            raise ValueError(f"Unsupported conversion pair without explicit rate: {c_from}->{c_to}")

                    logger.info(f"Applying conversion on {date.strftime('%Y-%m-%d')}: {amount:.2f} {c_from} -> {c_to} at {rate:.6g}")

                    if c_from == 'CAD' and c_to == 'USD':
                        cad_delta = -amount
                        usd_delta = amount * rate
                        current_cad_cash += cad_delta
                        current_usd_cash += usd_delta
                    elif c_from == 'USD' and c_to == 'CAD':
                        usd_delta = -amount
                        cad_delta = amount * rate
                        current_usd_cash += usd_delta
                        current_cad_cash += cad_delta
                    else:
                        # Future currencies can be added here
                        raise ValueError(f"Unsupported currency conversion: {c_from}->{c_to}")

                    # Update balances after each conversion
                    self.cash.at[date, 'CAD_Cash'] = current_cad_cash
                    self.cash.at[date, 'USD_Cash'] = current_usd_cash
                    total_cad = current_cad_cash + (current_usd_cash * self.exchange_rates.loc[date, 'USD'])
                    self.cash.at[date, 'Total_CAD'] = total_cad

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

                    logger.debug(f"Trade: {ticker} - {quantity} shares @ ${price:.2f} {currency}")
                    logger.debug(f"Trade value: ${trade_value:.2f} {currency}")

                    if quantity > 0:
                        # Buy: Deduct cash using helper
                        current_cad_cash, current_usd_cash, conversion_type = self._convert_currency_for_trade(
                            trade_value, currency, current_cad_cash, current_usd_cash, date
                        )
                        logger.debug("Buy: Decreased cash for purchase.")
                    elif quantity < 0:
                        # Sell: Add proceeds to correct cash balance
                        if currency == 'CAD':
                            current_cad_cash += trade_value
                            logger.debug(f"Sell: Increased CAD cash by ${trade_value:.2f}")
                        elif currency == 'USD':
                            current_usd_cash += trade_value
                            logger.debug(f"Sell: Increased USD cash by ${trade_value:.2f}")
                        else:
                            # If unknown currency, default to CAD
                            current_cad_cash += trade_value
                            logger.debug(f"Sell: Unknown currency, increased CAD cash by ${trade_value:.2f}")

                    # Update cash balances
                    self.cash.at[date, 'CAD_Cash'] = current_cad_cash
                    self.cash.at[date, 'USD_Cash'] = current_usd_cash
                    # Calculate total in CAD
                    total_cad = current_cad_cash + (current_usd_cash * self.exchange_rates.loc[date, 'USD'])
                    self.cash.at[date, 'Total_CAD'] = total_cad
                    logger.debug(f"After trade - CAD: ${current_cad_cash:.2f}, USD: ${current_usd_cash:.2f}, Total CAD: ${total_cad:.2f}")

            # Process dividends for this date
            if self.dividend_income is not None and date in self.dividend_income.index:
                logger.info(f"--- Processing dividends on {date.strftime('%Y-%m-%d')} ---")
                logger.debug(f"Starting balances - CAD: ${current_cad_cash:.2f}, USD: ${current_usd_cash:.2f}")
                
                for ticker in self.tickers:
                    dividend_amount = self.dividend_income.at[date, ticker] if ticker in self.dividend_income.columns else 0.0
                    if pd.isna(dividend_amount) or dividend_amount == 0.0:
                        continue
                    currency = ticker_currency_map.get(ticker, 'CAD')
                    logger.debug(f"Dividend: {ticker} - ${dividend_amount:.2f} {currency}")
                    # Add dividend to appropriate currency balance
                    if currency == 'CAD':
                        current_cad_cash += dividend_amount
                        logger.debug(f"Added ${dividend_amount:.2f} to CAD cash")
                    elif currency == 'USD':
                        current_usd_cash += dividend_amount
                        logger.debug(f"Added ${dividend_amount:.2f} to USD cash")
                    else:
                        # If unknown currency, default to CAD
                        current_cad_cash += dividend_amount
                        logger.debug(f"Unknown currency, added ${dividend_amount:.2f} to CAD cash")
                    # Update cash balances
                    self.cash.at[date, 'CAD_Cash'] = current_cad_cash
                    self.cash.at[date, 'USD_Cash'] = current_usd_cash
                    # Calculate total in CAD
                    total_cad = current_cad_cash + (current_usd_cash * self.exchange_rates.loc[date, 'USD'])
                    self.cash.at[date, 'Total_CAD'] = total_cad
                    logger.debug(f"After dividend - CAD: ${current_cad_cash:.2f}, USD: ${current_usd_cash:.2f}, Total CAD: ${total_cad:.2f}")

        pd.DataFrame(self.cash).to_csv(os.path.join(self.output_folder, cash_file), index_label='Date')

    def _convert_currency_for_trade(self, trade_value, trade_currency, current_cad_cash, current_usd_cash, date):
        """
        Helper function to handle currency conversion for trades.
        
        Args:
            trade_value: Amount of the trade
            trade_currency: Currency of the trade ('CAD' or 'USD')
            current_cad_cash: Current CAD cash balance
            current_usd_cash: Current USD cash balance
            date: Date of the trade for exchange rate lookup
            
        Returns:
            tuple: (new_cad_cash, new_usd_cash, conversion_details)
        """
        if trade_currency == 'CAD':
            # For CAD trades, use CAD cash first, convert USD if needed
            if current_cad_cash >= trade_value:
                # We have enough CAD cash
                logger.debug(f"CAD trade - using existing CAD cash (${current_cad_cash:.2f} available)")
                return current_cad_cash - trade_value, current_usd_cash, "used_cad_cash"
            else:
                # Need to convert some USD to CAD
                cad_needed = trade_value - current_cad_cash
                usd_to_convert = cad_needed / self.exchange_rates.loc[date, 'USD']
                exchange_rate = self.exchange_rates.loc[date, 'USD']
                
                logger.debug(f"CAD trade - need ${cad_needed:.2f} more CAD")
                logger.debug(f"Converting ${usd_to_convert:.2f} USD to CAD (rate: {exchange_rate:.4f})")
                logger.debug(f"Using all available CAD cash: ${current_cad_cash:.2f}")
                
                # Use all available CAD cash and convert USD
                new_cad_cash = 0
                new_usd_cash = current_usd_cash - usd_to_convert
                return new_cad_cash, new_usd_cash, "converted_usd_to_cad"
        elif trade_currency == 'USD':
            # For USD trades, use USD cash first, convert CAD if needed
            if current_usd_cash >= trade_value:
                # We have enough USD cash
                logger.debug(f"USD trade - using existing USD cash (${current_usd_cash:.2f} available)")
                return current_cad_cash, current_usd_cash - trade_value, "used_usd_cash"
            else:
                # Need to convert some CAD to USD
                usd_needed = trade_value - current_usd_cash
                cad_to_convert = usd_needed * self.exchange_rates.loc[date, 'USD']
                exchange_rate = self.exchange_rates.loc[date, 'USD']
                
                logger.debug(f"  USD trade - need ${usd_needed:.2f} more USD")
                logger.debug(f"  Converting ${cad_to_convert:.2f} CAD to USD (rate: {exchange_rate:.4f})")
                logger.debug(f"  Using all available USD cash: ${current_usd_cash:.2f}")
                
                # Use all available USD cash and convert CAD
                new_cad_cash = current_cad_cash - cad_to_convert
                new_usd_cash = 0
                return new_cad_cash, new_usd_cash, "converted_cad_to_usd"

    def create_table_market_values(self):
        holdings = self.holdings[self.tickers]
        prices = self.prices[self.tickers]
        
        # Convert to CAD directly using exchange rates
        market_values = pd.DataFrame(index=self.valid_dates)
        for ticker in self.tickers:
            market_values[ticker] = prices[ticker] * holdings[ticker]

        self.market_values = market_values
        pd.DataFrame(self.market_values).to_csv(os.path.join(self.output_folder, market_values_file), index_label='Date')

    def create_table_holdings(self):
        """
        Builds a holdings summary where all financial metrics are reported in 
        the ticker's NATIVE currency (USD or CAD).
        
        Aggregate calculations (Holding Weight) use a normalized CAD value 
        using the LATEST exchange rate to ensure accurate proportions.
        """
        if self.prices is None or self.prices.empty:
            raise ValueError("Prices are not computed.")

        split_events = self._fetch_split_events()
        
        # Get latest date for split calculations
        latest_date = self.valid_dates[-1]

        # Helper to calculate cumulative split factor from a date to the end
        def cumulative_split_factor(ticker, from_date, to_date):
            events = split_events.get(ticker, {})
            if not events:
                return 1.0
            factor = 1.0
            for event_date, event_factor in events.items():
                # Apply splits strictly after the date up to and including end date
                if from_date < event_date <= to_date:
                    try:
                        factor *= float(event_factor)
                    except Exception:
                        continue
            return factor

        # 1. Initialize State Tracking (All in Native Currency)
        positions = {
            ticker: {
                'qty': 0.0,
                'book_value': 0.0,       # Total Cost Basis (Native)
                'realized_pnl': 0.0,     # Realized Gains/Losses (Native)
                'total_dividends': 0.0,  # Dividends Collected (Native)
                'cost_of_closed': 0.0    # Accumulates cost of shares sold (for ROI calc)
            } for ticker in self.tickers
        }

        # 2. Process Trades (Chronological)
        # Apply split adjustments to trades so we process everything in "current share" equivalents
        if self.trades is not None and not self.trades.empty:
            sorted_trades = self.trades.sort_index().copy()
            
            # Apply split adjustment to all trades (Buys and Sells)
            # Quantity * Factor
            # Price / Factor
            # Value = Quantity * Price (Unchanged)
            
            sorted_trades['split_factor'] = sorted_trades.apply(
                lambda r: cumulative_split_factor(r['Ticker'], r.name, latest_date), axis=1
            )
            
            # Adjust Quantity and Price to be in "Today's Terms"
            sorted_trades['Quantity'] = sorted_trades['Quantity'] * sorted_trades['split_factor']
            sorted_trades['Price'] = sorted_trades['Price'] / sorted_trades['split_factor']

            for date, row in sorted_trades.iterrows():
                ticker = row['Ticker']
                quantity = row['Quantity'] # + for Buy, - for Sell
                price = row['Price']       # Adjusted Price
                
                # Transaction Value (Native) - Should match original trade value
                trade_val = abs(quantity) * price
                
                if quantity > 0: # BUY
                    positions[ticker]['qty'] += quantity
                    positions[ticker]['book_value'] += trade_val
                    
                elif quantity < 0: # SELL
                    qty_sold = abs(quantity)
                    qty_held_before = positions[ticker]['qty']
                    
                    # Prevent divide by zero / Short sell logic gap
                    if qty_held_before > 0:
                        fraction_sold = qty_sold / qty_held_before
                        
                        # 1. Calculate Cost Basis of the specific chunk being sold
                        cost_chunk = positions[ticker]['book_value'] * fraction_sold
                        
                        # 2. Calculate PnL (Proceeds - Cost)
                        proceeds = trade_val
                        pnl = proceeds - cost_chunk
                        
                        # 3. Update Ledger
                        positions[ticker]['realized_pnl'] += pnl
                        positions[ticker]['book_value'] -= cost_chunk
                        positions[ticker]['qty'] -= qty_sold
                        
                        # 4. Track capital for Closed ROI
                        # If we sold, we add the cost basis of those shares to the "closed bucket"
                        positions[ticker]['cost_of_closed'] += cost_chunk

            # First purchase and last sale dates per ticker (for annualized return)
            first_purchase_dates = {}
            last_sale_dates = {}
            for date, row in sorted_trades.iterrows():
                t = row['Ticker']
                qty_trade = row['Quantity']
                if qty_trade > 0:  # Buy: use first purchase date
                    if t not in first_purchase_dates or date < first_purchase_dates[t]:
                        first_purchase_dates[t] = date
                elif qty_trade < 0:  # Sell: use last sale date
                    if t not in last_sale_dates or date > last_sale_dates[t]:
                        last_sale_dates[t] = date
        else:
            first_purchase_dates = {}
            last_sale_dates = {}

        # 3. Process Dividends - No FX needed here!
        if self.dividend_income is not None and not self.dividend_income.empty:
            for date, row in self.dividend_income.iterrows():
                for ticker, div_amount in row.items():
                    if div_amount > 0 and ticker in positions:
                        # Assumes dividend is paid in native currency (Standard behavior)
                        positions[ticker]['total_dividends'] += div_amount

        # 4. Build Final DataFrame
        latest_date = self.valid_dates[-1]
        latest_prices = self.prices.loc[latest_date]
        
        # We only need the FX rate NOW for the weighting calculation
        # Get latest USD to CAD rate
        latest_fx_usd_cad = float(self.exchange_rates['USD'].dropna().iloc[-1])

        results = []
        
        for ticker, data in positions.items():
            qty = data['qty']
            
            # Metadata
            currency = self.ticker_currency_map[ticker]
            current_price = float(latest_prices[ticker])
            
            # --- Native Metrics ---
            market_val_native = qty * current_price
            
            # Average Price (Simple Average: Total Book / Total Shares)
            avg_price = (data['book_value'] / qty) if qty > 0 else 0.0
            
            # Unrealized PnL (Market Value - Remaining Book Value)
            if qty > 0.00001:
                unrealized_pnl = market_val_native - data['book_value']
                # Denominator for ROI is the current money tied up
                roi_denominator = data['book_value']
            else:
                unrealized_pnl = 0.0
                # Denominator for ROI is the money that WAS tied up
                roi_denominator = data['cost_of_closed']
                qty = 0.0 # Clean up dust
                
            total_return_native = data['realized_pnl'] + unrealized_pnl + data['total_dividends']
            
            # ROI % (Native Return / Native Investment)
            # Math is identical regardless of currency
            return_pct = (total_return_native / roi_denominator * 100.0) if roi_denominator > 0 else 0.0

            # Annualized return since purchase: (1 + Total Return %)^(365 / Days Held) - 1
            # Days Held: first purchase -> today (open) or last sale (closed); use first purchase only
            is_open = data['qty'] > 0.00001
            first_purchase = first_purchase_dates.get(ticker)
            if first_purchase is None or roi_denominator <= 0:
                annualized_return_pct = float('nan')
            else:
                end_date = latest_date if is_open else last_sale_dates.get(ticker, first_purchase)
                start_d = pd.Timestamp(first_purchase)
                end_d = pd.Timestamp(end_date)
                days_held = (end_d - start_d).days
                if days_held > 0:
                    annualized_return_pct = ((1.0 + return_pct / 100.0) ** (365.0 / days_held) - 1.0) * 100.0
                else:
                    annualized_return_pct = float('nan')

            # --- Aggregation Prep (Normalized to CAD) ---
            # We calculate a hidden CAD market value solely for the weighting step
            fx_multiplier = latest_fx_usd_cad if currency == 'USD' else 1.0
            market_val_cad_calc = market_val_native * fx_multiplier
            
            sec = self.securities.get(ticker)

            results.append({
                'ticker': ticker,
                'shares': qty,
                'currency': currency,
                
                # REPORTING COLUMNS (Native)
                'current_price': current_price,
                'avg_price': avg_price,
                'market_value': market_val_native,
                'book_value': data['book_value'] if qty > 0 else 0.0, # Only show book value if open
                'dividends': data['total_dividends'],
                'realized_pnl': data['realized_pnl'],
                'unrealized_pnl': unrealized_pnl,
                'total_return': total_return_native,
                'total_return_cad_normalized': total_return_native * latest_fx_usd_cad,
                'total_return_pct': return_pct,
                'annualized_return_pct': annualized_return_pct,
                
                'mv_cad_normalized': market_val_cad_calc,
                'invested_capital': roi_denominator,
                'invested_capital_cad': roi_denominator * latest_fx_usd_cad,
                
                # METADATA
                'sector': sec.get_sector() if sec else 'Unknown',
                'asset_class': sec.get_asset_class() if sec else 'Unknown',
                'status': 'Open' if qty > 0 else 'Closed'
            })

        df = pd.DataFrame(results)
        
        # 5. Calculate Weights (Using the Normalized CAD values)
        # Total Portfolio Value in CAD
        total_portfolio_cad = df['mv_cad_normalized'].sum()
        
        df['holding_weight'] = df['mv_cad_normalized'].apply(
            lambda x: (x / total_portfolio_cad * 100.0) if total_portfolio_cad > 0 else 0.0
        )
        
        # Sort by the implicit CAD value (Largest positions first)
        # We have to re-calculate sort key or use the weight
        df = df.sort_values('holding_weight', ascending=False)
        
        df.to_csv(os.path.join(self.output_folder, holdings_summary_file), index=False)

    def _build_currency_holdings(self):
        """
        Build CAD- and USD-only holdings DataFrames using precomputed ticker lists.

        Relies on:
        - self.cad_tickers / self.usd_tickers (populated in _load_trades)
        - self.holdings (constructed in create_table_holdings)

        Produces:
        - self.holdings_cad, self.holdings_usd
        """
        cad_tickers = self.cad_tickers or []
        usd_tickers = self.usd_tickers or []

        if self.holdings is not None and not self.holdings.empty:
            cad_cols = list(cad_tickers) if len(cad_tickers) > 0 else []
            usd_cols = list(usd_tickers) if len(usd_tickers) > 0 else []
            self.holdings_cad = self.holdings[cad_cols] if len(cad_cols) > 0 else pd.DataFrame(index=self.valid_dates)
            self.holdings_usd = self.holdings[usd_cols] if len(usd_cols) > 0 else pd.DataFrame(index=self.valid_dates)
        else:
            self.holdings_cad = pd.DataFrame(index=self.valid_dates)
            self.holdings_usd = pd.DataFrame(index=self.valid_dates)

    def _ensure_ticker_currency_map(self):
        """
        Build a cached map of ticker -> currency using yfinance.
        """
        if self.ticker_currency_map and all(t in self.ticker_currency_map for t in (self.tickers or [])):
            return
        ticker_currency_map = {}
        for ticker in (self.tickers or []):
            try:
                ticker_currency_map[ticker] = yf.Ticker(ticker).info.get('currency', 'CAD')
            except Exception:
                ticker_currency_map[ticker] = 'CAD'
        self.ticker_currency_map = ticker_currency_map

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

        # # Ensure currency map (CAD vs USD tickers)
        # self._ensure_ticker_currency_map()
        # cad_tickers = [t for t in (self.tickers or []) if self.ticker_currency_map.get(t, 'CAD') != 'USD']
        # usd_tickers = [t for t in (self.tickers or []) if self.ticker_currency_map.get(t, 'CAD') == 'USD']

        # Totals by currency (native units)
        cad_cols = list(self.cad_tickers) if len(self.cad_tickers) > 0 else []
        usd_cols = list(self.usd_tickers) if len(self.usd_tickers) > 0 else []
        cad_holdings_mv = self.market_values[cad_cols].sum(axis=1) if len(cad_cols) > 0 else pd.Series(0.0, index=self.valid_dates)
        usd_holdings_mv = self.market_values[usd_cols].sum(axis=1) if len(usd_cols) > 0 else pd.Series(0.0, index=self.valid_dates)

        # Use historical exchange rates for each date
        # Align exchange rates with the data index (should match valid_dates)
        usd_rates = self.exchange_rates['USD'].reindex(self.valid_dates).ffill()

        # Cash breakdown
        cad_cash = self.cash['CAD_Cash']
        usd_cash = self.cash['USD_Cash']
        
        # Convert USD cash to CAD using daily rates
        total_cash_cad = cad_cash + (usd_cash * usd_rates)

        # Convert USD holdings to CAD using daily rates
        total_holdings_cad = cad_holdings_mv + (usd_holdings_mv * usd_rates)
        
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
    portfolio._load_trades()

    portfolio.create_table_prices()
    portfolio.create_table_daily_holdings()
    portfolio.create_table_market_values()
    portfolio.create_table_dividend_per_share()
    portfolio.create_table_dividend_income()
    portfolio.create_table_cash()
    portfolio.create_table_portfolio_total()
    portfolio.create_table_holdings()
    portfolio.print_final_values()
