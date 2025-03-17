import os
import pandas as pd
from datetime import timedelta


class PortfolioPerformance:
    def __init__(self, output_folder):
        self.output_folder = output_folder
    
    def total_return(self):
        df = pd.read_csv(os.path.join(self.output_folder, 'portfolio_total.csv'))
        total_return = (df['Total_Portfolio_Value'].iloc[-1] - df['Total_Portfolio_Value'].iloc[0]) / df['Total_Portfolio_Value'].iloc[0]
        return total_return 

    def daily_average_return(self):
        df = pd.read_csv(os.path.join(self.output_folder, 'portfolio_total.csv'))
        daily_returns = df['pct_change'].dropna()
        average_return = daily_returns.mean()
        return average_return
    
    def annualized_average_return(self):
        df = pd.read_csv(os.path.join(self.output_folder, 'portfolio_total.csv'))
        daily_returns = df['pct_change'].dropna()
        average_daily_return = daily_returns.mean()
        annualized_avg_return = (1+average_daily_return) ** 252 - 1
        return annualized_avg_return
    
    def calculate_period_performance(self):
        df = pd.read_csv(os.path.join(self.output_folder, 'portfolio_total.csv'))
        df['Date'] = pd.to_datetime(df['Date'])

        latest_date = df['Date'].max()
        one_day = latest_date - timedelta(days=1)
        one_week = latest_date - timedelta(days=7)
        one_month = latest_date - timedelta(days=30)
        ytd = pd.Timestamp(year=latest_date.year, month=1, day=1)
        one_year = latest_date - timedelta(days=365)
        inception = df['Date'].min()

        def closest_date(target_date, side='left'):
            target_date = pd.to_datetime(target_date)
            if side == 'left':
                valid_dates = df[df['Date'] <= target_date]['Date']
                return valid_dates.max()
            elif side == 'right':
                valid_dates = df[df['Date'] >= target_date]['Date']
                return valid_dates.min()

        closest_1d = closest_date(one_day)
        closest_1w = closest_date(one_week)
        closest_1m = closest_date(one_month)
        closest_ytd = closest_date(ytd, side='right')
        closest_1y = closest_date(one_year)
        closest_inc = closest_date(inception)

        latest_value = df[df['Date'] == latest_date]['Total_Portfolio_Value'].values[0]
        one_day_value = df[df['Date'] == closest_1d]['Total_Portfolio_Value'].values[0]
        one_week_value = df[df['Date'] == closest_1w]['Total_Portfolio_Value'].values[0]
        one_month_value = df[df['Date'] == closest_1m]['Total_Portfolio_Value'].values[0]
        ytd_value = df[df['Date'] == closest_ytd]['Total_Portfolio_Value'].values[0]
        one_year_value = df[df['Date'] == closest_1y]['Total_Portfolio_Value'].values[0]
        inception_value = df[df['Date'] == closest_inc]['Total_Portfolio_Value'].values[0]

        one_day_return = (latest_value / one_day_value) - 1
        one_week_return = (latest_value / one_week_value) - 1
        one_month_return = (latest_value / one_month_value) - 1
        ytd_return = (latest_value / ytd_value) - 1
        one_year_return = (latest_value / one_year_value) - 1
        inception_return = (latest_value / inception_value) - 1

        return {
            "1d": one_day_return,
            "1w": one_week_return,
            "1m": one_month_return,
            "YTD": ytd_return,
            "1y": one_year_return,
            "Inception": inception_return
        }