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
from typing import List, Dict, Optional, Any

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import models
from src.models.portfolio_csv_builder import Portfolio as CSVBuilderPortfolio

# Import performance modules
from .returns_calculator import ReturnsCalculator
from .risk_metrics import RiskMetrics
from .ratios import Ratios
from .market_comparison import MarketComparison
from .benchmark import Benchmark
from .data_service import DataService

# Import config
from src.config.securities_config import securities_config

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
        self._risk_metrics = RiskMetrics(self.output_folder)
        self._ratios = Ratios(self.output_folder)
        self._market_comparison = MarketComparison(self.output_folder)
        self._benchmark = Benchmark(self.output_folder)
    
    def get_available_portfolios(self) -> List[str]:
        """Get list of available portfolios"""
        if not os.path.exists(self.data_directory):
            return []
        
        return [
            folder for folder in os.listdir(self.data_directory)
            if os.path.isdir(os.path.join(self.data_directory, folder))
        ]
    
    def build_portfolio_data(self, start_date: str = '2022-05-01', 
                           end_date: str = None, 
                           starting_cash: float = 101644.99) -> None:
        """Build all portfolio CSV files using the CSV builder"""
        if end_date is None:
            end_date = (pd.Timestamp.now() + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Initialize the CSV builder
        csv_builder = CSVBuilderPortfolio(start_date, end_date, starting_cash, self.portfolio_name)
        
        # Run the complete data processing pipeline
        print(f"Building portfolio data for {self.portfolio_name}...")
        
        csv_builder.create_table_exchange_rates()
        csv_builder.load_trades()
        csv_builder.create_table_prices()
        csv_builder.create_table_holdings()
        csv_builder.create_table_cad_market_values()
        csv_builder.create_table_dividend_per_share()
        csv_builder.create_table_dividend_income()
        csv_builder.create_table_cash()
        
        # Clear cache after data rebuild
        self._data_service.clear_cache()
        
        print(f"Portfolio data build complete for {self.portfolio_name}")
        csv_builder.print_final_values()
    
    def get_portfolio_summary(self, as_of_date: str = None) -> Dict[str, Any]:
        """Get portfolio summary data"""
        try:
            holdings_df = self._data_service.get_holdings_data(as_of_date)
            
            if holdings_df.empty:
                raise ValueError(f"No holdings data found for portfolio {self.portfolio_name}. Please ensure the portfolio data has been built.")
        except Exception as e:
            raise ValueError(f"Error loading portfolio data for {self.portfolio_name}: {str(e)}")
        
        # Calculate summary metrics
        total_value = holdings_df['market_value'].sum()
        total_holdings = len(holdings_df)
        
        # Find largest position
        if total_holdings > 0:
            largest_position = holdings_df.iloc[0]  # Already sorted by market value
            largest_position_ticker = largest_position['ticker']
            largest_position_value = largest_position['market_value']
            largest_position_weight = (largest_position_value / total_value * 100) if total_value > 0 else 0
        else:
            largest_position_ticker = ""
            largest_position_value = 0
            largest_position_weight = 0
        
        return {
            'total_value': total_value,
            'total_holdings': total_holdings,
            'largest_position_ticker': largest_position_ticker,
            'largest_position_value': largest_position_value,
            'largest_position_weight': largest_position_weight,
            'as_of_date': pd.to_datetime(as_of_date) if as_of_date else pd.to_datetime(datetime.now())
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
            print(f"Warning: Date {date} not available in data, using latest available date")
            date = portfolio_total_df['Date'].max()
            returns_calc = ReturnsCalculator(portfolio_total_df, date)
        
        performance = returns_calc.calculate_performance()
        
        risk_metrics = {
            'daily_volatility': self._risk_metrics.daily_volatility(portfolio_total_df),
            'annualized_volatility': self._risk_metrics.annualized_volatility(portfolio_total_df),
            'maximum_drawdown': self._risk_metrics.maximum_drawdown(portfolio_total_df),
            'daily_downside_volatility': self._risk_metrics.daily_downside_volatility(portfolio_total_df),
            'annualized_downside_volatility': self._risk_metrics.annualized_downside_volatility(portfolio_total_df)
        }
        
        # Add ratios - pass portfolio data to avoid reading non-existent file
        try:
            daily_sharpe, annualized_sharpe = self._ratios.sharpe_ratio(risk_free_rate, portfolio_total_df)
            daily_sortino, annualized_sortino = self._ratios.sortino_ratio(risk_free_rate, portfolio_total_df)
            daily_info, annualized_info = self._ratios.information_ratio(portfolio_total_df)
            
            ratios = {
                'daily_sharpe_ratio': daily_sharpe,
                'annualized_sharpe_ratio': annualized_sharpe,
                'daily_sortino_ratio': daily_sortino,
                'annualized_sortino_ratio': annualized_sortino,
                'daily_information_ratio': daily_info,
                'annualized_information_ratio': annualized_info
            }
        except Exception as e:
            print(f"Warning: Could not calculate ratios: {e}")
            ratios = {}
        
        # Add market comparison metrics - pass portfolio data to avoid reading non-existent file
        try:
            beta = self._market_comparison.beta(portfolio_total_df)
            alpha = self._market_comparison.alpha(risk_free_rate, portfolio_total_df)
            risk_premium = self._market_comparison.portfolio_risk_premium(risk_free_rate, portfolio_total_df)
            
            market_metrics = {
                'beta': beta,
                'alpha': alpha,
                'risk_premium': risk_premium
            }
        except Exception as e:
            print(f"Warning: Could not calculate market metrics: {e}")
            market_metrics = {}
        
        return {
            'performance': performance,
            'risk_metrics': risk_metrics,
            'ratios': ratios,
            'market_metrics': market_metrics,
            'as_of_date': date
        }
    
    def get_cash_data(self, as_of_date: str = None) -> Dict[str, float]:
        """Get cash data for a specific date"""
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
