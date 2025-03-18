import pandas as pd
import os
import sys
from datetime import timedelta
import mysql.connector
from dotenv import load_dotenv

class Performance:
    def __init__(self, fund, date, portfolio_column="Total_Portfolio_Value"):
        """
        Initializes the Performance class with portfolio data for a specific fund.

        :param fund: The name of the fund (used to locate the data).
        :param date: The end date for performance calculation.
        :param portfolio_column: The column name representing portfolio value.
        """
        load_dotenv()

        self.fund = fund
        self.date = pd.to_datetime(date)
        self.portfolio_column = portfolio_column

        # File paths
        self.input_file = os.path.join('data', fund, 'output', 'portfolio_total.csv')
        self.output_file = os.path.join('data', fund, 'output', 'performance_returns.csv')

        # Validate file existence
        if not os.path.exists(self.input_file):
            sys.exit(f"Error: File not found at {self.input_file}")

        # Load and preprocess data
        self.df = pd.read_csv(self.input_file)
        self.df['Date'] = pd.to_datetime(self.df['Date'])

        # Ensure column exists
        if self.portfolio_column not in self.df.columns:
            sys.exit(f"Error: Column '{self.portfolio_column}' not found in dataset.")

    def valid_date(self):
        """
        Validate the end date provided by the user. It must be an available date in the dataset.

        :return: True if the date is valid, False otherwise.
        """
        return self.date in self.df['Date'].values

    def _closest_date(self, target_date, side='left'):
        """
        Finds the closest available date in the dataset.

        :param target_date: The target date to search for.
        :param side: 'left' to find the closest past date, 'right' for the closest future date.
        :return: The closest date found in the dataset.
        """
        target_date = pd.to_datetime(target_date)
        valid_dates = self.df[self.df['Date'] <= target_date]['Date'] if side == 'left' else self.df[self.df['Date'] >= target_date]['Date']
        return valid_dates.max() if side == 'left' else valid_dates.min()

    def _get_value_by_date(self, date):
        """
        Retrieves the portfolio value on a specific date.

        :param date: The date for which to fetch the portfolio value.
        :return: Portfolio value on the given date or None if unavailable.
        """
        row = self.df[self.df['Date'] == date]
        return row[self.portfolio_column].values[0] if not row.empty else None

    def calculate_performance(self):
        """
        Calculates portfolio performance over multiple periods.

        :return: A dictionary containing returns for different periods.
        """
        periods = {
            "one_day": self.date - timedelta(days=1),
            "one_week": self.date - timedelta(days=7),
            "one_month": self.date - timedelta(days=30),
            "ytd": pd.Timestamp(year=self.date.year, month=1, day=1),
            "one_year": self.date - timedelta(days=365),
            "inception": self.df['Date'].min()
        }

        performance = {}
        latest_value = self._get_value_by_date(self.date)

        for key, period_date in periods.items():
            closest_date = self._closest_date(period_date, side='right' if key == 'ytd' else 'left')
            previous_value = self._get_value_by_date(closest_date)

            # Calculate return only if both values exist
            performance[key] = (latest_value / previous_value - 1) * 100 if latest_value and previous_value else None

        return performance

    def save_results_to_csv(self, results):
        """
        Saves the performance results to a CSV file.

        :param results: Dictionary of performance returns.
        """
        date = self.date
        # Create a new dataframe to store the results
        results_df = pd.DataFrame([results], index=[date])
        results_df.index.name = "Date"

        # Read existing data if the file exists and append new data
        if os.path.exists(self.output_file):
            saved_df = pd.read_csv(self.output_file, index_col="Date")
            saved_df.index = pd.to_datetime(saved_df.index)
            results_df = pd.concat([saved_df, results_df])
        
        results_df = results_df[~results_df.index.duplicated(keep='last')]
        results_df = results_df.sort_index()

        # Save to CSV
        results_df.to_csv(self.output_file, mode='w', index=True, header=True)

    def save_results_to_db(self, results):
        """
        Saves the performance results to a database.

        :param results: Dictionary of performance returns.
        """
        # Prepare data for query
        date = self.date
        results['date'] = date.strftime("%Y-%m-%d")

        for key, value in results.items():
            if key != 'date':
                results[key] = float(value) if value else None 

        # Connect to database        
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOSTNAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            port=os.getenv('DB_PORT'),
            database="Fund"
        )

        cursor = conn.cursor(dictionary=True)

        # Insert or update data
        cursor.execute("INSERT INTO performance_returns (date, one_day_return, one_week_return, one_month_return, ytd_return, one_year_return, inception_return) VALUES (%s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE one_day_return=VALUES(one_day_return), one_week_return=VALUES(one_week_return), one_month_return=VALUES(one_month_return), ytd_return=VALUES(ytd_return), one_year_return=VALUES(one_year_return), inception_return=VALUES(inception_return)",
                          (results['date'], results['one_day'], results['one_week'], results['one_month'], results['ytd'], results['one_year'], results['inception']))
        
        conn.commit()
        conn.close()

if __name__ == '__main__':

    if len(sys.argv) < 2:
        sys.exit("Usage: python Performance.py <fund> <date> (date is optional, leave empty for historical run).")

    fund = sys.argv[1]
    date = sys.argv[2] if len(sys.argv) > 2 else None

    if date:
        dates = [date]
    else:
        dates = pd.read_csv(os.path.join('data', fund, 'output', 'portfolio_total.csv'))['Date']
    
    for date in dates:
        performance = Performance(fund, date)
        if not performance.valid_date():
            print(f"Skipping {fund} on {date}, portfolio_total.csv data not available.")
        else:
            print(f"Calculating performance for {fund} on {date}")
            results = performance.calculate_performance()
            performance.save_results_to_csv(results)
            performance.save_results_to_db(results)
