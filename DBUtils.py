import os
import pandas as pd
import mysql.connector
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

class DBConnection:
    def __init__(self):
        self.host = os.getenv('DB_HOSTNAME')
        self.user = os.getenv('DB_USER')
        self.password = os.getenv('DB_PASSWORD')
        self.port = os.getenv('DB_PORT')
        self.connection = None
        self.cursor = None

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                port=self.port
            )
            self.cursor = self.connection.cursor()
            
            # Create database if it doesn't exist
            self.cursor.execute("CREATE DATABASE IF NOT EXISTS Fund")
            self.connection.database = "Fund"
            
            return True
        except mysql.connector.Error as err:
            print(f"Error connecting to database: {err}")
            return False

    def create_performance_metrics_table(self):
        create_table_query = """
        CREATE TABLE IF NOT EXISTS PerformanceReturns (
            date DATE PRIMARY KEY,
            one_day_return DECIMAL(10, 4),
            one_week_return DECIMAL(10, 4),
            one_month_return DECIMAL(10, 4),
            ytd_return DECIMAL(10, 4),
            one_year_return DECIMAL(10, 4),
            inception_return DECIMAL(10, 4)
        )
        """
        try:
            self.cursor.execute(create_table_query)
            self.connection.commit()
            return True
        except mysql.connector.Error as err:
            print(f"Error creating table: {err}")
            return False

    def insert_performance_metrics(self, metrics_df):
        insert_query = """
        INSERT INTO PerformanceReturns (
            date,
            one_day_return,
            one_week_return,
            one_month_return,
            ytd_return,
            one_year_return,
            inception_return
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            one_day_return = VALUES(one_day_return),
            one_week_return = VALUES(one_week_return),
            one_month_return = VALUES(one_month_return),
            ytd_return = VALUES(ytd_return),
            one_year_return = VALUES(one_year_return),
            inception_return = VALUES(inception_return)
        """
        try:
            current_date = datetime.now().date()
            
            # Convert the metrics DataFrame to a dictionary for easier access
            metrics_dict = pd.Series(metrics_df.Value.values, index=metrics_df.Metric).to_dict()
            
            # Extract values and convert percentages to decimals
            values = [
                current_date,
                float(metrics_dict['1 Day Return'].strip('%')),
                float(metrics_dict['1 Week Return'].strip('%')),
                float(metrics_dict['1 Month Return'].strip('%')),
                float(metrics_dict['Year-to-Date Return'].strip('%')),
                float(metrics_dict['1 Year Return'].strip('%')),
                float(metrics_dict['Inception'].strip('%'))
            ]
            
            self.cursor.execute(insert_query, values)
            self.connection.commit()
            return True
        except (mysql.connector.Error, KeyError, ValueError) as err:
            print(f"Error inserting data: {err}")
            return False

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()

def main():
    # Read the CSV file
    try:
        metrics_df = pd.read_csv('data/fund/output/performance_metrics.csv')
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    # Initialize database connection
    db = DBConnection()
    
    if not db.connect():
        print("Failed to connect to database")
        return

    # Create table if it doesn't exist
    if not db.create_performance_metrics_table():
        print("Failed to create table")
        db.close()
        return

    # Insert the metrics
    if db.insert_performance_metrics(metrics_df):
        print("Successfully inserted performance metrics into database")
    else:
        print("Failed to insert performance metrics")

    # Close the database connection
    db.close()

if __name__ == "__main__":
    main()
