"""
Portfolio returns calculation module.

This module provides comprehensive portfolio return calculations.
It handles:
- Period returns (1-day, 1-week, 1-month, YTD, 1-year, inception)
- Total return calculations
- Daily and annualized average returns

The module is designed to work with either a DataFrame or CSV file input.
"""

import pandas as pd
from datetime import timedelta


class ReturnsCalculator:
    def __init__(self, portfolio_data=None, date=None, portfolio_column="Total_Portfolio_Value"):
        self.df = portfolio_data
        self.date = pd.to_datetime(date) if date else None
        self.portfolio_column = portfolio_column

    def valid_date(self):
        return self.date in self.df['Date'].values

    def _closest_date(self, target_date, side='left'):
        target_date = pd.to_datetime(target_date)
        valid_dates = self.df[self.df['Date'] <= target_date]['Date'] if side == 'left' else self.df[self.df['Date'] >= target_date]['Date']
        return valid_dates.max() if side == 'left' else valid_dates.min()

    def _get_value_by_date(self, date):
        row = self.df[self.df['Date'] == date]
        return row[self.portfolio_column].values[0] if not row.empty else None

    def calculate_performance(self):
        periods = {
            "one_day": self.date - timedelta(days=1),
            "one_week": self.date - timedelta(days=7),
            "one_month": self.date - timedelta(days=30),
            "qtd": self.date.replace(month=self.date.month - ((self.date.month - 1) % 3), day=1),
            "ytd": pd.Timestamp(year=self.date.year, month=1, day=1),
            "one_year": self.date - timedelta(days=365),
            "inception": self.df['Date'].min()
        }

        performance = {}
        current_value = self._get_value_by_date(self.date)

        for key, period_date in periods.items():
            closest_date = self._closest_date(period_date, side='right' if key == 'ytd' else 'left')
            previous_value = self._get_value_by_date(closest_date)

            # Calculate return only if both values exist
            performance[key] = (current_value / previous_value - 1) * 100 if current_value and previous_value else None

        return performance

    def total_return(self):
        total_return = (self.df[self.portfolio_column].iloc[-1] - self.df[self.portfolio_column].iloc[0]) / self.df[self.portfolio_column].iloc[0]
        return total_return

    def daily_average_return(self):
        daily_returns = self.df['pct_change'].dropna()
        return daily_returns.mean()
    
    def annualized_average_return(self):
        daily_returns = self.df['pct_change'].dropna()
        average_daily_return = daily_returns.mean()
        return (1 + average_daily_return) ** 252 - 1 
    
    def annualized_return(self, as_of_date=None):
        """
        Calculate annualized return since inception.
        
        Args:
            as_of_date: Date to calculate as of (defaults to latest date in dataframe or self.date)
        
        Returns:
            Annualized return as a percentage (e.g., 10.5 for 10.5%)
        """
        if self.df is None or self.df.empty:
            return None
        
        df = self.df.copy()
        df = df.sort_values('Date').reset_index(drop=True)
        
        if self.portfolio_column not in df.columns:
            return None
        
        # Determine end date - normalize to date only (remove time component)
        if as_of_date is not None:
            end_date = pd.to_datetime(as_of_date).normalize()
        elif self.date is not None:
            end_date = pd.to_datetime(self.date).normalize()
        else:
            end_date = df['Date'].max()
        
        # Normalize all dates in dataframe for comparison
        df['Date'] = pd.to_datetime(df['Date']).dt.normalize()
        end_date = pd.to_datetime(end_date).normalize()
        
        # Get start date (inception)
        start_date = df['Date'].min()
        
        # Get start value
        start_value = df[self.portfolio_column].iloc[0]
        if start_value == 0 or pd.isna(start_value):
            return None
        
        # Find end value - try exact match first, then closest date <= end_date
        end_row = df[df['Date'] == end_date]
        if end_row.empty:
            # Fall back to closest date <= end_date
            end_row = df[df['Date'] <= end_date]
            if end_row.empty:
                return None
        
        end_value = end_row[self.portfolio_column].iloc[-1]
        actual_end_date = end_row['Date'].iloc[-1]
        
        if pd.isna(end_value):
            return None
        
        # Calculate total return
        total_return = (end_value / start_value) - 1.0
        
        # Calculate days held using actual end date found
        days_held = (actual_end_date - start_date).days
        if days_held <= 0:
            return None
        
        # Annualize: (1 + total_return) ^ (365 / days_held) - 1
        annualized_return = ((1.0 + total_return) ** (365.0 / days_held) - 1.0) * 100.0
        
        return annualized_return
    
    def cumulative_return_series(self) -> pd.DataFrame:
        """
        Compute cumulative return since inception as a percentage time series.
        Returns a DataFrame with columns: Date, Cumulative_Return_Pct
        """
        if self.df is None or self.df.empty:
            return pd.DataFrame(columns=['Date', 'Cumulative_Return_Pct'])
        
        df = self.df.copy()
        df = df.sort_values('Date').reset_index(drop=True)
        if self.portfolio_column not in df.columns:
            return pd.DataFrame(columns=['Date', 'Cumulative_Return_Pct'])
        
        starting_value = df[self.portfolio_column].iloc[0]
        if starting_value == 0 or pd.isna(starting_value):
            return pd.DataFrame(columns=['Date', 'Cumulative_Return_Pct'])
        
        df['Cumulative_Return_Pct'] = (df[self.portfolio_column] / starting_value - 1.0) * 100.0
        return df[['Date', 'Cumulative_Return_Pct']]


