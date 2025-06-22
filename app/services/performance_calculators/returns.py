# app/services/performance/return_calculator.py
import pandas as pd
from typing import Dict, Optional
from app.services.performance_calculators.currency_attribution import get_db_connection

class ReturnCalculator:
    def __init__(self):
        self.conn = get_db_connection()
    
    def calculate_daily_returns(self, portfolio: str, date: str) -> Dict[str, float]:
        """Calculate various return metrics for a portfolio on a given date."""
        
        # Get portfolio holdings and prices
        holdings_query = """
        SELECT ticker, shares_held, price, market_value
        FROM MaterializedHoldings
        WHERE portfolio = %s AND trading_date = %s AND shares_held > 0
        """
        
        holdings_df = pd.read_sql(holdings_query, self.conn, params=(portfolio, date))
        
        if holdings_df.empty:
            return {}
        
        # Calculate different return periods
        returns = {
            'one_day_return': self._calculate_period_return(portfolio, date, days=1),
            'one_week_return': self._calculate_period_return(portfolio, date, days=7),
            'one_month_return': self._calculate_period_return(portfolio, date, days=30),
            'ytd_return': self._calculate_ytd_return(portfolio, date),
            'one_year_return': self._calculate_period_return(portfolio, date, days=365),
        }
        
        return returns
    
    def _calculate_period_return(self, portfolio: str, end_date: str, days: int) -> float:
        """Calculate return over a specific period."""
        # Get start and end portfolio values
        start_date_query = """
        SELECT trading_date FROM TradingCalendar 
        WHERE trading_date <= %s 
        ORDER BY trading_date DESC 
        LIMIT 1 OFFSET %s
        """
        
        start_date = pd.read_sql(start_date_query, self.conn, params=(end_date, days-1)).iloc[0, 0]
        
        # Calculate total portfolio values
        start_value = self._get_portfolio_value(portfolio, start_date)
        end_value = self._get_portfolio_value(portfolio, end_date)
        
        if start_value == 0:
            return 0.0
        
        return (end_value - start_value) / start_value
    
    def _get_portfolio_value(self, portfolio: str, date: str) -> float:
        """Get total portfolio value on a given date."""
        query = """
        SELECT SUM(total_market_value) 
        FROM MaterializedHoldings 
        WHERE portfolio = %s AND trading_date = %s
        """
        
        result = pd.read_sql(query, self.conn, params=(portfolio, date))
        return result.iloc[0, 0] or 0.0
    
    def _calculate_ytd_return(self, portfolio: str, date: str) -> float:
        """Calculate year-to-date return."""
        year_start = f"{date[:4]}-01-01"
        
        # Get portfolio values at year start and current date
        start_value = self._get_portfolio_value(portfolio, year_start)
        end_value = self._get_portfolio_value(portfolio, date)
        
        if start_value == 0:
            return 0.0
        
        return (end_value - start_value) / start_value