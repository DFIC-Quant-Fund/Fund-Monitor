"""
Portfolio Controller - Main business logic orchestrator.

This controller handles all portfolio operations including:
- Loading portfolio data via DataService
- Calculating performance metrics
- Managing data building operations
- Serving data directly to views
"""

import os
import sys
import pandas as pd
import yfinance as yf
from datetime import datetime
from typing import List, Dict, Any

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import performance modules
from .returns_calculator import ReturnsCalculator
from .risk_metrics import RiskMetrics
from .market_comparison import MarketComparison
from .benchmark import Benchmark
from .data_service import DataService

# Import logging
from ..config.logging_config import get_logger

# Set up logger for this module
logger = get_logger(__name__)

class PortfolioController:
    """Main controller for portfolio operations"""
    
    def __init__(self, portfolio_name: str, data_directory: str = "data"):
        self.portfolio_name = portfolio_name
        self.data_directory = data_directory
        self.output_folder = os.path.join(data_directory, portfolio_name, "output")
        self.input_folder = os.path.join(data_directory, portfolio_name, "input")
        
        # Initialize data service
        self._data_service = DataService(portfolio_name, data_directory)
        
        # Initialize performance calculators
        self._risk_metrics = None  # Will build per-request with actual df
        self._market_comparison = None  # Construct per-request with current portfolio df
        self._benchmark = Benchmark()
    
    def get_available_portfolios(self) -> List[str]:
        """Get list of available portfolios"""
        if not os.path.exists(self.data_directory):
            return []
        
        return [
            folder for folder in os.listdir(self.data_directory)
            if os.path.isdir(os.path.join(self.data_directory, folder))
        ]
    
    
    def get_portfolio_summary(self, as_of_date: str = None) -> Dict[str, Any]:
        """Get portfolio summary data"""
        try:
            holdings_df = self._data_service.get_holdings_data()
            if holdings_df.empty:
                raise ValueError(f"No holdings data found for portfolio {self.portfolio_name}. Please ensure the portfolio data has been built.")
        except Exception as e:
            raise ValueError(f"Error loading portfolio data for {self.portfolio_name}: {str(e)}")
        
        # Use authoritative totals from portfolio_total.csv
        totals_df = self._data_service.get_portfolio_total_data()
        if as_of_date:
            as_of_dt = pd.to_datetime(as_of_date)
        else:
            as_of_dt = totals_df['Date'].max() if not totals_df.empty else pd.to_datetime(datetime.now())
        row = totals_df[totals_df['Date'] == as_of_dt]
        if row.empty and not totals_df.empty:
            # closest previous date
            as_of_dt = totals_df['Date'].max()
            row = totals_df[totals_df['Date'] == as_of_dt]
        # Use concrete columns emitted by the builder
        if not row.empty:
            total_holdings_value = float(row.iloc[0]['Total_Holdings_CAD'])
            total_portfolio_value = float(row.iloc[0]['Total_Portfolio_Value'])
            total_cash_cad = float(row.iloc[0]['Total_Cash_CAD'])
            cad_holdings_mv = float(row.iloc[0]['CAD_Holdings_MV'])
            usd_holdings_mv = float(row.iloc[0]['USD_Holdings_MV'])
            cad_cash = float(row.iloc[0]['CAD_Cash'])
            usd_cash = float(row.iloc[0]['USD_Cash'])
        else:
            logger.warning(f"No portfolio total data found for {as_of_date}. Using latest available data.")
            total_holdings_value = float(holdings_df['market_value'].sum())
            total_portfolio_value = total_holdings_value
            total_cash_cad = 0.0
            cad_holdings_mv = float(holdings_df['market_value'].sum())
            usd_holdings_mv = 0.0
            cad_cash = 0.0
            usd_cash = 0.0
        
        total_holdings = len(holdings_df)

        # Cumulative return since inception (%)
        try:
            returns_series_df = ReturnsCalculator(totals_df).cumulative_return_series()
            inception_return_pct = float(returns_series_df['Cumulative_Return_Pct'].iloc[-1]) if not returns_series_df.empty else None
        except Exception as e:
            logger.warning(f"Could not compute inception cumulative return: {e}")
            inception_return_pct = None
        
        return {
            'total_holdings_value': total_holdings_value,
            'total_holdings': total_holdings,
            'as_of_date': as_of_dt,
            'total_portfolio_value': total_portfolio_value,
            'total_cash_cad': total_cash_cad,
            'cad_holdings_mv': cad_holdings_mv,
            'usd_holdings_mv': usd_holdings_mv,
            'cad_cash': cad_cash,
            'usd_cash': usd_cash,
            'inception_return_pct': inception_return_pct
        }
    
    def get_holdings_data(self, as_of_date: str = None) -> pd.DataFrame:
        """Get holdings data as DataFrame"""
        holdings_df = self._data_service.get_holdings_data()
        portfolio_total_df = self._data_service.get_portfolio_total_data()
        
        # Calculate weights
        if portfolio_total_df.empty:
            raise ValueError("portfolio_total.csv is empty or missing required data (Total_Holdings_CAD).")
        # Use latest (or selected) Total_Holdings_CAD
        if as_of_date is not None:
            as_of_dt = pd.to_datetime(as_of_date)
            row = portfolio_total_df.loc[portfolio_total_df['Date'] == as_of_dt]
            if row.empty:
                row = portfolio_total_df.sort_values('Date').iloc[[-1]]
        else:
            row = portfolio_total_df.sort_values('Date').iloc[[-1]]
        total_value = float(row.iloc[0]['Total_Holdings_CAD'])

        denom = total_value if total_value > 0 else 0.0
        if denom > 0:
            # Prefer CAD-based weighting if available
            numer = holdings_df['market_value_cad'] if 'market_value_cad' in holdings_df.columns else holdings_df['market_value']
            holdings_df['holdings_weight_percent'] = (numer / denom) * 100.0
        else:
            holdings_df['holdings_weight_percent'] = 0.0
        
        return holdings_df
    
    def get_allocation_data(self) -> pd.DataFrame:
        """Get allocation data as DataFrame"""
        df = self._data_service.get_allocation_data()
        if df.empty:
            logger.error("Allocation data is empty")
            return df
        
        # Need: ticker, sector, geography, currency, holding_weight, market_value
        # Then need allocation chart for only equities (exclude cash, fixed income and gold)
        # and another chart for cash and fixed income only
        # Another chart for all holdings including cash, gold and fixed income

        # Calculate per-ticker weights directly on df
        sector_norm = df['sector'].astype(str).str.lower()
        is_equity = (sector_norm != 'fixed income') & (sector_norm != 'absolute return')
        is_fixed_income = (sector_norm == 'fixed income')

        total_equity_mv = df.loc[is_equity, 'market_value_cad'].sum()
        total_fi_mv = df.loc[is_fixed_income, 'market_value_cad'].sum()

        df['equity_weight_percent'] = 0.0
        df.loc[is_equity & (total_equity_mv > 0), 'equity_weight_percent'] = (
            df.loc[is_equity, 'market_value_cad'] / total_equity_mv * 100.0
        )

        df['fi_weight_percent'] = 0.0
        df.loc[is_fixed_income & (total_fi_mv > 0), 'fi_weight_percent'] = (
            df.loc[is_fixed_income, 'market_value_cad'] / total_fi_mv * 100.0
        )

        return df


    
    def get_performance_metrics(self, date: str = None, risk_free_rate: float = 0.02) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        portfolio_total_df = self._data_service.get_portfolio_total_data()
        
        if portfolio_total_df.empty:
            raise FileNotFoundError(f"Portfolio total data not found for {self.portfolio_name}")
        
        if date is None:
            date = portfolio_total_df['Date'].max()
        else:
            date = pd.to_datetime(date)
        
        # Calculate returns for different periods
        returns_calc = ReturnsCalculator(portfolio_total_df, date)
        if not returns_calc.valid_date():
            logger.warning(f"Date {date} not available in data, using latest available date")
            date = portfolio_total_df['Date'].max()
            returns_calc = ReturnsCalculator(portfolio_total_df, date)
        
        performance = returns_calc.calculate_performance()
        
        risk_metrics = {
            'daily_volatility': RiskMetrics(portfolio_total_df).daily_volatility(),
            'annualized_volatility': RiskMetrics(portfolio_total_df).annualized_volatility(),
            'maximum_drawdown': RiskMetrics(portfolio_total_df).maximum_drawdown(),
            'daily_downside_volatility': RiskMetrics(portfolio_total_df).daily_downside_volatility(),
            'annualized_downside_volatility': RiskMetrics(portfolio_total_df).annualized_downside_volatility()
        }
        
        # Add ratios - use in-memory portfolio data
        try:
            risk_metrics_inst = RiskMetrics(portfolio_total_df)
            daily_sharpe, annualized_sharpe = risk_metrics_inst.sharpe_ratio(risk_free_rate)
            daily_sortino, annualized_sortino = risk_metrics_inst.sortino_ratio(risk_free_rate)
            market_comp = MarketComparison(portfolio_total_df, useSpy=False, risk_free_rate=risk_free_rate)
            daily_info, annualized_info = market_comp.information_ratio()
            
            ratios = {
                'daily_sharpe_ratio': daily_sharpe,
                'annualized_sharpe_ratio': annualized_sharpe,
                'daily_sortino_ratio': daily_sortino,
                'annualized_sortino_ratio': annualized_sortino,
                'daily_information_ratio': daily_info,
                'annualized_information_ratio': annualized_info
            }
        except Exception as e:
            logger.exception(f"Could not calculate ratios: {e}")
            ratios = {}
        
        # Add market comparison metrics - use in-memory portfolio data
        try:
            market_comp = market_comp if 'market_comp' in locals() else MarketComparison(portfolio_total_df, useSpy=False, risk_free_rate=risk_free_rate)
            beta = market_comp.beta()
            alpha = market_comp.alpha()
            risk_premium = market_comp.portfolio_risk_premium()
            
            market_metrics = {
                'beta': beta,
                'alpha': alpha,
                'risk_premium': risk_premium
            }
        except Exception as e:
            logger.exception(f"Could not calculate market metrics: {e}")
            market_metrics = {}
        
        return {
            'performance': performance,
            'risk_metrics': risk_metrics,
            'ratios': ratios,
            'market_metrics': market_metrics,
            'as_of_date': date
        }
    
    def get_cash_data(self, as_of_date: str = None) -> Dict[str, float]:
        """Get cash data for a specific date with CAD/USD breakdown from cash.csv"""
        return self._data_service.get_cash_data(as_of_date)
    
    def get_total_portfolio_value(self, as_of_date: str = None) -> float:
        """Get total portfolio value (including cash) for a specific date"""
        portfolio_total_df = self._data_service.get_portfolio_total_data()
        
        if portfolio_total_df.empty:
            return 0.0
        
        if as_of_date is None:
            as_of_date = portfolio_total_df['Date'].max()
        else:
            as_of_date = pd.to_datetime(as_of_date)
        
        # Get data for the specific date
        portfolio_data = portfolio_total_df[portfolio_total_df['Date'] == as_of_date]
        if len(portfolio_data) == 0:
            # Use latest available data
            portfolio_data = portfolio_total_df.iloc[-1:]
        
        return portfolio_data.iloc[0]['Total_Portfolio_Value']
    
    def get_portfolio_total_data(self) -> pd.DataFrame:
        """Get portfolio total data DataFrame"""
        return self._data_service.get_portfolio_total_data()
    
    def get_dividend_data(self) -> pd.DataFrame:
        """Get dividend data DataFrame"""
        return self._data_service.get_dividend_data()
    
    def clear_cache(self):
        """Clear data cache"""
        self._data_service.clear_cache()
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache information"""
        return self._data_service.get_cache_info()
    
    def get_cumulative_returns(self) -> pd.DataFrame:
        """Get cumulative return since inception as a percentage series (Date, Cumulative_Return_Pct)."""
        portfolio_total_df = self._data_service.get_portfolio_total_data()
        if portfolio_total_df.empty:
            return pd.DataFrame(columns=['Date', 'Cumulative_Return_Pct', 'Benchmark_Cumulative_Return_Pct'])
        
        calc = ReturnsCalculator(portfolio_total_df)
        portfolio_returns = calc.cumulative_return_series()
        
        # Get Benchmark Returns
        try:
            # Direct read from benchmark output
            benchmark_path = os.path.join(self.data_directory, 'benchmark', 'output', 'portfolio_total.csv')
            if os.path.exists(benchmark_path):
                bench_df = pd.read_csv(benchmark_path)
                if not bench_df.empty and 'Date' in bench_df.columns and 'Total_Portfolio_Value' in bench_df.columns:
                    bench_df['Date'] = pd.to_datetime(bench_df['Date'])
                    
                    # Filter benchmark to match portfolio date range
                    start_date = portfolio_returns['Date'].min()
                    bench_df = bench_df[bench_df['Date'] >= start_date].copy()
                    bench_df = bench_df.sort_values('Date')
                    
                    if not bench_df.empty:
                        start_val = bench_df['Total_Portfolio_Value'].iloc[0]
                        if start_val > 0:
                            bench_df['Benchmark_Cumulative_Return_Pct'] = (bench_df['Total_Portfolio_Value'] / start_val - 1.0) * 100.0
                            
                            # Merge with portfolio returns
                            portfolio_returns = pd.merge(
                                portfolio_returns, 
                                bench_df[['Date', 'Benchmark_Cumulative_Return_Pct']], 
                                on='Date', 
                                how='left'
                            )
        except Exception as e:
            logger.warning(f"Could not load benchmark data: {e}")

        # Get SPY Returns
        try:
            start_date = portfolio_returns['Date'].min()
            end_date = portfolio_returns['Date'].max() + pd.Timedelta(days=1)
            
            # Download SPY data
            spy_data = yf.Ticker('SPY').history(start=start_date, end=end_date)
            
            if not spy_data.empty:
                # Reset index to get Date column and ensure timezone naive
                spy_data = spy_data.reset_index()
                spy_data['Date'] = pd.to_datetime(spy_data['Date']).dt.tz_localize(None)
                spy_data = spy_data.sort_values('Date')
                
                # Filter to ensure we align with portfolio dates
                spy_data = spy_data[spy_data['Date'] >= start_date]
                
                if not spy_data.empty:
                    start_price = spy_data['Close'].iloc[0]
                    if start_price > 0:
                        spy_data['SPY_Cumulative_Return_Pct'] = (spy_data['Close'] / start_price - 1.0) * 100.0
                        
                        # Merge with portfolio returns
                        portfolio_returns = pd.merge(
                            portfolio_returns, 
                            spy_data[['Date', 'SPY_Cumulative_Return_Pct']], 
                            on='Date', 
                            how='left'
                        )
        except Exception as e:
            logger.warning(f"Could not load SPY data: {e}")
            
        return portfolio_returns
