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

# Import config
from src.config.securities_config import securities_config

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
            holdings_df = self._data_service.get_holdings_data(as_of_date)
            
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
        
        # Find largest position
        if total_holdings > 0:
            largest_position = holdings_df.iloc[0]  # Already sorted by market value
            largest_position_ticker = largest_position['ticker']
            largest_position_value = largest_position['market_value']
            largest_position_weight = (largest_position_value / total_holdings_value * 100) if total_holdings_value > 0 else 0
        else:
            largest_position_ticker = ""
            largest_position_value = 0
            largest_position_weight = 0
        
        return {
            'total_holdings_value': total_holdings_value,
            'total_holdings': total_holdings,
            'largest_position_ticker': largest_position_ticker,
            'largest_position_value': largest_position_value,
            'largest_position_weight': largest_position_weight,
            'as_of_date': as_of_dt,
            'total_portfolio_value': total_portfolio_value,
            'total_cash_cad': total_cash_cad,
            'cad_holdings_mv': cad_holdings_mv,
            'usd_holdings_mv': usd_holdings_mv,
            'cad_cash': cad_cash,
            'usd_cash': usd_cash
        }
    
    def get_holdings_data(self, as_of_date: str = None) -> pd.DataFrame:
        """Get holdings data as DataFrame"""
        holdings_df = self._data_service.get_holdings_data(as_of_date)
        
        if holdings_df.empty:
            return pd.DataFrame()
        
        # Add sector, fund, and geography information
        holdings_df['sector'] = holdings_df['ticker'].apply(self._get_sector)
        holdings_df['fund'] = holdings_df['ticker'].apply(self._get_fund)
        holdings_df['geography'] = holdings_df['ticker'].apply(self._get_geography)
        
        # Calculate weights
        total_value = holdings_df['market_value'].sum()
        holdings_df['weight_percent'] = (holdings_df['market_value'] / total_value * 100) if total_value > 0 else 0
        
        return holdings_df
    
    def get_holdings_summary_data(self) -> pd.DataFrame:
        """Get per-ticker holdings summary data as DataFrame"""
        summary_df = self._data_service.get_holdings_summary()
        if summary_df.empty:
            return pd.DataFrame()
        
        # Add sector, fund, and geography information
        summary_df['sector'] = summary_df['ticker'].apply(self._get_sector)
        summary_df['fund'] = summary_df['ticker'].apply(self._get_fund)
        summary_df['geography'] = summary_df['ticker'].apply(self._get_geography)
        
        # Calculate weights
        total_value = float(summary_df['market_value'].sum()) if 'market_value' in summary_df.columns else 0.0
        summary_df['weight_percent'] = (summary_df['market_value'] / total_value * 100) if total_value > 0 else 0
        
        return summary_df
    
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
            market_comp = MarketComparison(portfolio_total_df, useSpy=True, risk_free_rate=risk_free_rate)
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
            market_comp = market_comp if 'market_comp' in locals() else MarketComparison(portfolio_total_df, useSpy=True, risk_free_rate=risk_free_rate)
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
    
    def _get_sector(self, ticker: str) -> str:
        """Get sector for ticker from config or fallback mapping"""
        security_info = securities_config.get_security_info(ticker)
        if security_info:
            return security_info.sector.value
        
        # Fallback mapping
        fallback_mapping = {
            'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology',
            'NVDA': 'Technology', 'AMAT': 'Technology', 'VEEV': 'Technology',
            'ISRG': 'Technology', 'MA': 'Financial Services', 'APO': 'Financial Services',
            'WFG.TO': 'Financial Services', 'TMUS': 'Communication Services',
            'EA': 'Communication Services', 'ACO-X.TO': 'Consumer Discretionary',
            'DOLE': 'Consumer Discretionary', 'AER': 'Energy', 'CEG': 'Energy',
            'CG': 'Energy', 'HBM.TO': 'Materials', 'MP': 'Materials',
            'L.TO': 'Industrials', 'WSC': 'Industrials', 'BLBD': 'Industrials',
            'GSL': 'Industrials', 'TEX': 'Industrials', 'CSH-UN.TO': 'Real Estate',
            'AGG': 'Fixed Income', 'SCHP': 'Fixed Income', 'TLT': 'Fixed Income',
            'XBB.TO': 'Fixed Income', 'SPSB': 'Fixed Income', 'SPY': 'Equity ETF',
            'XIU.TO': 'Equity ETF', 'AMSF': 'Insurance'
        }
        return fallback_mapping.get(ticker, 'Other')
    
    def _get_fund(self, ticker: str) -> str:
        """Get fund for ticker from config"""
        security_info = securities_config.get_security_info(ticker)
        if security_info:
            return security_info.fund.value
        return 'Other'
    
    def _get_geography(self, ticker: str) -> str:
        """Get geography from config or ticker-based logic"""
        security_info = securities_config.get_security_info(ticker)
        if security_info:
            return 'Canada' if security_info.geography.value == 'CAN' else 'US'
        
        # Fallback to ticker-based logic
        return 'Canada' if '.TO' in ticker else 'US'
