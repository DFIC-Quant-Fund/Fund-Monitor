from alembic import op
import pandas as pd
from app.services.performance.returns import ReturnCalculator

def upgrade():
    """Populate PerformanceMetrics table with historical data."""
    # Get the connection from the current migration context
    connection = op.get_bind()
    
    # Define portfolios and date ranges to populate
    portfolios_data = [
        {
            'portfolio': 'dfic_core',
            'start_date': '2024-01-01',
            'end_date': '2024-12-31'
        }
        # Add more portfolios here as needed
    ]
    
    for portfolio_config in portfolios_data:
        populate_portfolio_data(
            connection=connection,
            portfolio=portfolio_config['portfolio'],
            start_date=portfolio_config['start_date'],
            end_date=portfolio_config['end_date']
        )

def downgrade():
    """Remove all historical performance data."""
    op.execute("DELETE FROM PerformanceMetrics")

def populate_portfolio_data(connection, portfolio: str, start_date: str, end_date: str):
    """Populate historical performance metrics for a specific portfolio."""
    calculator = ReturnCalculator()
    
    # Get all trading dates in range
    dates_query = """
    SELECT trading_date FROM TradingCalendar 
    WHERE trading_date BETWEEN %s AND %s 
    ORDER BY trading_date
    """
    
    dates_df = pd.read_sql(dates_query, connection, params=(start_date, end_date))
    
    print(f"Populating data for {portfolio} from {start_date} to {end_date}")
    print(f"Found {len(dates_df)} trading days to process")
    
    success_count = 0
    error_count = 0
    
    for _, row in dates_df.iterrows():
        date = row['trading_date']
        
        try:
            returns = calculator.calculate_daily_returns(portfolio, str(date))
            
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
                    date, portfolio, returns.get('one_day_return', 0),
                    returns.get('one_week_return', 0), returns.get('one_month_return', 0),
                    returns.get('ytd_return', 0), returns.get('one_year_return', 0)
                )
                
                connection.execute(insert_query, values)
                success_count += 1
                
                # Progress indicator
                if success_count % 50 == 0:
                    print(f"Processed {success_count} records for {portfolio}")
                
        except Exception as e:
            error_count += 1
            print(f"Error calculating metrics for {portfolio} on {date}: {str(e)}")
            # Continue processing other dates even if one fails
            continue
    
    print(f"Completed {portfolio}: {success_count} successful, {error_count} errors") 