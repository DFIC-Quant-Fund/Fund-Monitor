import os
import pandas as pd
from datetime import timedelta
import yfinance as yf


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
    
    def get_fixed_income_info(self, tickers: list):
        df = pd.read_csv(os.path.join(self.output_folder, 'market_values.csv'))
        df_xrates = pd.read_csv(os.path.join(self.output_folder, 'exchange_rates.csv'))

        usd_tickers = []

        for t in tickers:
            try:
                currency = yf.Ticker(t).info['currency']
            except:
                currency = 'CAD'

            if currency == 'USD':
                df[t] = df[t] * df_xrates['USD'].iloc[-1]
                usd_tickers.append(t)

        current_mkt_vals = {ticker: df[ticker].iloc[-1] for ticker in tickers}
        total_mkt_vals = sum(current_mkt_vals.values())
        fi_mkt_shares = {ticker: current_mkt_vals[ticker] / total_mkt_vals for ticker in tickers}

        usd_total_mkt_val = sum([current_mkt_vals[ticker] for ticker in usd_tickers])
        usd_fi_mkt_shares = {ticker: current_mkt_vals[ticker] / usd_total_mkt_val for ticker in usd_tickers}

        # combine all these dictionaries into a dataframe
        data = {
            'Ticker': tickers,
            'Market Value': [current_mkt_vals[ticker] for ticker in tickers],
            'Total Market Share': [fi_mkt_shares[ticker] for ticker in tickers],
            'USD Market Share': [usd_fi_mkt_shares[ticker] if ticker in usd_tickers else 0 for ticker in tickers]
        }

        data = pd.DataFrame(data)
        data.set_index('Ticker', inplace=True)

        return data