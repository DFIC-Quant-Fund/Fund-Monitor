#!/usr/bin/env python3
"""
Daily script to update performance metrics for the most recent trading day.
This can be run manually or scheduled via cron/Task Scheduler.
"""

from datetime import datetime, timedelta
import pandas as pd
from app.services.performance_calculators.returns import ReturnCalculator
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Get database connection."""
    return mysql.connector.connect(
        host=os.getenv('DB_HOSTNAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT'),
        database="Fund"
    )

def get_latest_trading_day(connection) -> str:
    """Get the most recent trading day."""
    query = """
    SELECT MAX(trading_date) FROM TradingCalendar 
    WHERE trading_date <= CURDATE()
    """
    
    result = pd.read_sql(query, connection)
    latest_date = result.iloc[0, 0]
    
    if not latest_date:
        raise ValueError("No trading dates found")
    
    return str(latest_date)

def update_daily_metrics(portfolio: str):
    """Update performance metrics for the most recent trading day."""
    connection = get_db_connection()
    cursor = connection.cursor()
    
    try:
        latest_date = get_latest_trading_day(connection)
        print(f"Calculating metrics for {portfolio} on {latest_date}")
        
        # Check if data already exists for this date
        check_query = """
        SELECT COUNT(*) FROM PerformanceMetrics 
        WHERE portfolio = %s AND date = %s
        """
        cursor.execute(check_query, (portfolio, latest_date))
        existing_count = cursor.fetchone()[0]
        
        if existing_count > 0:
            print(f"Metrics already exist for {portfolio} on {latest_date}. Updating...")
        
        # Calculate metrics
        calculator = ReturnCalculator()
        returns = calculator.calculate_daily_returns(portfolio, latest_date)
        
        if returns:
            insert_query = """
            INSERT INTO PerformanceMetrics 
            (date, portfolio, one_day_return, one_week_return, one_month_return, ytd_return, one_year_return)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            one_day_return = VALUES(one_day_return),
            one_week_return = VALUES(one_week_return),
            one_month_return = VALUES(one_month_return),
            ytd_return = VALUES(ytd_return),
            one_year_return = VALUES(one_year_return)
            """
            
            values = (
                latest_date, portfolio, returns.get('one_day_return', 0),
                returns.get('one_week_return', 0), returns.get('one_month_return', 0),
                returns.get('ytd_return', 0), returns.get('one_year_return', 0)
            )
            
            cursor.execute(insert_query, values)
            connection.commit()
            print(f"Successfully updated metrics for {portfolio}")
            
            # Print summary
            print(f"Returns for {portfolio} on {latest_date}:")
            for period, value in returns.items():
                print(f"  {period}: {value:.4%}")
        else:
            print(f"No data available for {portfolio} on {latest_date}")
            
    except Exception as e:
        print(f"Error updating metrics for {portfolio}: {str(e)}")
        connection.rollback()
    finally:
        cursor.close()
        connection.close()

def main():
    """Main function to update all portfolios."""
    portfolios = ['dfic_core']  # Add more portfolios as needed
    
    print(f"Starting daily performance metrics update at {datetime.now()}")
    
    for portfolio in portfolios:
        try:
            update_daily_metrics(portfolio)
        except Exception as e:
            print(f"Failed to update {portfolio}: {str(e)}")
    
    print(f"Daily update completed at {datetime.now()}")

if __name__ == "__main__":
    main() 