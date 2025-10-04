"""
Data Service Layer - Centralized data management and caching.

This service layer provides:
- Cached access to portfolio data
- Centralized data loading and processing
- Memory-efficient data serving to views
- Automatic cache invalidation when source data changes
"""

import os
import pandas as pd
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import hashlib
from ..config.logging_config import get_logger

# Set up logger for this module
logger = get_logger(__name__)

class DataService:
    """Centralized data service for portfolio data management"""
    
    def __init__(self, portfolio_name: str, data_directory: str = "data"):
        self.portfolio_name = portfolio_name
        self.data_directory = data_directory
        self.output_folder = os.path.join(data_directory, portfolio_name, "output")
        self.cache_dir = os.path.join(self.output_folder, ".cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Cache for DataFrames
        self._data_cache: Dict[str, Tuple[pd.DataFrame, datetime]] = {}
        self._cache_duration = timedelta(minutes=30)  # Cache for 30 minutes
        
    def _get_file_hash(self, filepath: str) -> str:
        """Get file hash for cache invalidation"""
        if not os.path.exists(filepath):
            return "nonexistent"
        
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def _is_cache_valid(self, cache_key: str, source_files: list) -> bool:
        """Check if cache is still valid based on source file timestamps"""
        if cache_key not in self._data_cache:
            return False
            
        cached_time = self._data_cache[cache_key][1]
        if datetime.now() - cached_time > self._cache_duration:
            return False
            
        # Check if source files have changed
        for filepath in source_files:
            if not os.path.exists(filepath):
                return False
            file_hash = self._get_file_hash(filepath)
            cache_file = os.path.join(self.cache_dir, f"{cache_key}_{os.path.basename(filepath)}.hash")
            
            if not os.path.exists(cache_file):
                return False
                
            with open(cache_file, 'r') as f:
                cached_hash = f.read().strip()
                
            if file_hash != cached_hash:
                return False
                
        return True
    
    def _update_cache(self, cache_key: str, data: pd.DataFrame, source_files: list):
        """Update cache with new data and file hashes"""
        self._data_cache[cache_key] = (data, datetime.now())
        
        # Store file hashes
        for filepath in source_files:
            if os.path.exists(filepath):
                file_hash = self._get_file_hash(filepath)
                cache_file = os.path.join(self.cache_dir, f"{cache_key}_{os.path.basename(filepath)}.hash")
                with open(cache_file, 'w') as f:
                    f.write(file_hash)
    
    def get_portfolio_total_data(self) -> pd.DataFrame:
        """Get portfolio total data (market values + cash)"""
        cache_key = "portfolio_total"
        source_file = os.path.join(self.output_folder, "portfolio_total.csv")
        
        if self._is_cache_valid(cache_key, [source_file]):
            return self._data_cache[cache_key][0]
        
        # Load directly from portfolio_total.csv for authoritative values
        if not os.path.exists(source_file):
            # Fallback to previous method if file missing
            fallback_mv = os.path.join(self.output_folder, "cad_market_values.csv")
            fallback_cash = os.path.join(self.output_folder, "cash.csv")
            if not (os.path.exists(fallback_mv) and os.path.exists(fallback_cash)):
                return pd.DataFrame()
            market_values = pd.read_csv(fallback_mv)
            cash_data = pd.read_csv(fallback_cash)
            market_values['Date'] = pd.to_datetime(market_values['Date'])
            cash_data['Date'] = pd.to_datetime(cash_data['Date'])
            numeric_columns = market_values.columns.drop('Date')
            market_values[numeric_columns] = market_values[numeric_columns].apply(pd.to_numeric, errors='coerce')
            cash_data['Total_CAD'] = cash_data['Total_CAD'].apply(pd.to_numeric, errors='coerce')
            market_values['Total_Market_Value'] = market_values[numeric_columns].sum(axis=1)
            market_values['Total_Portfolio_Value'] = market_values['Total_Market_Value'] + cash_data['Total_CAD']
            result = market_values[['Date', 'Total_Market_Value', 'Total_Portfolio_Value']].copy()
        else:
            result = pd.read_csv(source_file)
            # Ensure proper dtypes and columns
            if 'Date' in result.columns:
                result['Date'] = pd.to_datetime(result['Date'])
            result = result.sort_values('Date')
            # Ensure both columns exist
            if 'Total_Portfolio_Value' not in result.columns or 'Total_Market_Value' not in result.columns:
                # Attempt to infer if different naming used
                raise ValueError("portfolio_total.csv must contain 'Total_Market_Value' and 'Total_Portfolio_Value' columns")
        
        # Compute pct_change if not present
        if 'pct_change' not in result.columns:
            result['pct_change'] = result['Total_Portfolio_Value'].pct_change()
        
        self._update_cache(cache_key, result, [source_file])
        return result
    
    def get_holdings_data(self, as_of_date: Optional[str] = None) -> pd.DataFrame:
        """Get current holdings data"""
        cache_key = "holdings"
        source_files = [
            os.path.join(self.output_folder, "holdings.csv"),
            os.path.join(self.output_folder, "cad_market_values.csv"),
            os.path.join(self.output_folder, "prices.csv")
        ]
        
        # Check if source files exist
        for file_path in source_files:
            if not os.path.exists(file_path):
                logger.error(f"Source file not found: {file_path}")
                return pd.DataFrame()
        
        if self._is_cache_valid(cache_key, source_files):
            return self._data_cache[cache_key][0]
        
        # Load data
        try:
            holdings_df = pd.read_csv(source_files[0])
            market_values_df = pd.read_csv(source_files[1])
            prices_df = pd.read_csv(source_files[2])
            
            # Process holdings data (simplified version)
            holdings_df['Date'] = pd.to_datetime(holdings_df['Date'])
            market_values_df['Date'] = pd.to_datetime(market_values_df['Date'])
            prices_df['Date'] = pd.to_datetime(prices_df['Date'])
            
            # Get latest data
            latest_date = holdings_df['Date'].max()
            if as_of_date:
                latest_date = pd.to_datetime(as_of_date)
        except Exception as e:
            logger.exception(f"Error loading holdings data: {e}")
            return pd.DataFrame()
        
        try:
            holdings_data = holdings_df[holdings_df['Date'] == latest_date].iloc[0]
            market_values_data = market_values_df[market_values_df['Date'] == latest_date].iloc[0]
            prices_data = prices_df[prices_df['Date'] == latest_date].iloc[0]
            
            # Create holdings DataFrame
            holdings_list = []
            for ticker in holdings_data.index:
                if ticker == 'Date':
                    continue
                    
                shares = holdings_data[ticker]
                if shares > 0:
                    market_value = market_values_data[ticker]
                    price = prices_data[ticker]
                    
                    holdings_list.append({
                        'ticker': ticker,
                        'shares': shares,
                        'price': price,
                        'market_value': market_value
                    })
            
            result = pd.DataFrame(holdings_list)
            result = result.sort_values('market_value', ascending=False)
        except Exception as e:
            logger.exception(f"Error processing holdings data: {e}")
            return pd.DataFrame()
        
        self._update_cache(cache_key, result, source_files)
        return result
    
    def get_cash_data(self, as_of_date: Optional[str] = None) -> Dict[str, float]:
        """Get cash data, including USD→CAD exchange rate used for conversion"""
        cache_key = "cash"
        cash_file = os.path.join(self.output_folder, "cash.csv")
        fx_file = os.path.join(self.output_folder, "exchange_rates.csv")
        
        if self._is_cache_valid(cache_key, [cash_file, fx_file]):
            return self._data_cache[cache_key][0]
        
        cash_df = pd.read_csv(cash_file)
        cash_df['Date'] = pd.to_datetime(cash_df['Date'])
        
        if as_of_date is None:
            as_of_dt = cash_df['Date'].max()
        else:
            as_of_dt = pd.to_datetime(as_of_date)
        
        # Load exchange rates to provide USD→CAD rate on the same date
        usd_cad_rate = None
        try:
            fx_df = pd.read_csv(fx_file)
            fx_df['Date'] = pd.to_datetime(fx_df['Date'])
            rate_series = fx_df.set_index('Date')['USD']
            if as_of_dt in rate_series.index:
                usd_cad_rate = float(rate_series.loc[as_of_dt])
            else:
                prior = rate_series[rate_series.index <= as_of_dt]
                usd_cad_rate = float(prior.iloc[-1]) if not prior.empty else None
        except Exception:
            usd_cad_rate = None
        
        cash_row = cash_df[cash_df['Date'] == as_of_dt]
        if cash_row.empty:
            cash_row = cash_df.iloc[[-1]]
        cash_row = cash_row.iloc[0]
        
        result = {
            'CAD_Cash': float(cash_row['CAD_Cash']),
            'USD_Cash': float(cash_row['USD_Cash']),
            'Total_CAD': float(cash_row['Total_CAD']),
            'USD_CAD_Rate': usd_cad_rate
        }
        
        self._update_cache(cache_key, result, [cash_file, fx_file])
        return result
    
    def get_dividend_data(self) -> pd.DataFrame:
        """Get dividend income data"""
        cache_key = "dividends"
        source_file = os.path.join(self.output_folder, "dividend_income.csv")
        
        if self._is_cache_valid(cache_key, [source_file]):
            return self._data_cache[cache_key][0]
        
        dividends_df = pd.read_csv(source_file)
        dividends_df['Date'] = pd.to_datetime(dividends_df['Date'])
        
        self._update_cache(cache_key, dividends_df, [source_file])
        return dividends_df
    
    def clear_cache(self):
        """Clear all cached data"""
        self._data_cache.clear()
        for file in os.listdir(self.cache_dir):
            if file.endswith('.hash'):
                os.remove(os.path.join(self.cache_dir, file))
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about current cache status"""
        cache_info = {}
        for key, (data, timestamp) in self._data_cache.items():
            cache_info[key] = {
                'last_updated': timestamp,
                'age_minutes': (datetime.now() - timestamp).total_seconds() / 60,
                'data_shape': data.shape if hasattr(data, 'shape') else 'dict'
            }
        return cache_info
