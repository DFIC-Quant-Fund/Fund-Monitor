"""
Portfolio Controller - Main business logic orchestrator.

This controller handles all portfolio operations including:
- Loading portfolio data
- Calculating performance metrics
- Managing data building operations
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
from .data_processor import DataProcessor

# Import config
from src.config.securities_config import securities_config

class PortfolioController:
    """Main controller for portfolio operations"""
    
    def __init__(self, portfolio_name: str, data_directory: str = "data"):
        self.portfolio_name = portfolio_name
        self.data_directory = data_directory
        self.output_folder = os.path.join(data_directory, portfolio_name, "output")
        self.input_folder = os.path.join(data_directory, portfolio_name, "input")
        
        # Initialize performance calculators
        self._data_processor = DataProcessor(self.output_folder)
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
        
        # Aggregate data for performance analysis
        self._aggregate_portfolio_data()
        
        print(f"Portfolio data build complete for {self.portfolio_name}")
        csv_builder.print_final_values()
    
    def _aggregate_portfolio_data(self) -> None:
        """Aggregate market values, cash, and dividends into portfolio_total.csv"""
        market_values_file = os.path.join(self.output_folder, 'market_values.csv')
        cash_file = os.path.join(self.output_folder, 'cash.csv')
        dividends_file = os.path.join(self.output_folder, 'dividend_income.csv')
        output_file = os.path.join(self.output_folder, 'portfolio_total.csv')
        
        self._data_processor.aggregate_data(market_values_file, cash_file, dividends_file, output_file)
    
    def get_portfolio_summary(self, as_of_date: str = None) -> Dict[str, Any]:
        """Get portfolio summary data"""
        # Load the data files
        holdings_df = self._load_csv_file('holdings.csv')
        market_values_df = self._load_csv_file('market_values.csv')
        
        if holdings_df.empty or market_values_df.empty:
            raise ValueError(f"Required data files not found for portfolio {self.portfolio_name}")
        
        # Determine the date to use
        if as_of_date is None:
            as_of_date = holdings_df['Date'].max()
        else:
            as_of_date = pd.to_datetime(as_of_date)
        
        # Get data for the specific date
        holdings_data = holdings_df[holdings_df['Date'] == as_of_date].iloc[0] if len(holdings_df[holdings_df['Date'] == as_of_date]) > 0 else holdings_df.iloc[-1]
        market_values_data = market_values_df[market_values_df['Date'] == as_of_date].iloc[0] if len(market_values_df[market_values_df['Date'] == as_of_date]) > 0 else market_values_df.iloc[-1]
        
        # Calculate summary metrics
        total_value = sum(market_values_data[ticker] for ticker in holdings_data.index if ticker != 'Date' and holdings_data[ticker] > 0)
        total_holdings = sum(1 for ticker in holdings_data.index if ticker != 'Date' and holdings_data[ticker] > 0)
        
        # Find largest position
        largest_position = max(
            ((ticker, market_values_data[ticker]) 
            for ticker in holdings_data.index 
            if ticker != 'Date' and holdings_data[ticker] > 0),
            key=lambda x: x[1]
        ) if total_holdings > 0 else ("", 0)
        
        # Ensure as_of_date is a datetime object
        if isinstance(as_of_date, str):
            as_of_date = pd.to_datetime(as_of_date)
        
        return {
            'total_value': total_value,
            'total_holdings': total_holdings,
            'largest_position_ticker': largest_position[0],
            'largest_position_value': largest_position[1],
            'largest_position_weight': (largest_position[1] / total_value * 100) if total_value > 0 else 0,
            'as_of_date': as_of_date
        }
    
    def get_holdings_data(self, as_of_date: str = None) -> pd.DataFrame:
        """Get holdings data as DataFrame"""
        holdings_df = self._load_csv_file('holdings.csv')
        market_values_df = self._load_csv_file('market_values.csv')
        prices_df = self._load_csv_file('prices.csv')
        
        if holdings_df.empty or market_values_df.empty or prices_df.empty:
            raise ValueError(f"Required data files not found for portfolio {self.portfolio_name}")
        
        # Determine the date to use
        if as_of_date is None:
            as_of_date = holdings_df['Date'].max()
        else:
            as_of_date = pd.to_datetime(as_of_date)
        
        # Get data for the specific date
        holdings_data = holdings_df[holdings_df['Date'] == as_of_date].iloc[0] if len(holdings_df[holdings_df['Date'] == as_of_date]) > 0 else holdings_df.iloc[-1]
        market_values_data = market_values_df[market_values_df['Date'] == as_of_date].iloc[0] if len(market_values_df[market_values_df['Date'] == as_of_date]) > 0 else market_values_df.iloc[-1]
        prices_data = prices_df[prices_df['Date'] == as_of_date].iloc[0] if len(prices_df[prices_df['Date'] == as_of_date]) > 0 else prices_df.iloc[-1]
        
        # Create holdings DataFrame
        holdings_list = []
        total_value = 0
        
        for ticker in holdings_data.index:
            if ticker == 'Date':
                continue
                
            shares = holdings_data[ticker]
            if shares > 0:  # Only include non-zero positions
                market_value = market_values_data[ticker]
                price = prices_data[ticker]
                total_value += market_value
                
                holdings_list.append({
                    'ticker': ticker,
                    'shares': shares,
                    'price': price,
                    'market_value': market_value,
                    'sector': self._get_sector(ticker),
                    'fund': self._get_fund(ticker),
                    'geography': self._get_geography(ticker)
                })
        
        # Calculate weights
        for holding in holdings_list:
            holding['weight_percent'] = (holding['market_value'] / total_value * 100) if total_value > 0 else 0
        
        # Sort by market value
        holdings_list.sort(key=lambda h: h['market_value'], reverse=True)
        
        return pd.DataFrame(holdings_list)
    
    def get_performance_metrics(self, date: str = None, risk_free_rate: float = 0.02) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        portfolio_total_file = os.path.join(self.output_folder, 'portfolio_total.csv')
        
        if not os.path.exists(portfolio_total_file):
            raise FileNotFoundError(f"Portfolio total file not found: {portfolio_total_file}")
        
        df = pd.read_csv(portfolio_total_file)
        df['Date'] = pd.to_datetime(df['Date'])
        
        if date is None:
            date = df['Date'].max()
        else:
            date = pd.to_datetime(date)
        
        # Calculate returns for different periods
        returns_calc = ReturnsCalculator(df, date)
        if not returns_calc.valid_date():
            print(f"Warning: Date {date} not available in data, using latest available date")
            date = df['Date'].max()
            returns_calc = ReturnsCalculator(df, date)
        
        performance = returns_calc.calculate_performance()
        
        # Add risk metrics
        risk_metrics = {
            'daily_volatility': self._risk_metrics.daily_volatility(),
            'annualized_volatility': self._risk_metrics.annualized_volatility(),
            'maximum_drawdown': self._risk_metrics.maximum_drawdown(),
            'daily_downside_volatility': self._risk_metrics.daily_downside_volatility(),
            'annualized_downside_volatility': self._risk_metrics.annualized_downside_volatility()
        }
        
        # Add ratios
        try:
            daily_sharpe, annualized_sharpe = self._ratios.sharpe_ratio(risk_free_rate)
            daily_sortino, annualized_sortino = self._ratios.sortino_ratio(risk_free_rate)
            daily_info, annualized_info = self._ratios.information_ratio()
            
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
        
        # Add market comparison metrics
        try:
            beta = self._market_comparison.beta()
            alpha = self._market_comparison.alpha(risk_free_rate)
            risk_premium = self._market_comparison.portfolio_risk_premium(risk_free_rate)
            
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
        cash_df = self._load_csv_file('cash.csv')
        
        if cash_df.empty:
            return {'CAD_Cash': 0.0, 'USD_Cash': 0.0, 'Total_CAD': 0.0}
        
        # Determine the date to use
        if as_of_date is None:
            as_of_date = cash_df['Date'].max()
        else:
            as_of_date = pd.to_datetime(as_of_date)
        
        # Get data for the specific date
        cash_data = cash_df[cash_df['Date'] == as_of_date].iloc[0] if len(cash_df[cash_df['Date'] == as_of_date]) > 0 else cash_df.iloc[-1]
        
        return {
            'CAD_Cash': cash_data['CAD_Cash'],
            'USD_Cash': cash_data['USD_Cash'],
            'Total_CAD': cash_data['Total_CAD']
        }
    
    def get_total_portfolio_value(self, as_of_date: str = None) -> float:
        """Get total portfolio value (including cash) for a specific date"""
        portfolio_total_df = self._load_csv_file('portfolio_total.csv')
        
        if portfolio_total_df.empty:
            return 0.0
        
        # Determine the date to use
        if as_of_date is None:
            as_of_date = portfolio_total_df['Date'].max()
        else:
            as_of_date = pd.to_datetime(as_of_date)
        
        # Get data for the specific date
        portfolio_data = portfolio_total_df[portfolio_total_df['Date'] == as_of_date].iloc[0] if len(portfolio_total_df[portfolio_total_df['Date'] == as_of_date]) > 0 else portfolio_total_df.iloc[-1]
        
        return portfolio_data['Total_Portfolio_Value']
    
    def _load_csv_file(self, filename: str) -> pd.DataFrame:
        """Load a CSV file from the output folder"""
        file_path = os.path.join(self.output_folder, filename)
        try:
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                # Convert Date column to datetime if it exists
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                return df
            else:
                print(f"File not found: {file_path}")
                return pd.DataFrame()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return pd.DataFrame()
    
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