if __name__ == "__main__":
    import argparse
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(
        description="Run portfolio return calculations from a CSV file."
    )
    parser.add_argument(
        "csv_path",
        help="Path to CSV file with at least 'Date' and 'Total_Portfolio_Value' columns.",
    )
    parser.add_argument(
        "--date",
        help="As-of date in YYYY-MM-DD format (defaults to latest date in the file).",
        default=None,
    )
    parser.add_argument(
        "--portfolio-column",
        help="Name of the column containing portfolio values.",
        default="Total_Portfolio_Value",
    )

    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    if not csv_path.is_file():
        print(f"CSV file not found: {csv_path}")
        sys.exit(1)

    # Load data
    df = pd.read_csv(csv_path)
    if "Date" not in df.columns:
        print("CSV must contain a 'Date' column.")
        sys.exit(1)

    df["Date"] = pd.to_datetime(df["Date"])

    portfolio_col = args.portfolio_column
    if portfolio_col not in df.columns:
        print(f"CSV must contain a '{portfolio_col}' column.")
        sys.exit(1)

    # Ensure pct_change column exists for average-return methods
    if "pct_change" not in df.columns:
        df["pct_change"] = df[portfolio_col].pct_change()

    # Determine as-of date
    as_of_date = args.date if args.date else df["Date"].max()

    calc = ReturnsCalculator(
        portfolio_data=df,
        date=as_of_date,
        portfolio_column=portfolio_col,
    )

    print(f"Using data from: {csv_path}")
    print(f"As-of date: {pd.to_datetime(as_of_date).date()}")
    print()

    performance = calc.calculate_performance()
    print("Period performance (%):")
    for period, value in performance.items():
        if value is None:
            print(f"  {period:>10}: N/A")
        else:
            print(f"  {period:>10}: {value:8.3f}%")

    total_ret = calc.total_return()
    daily_avg = calc.daily_average_return()
    annualized_avg = calc.annualized_average_return()
    annualized = calc.annualized_return(as_of_date=as_of_date)

    print()
    print(f"Total return (since inception): {total_ret * 100:.3f}%")
    print(f"Average daily return:          {daily_avg * 100:.5f}%")
    print(f"Annualized avg daily return:   {annualized_avg * 100:.3f}%")
    if annualized is not None:
        print(f"Annualized return (CAGR):      {annualized:.3f}%")
    else:
        print("Annualized return (CAGR):      N/A")

    # Show last few rows of cumulative return series as a quick sanity check
    cum_df = calc.cumulative_return_series()
    if not cum_df.empty:
        print()
        print("Last 5 rows of cumulative return series (%):")
        print(cum_df.tail().to_string(index=False))