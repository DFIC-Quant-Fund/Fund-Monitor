import os
import pandas as pd
import sys
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import timedelta
from performance import DataProcessor, Benchmark, PortfolioPerformance


# def aggregate_data_old(input_file, output_file):
#     df = pd.read_csv(input_file)
#     df['Date'] = pd.to_datetime(df['Date'])
#     df = df.replace('', 0)
#     numeric_columns = df.columns.drop('Date')
#     df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors='coerce')

#     df['Total_Portfolio_Value'] = df[numeric_columns].sum(axis=1)
#     df_filtered = df[df['Total_Portfolio_Value'] > 0]
#     output_df = df_filtered[['Date', 'Total_Portfolio_Value']].copy()
#     output_df = output_df.sort_values('Date')
#     output_df['pct_change'] = output_df['Total_Portfolio_Value'].pct_change()

#     output_df.to_csv(output_file, index=False, float_format='%.6f')

#     print(output_df.head())


class RiskMetrics:
    def __init__(self):
        pass

    def daily_variance(self):
        df = pd.read_csv(os.path.join(output_folder, 'portfolio_total.csv'))
        daily_returns = df['pct_change'].dropna()
        daily_variance = daily_returns.var()

        return daily_variance

    def annualized_variance(self):
        df = pd.read_csv(os.path.join(output_folder, 'portfolio_total.csv'))
        annualized_variance = self.daily_variance() * 252
        # print(f"Annualized Variance: {annualized_variance:.4f}")
        return annualized_variance

    def annualized_volatility(self):
        annualized_volatility = self.annualized_variance() ** 0.5
        # print(f"Annualized Volatility: {annualized_volatility:.4f}")
        return annualized_volatility

    def daily_volatility(self):
        df = pd.read_csv(os.path.join(output_folder, 'portfolio_total.csv'))
        # daily_return = df['Total_Portfolio_Value'].pct_change()
        daily_return = df['pct_change'].dropna()
        daily_volatility = daily_return.std()

        # print(f"Daily Volatility: {daily_volatility:.4f}")
        return daily_volatility

    def daily_downside_variance(self):
        df = pd.read_csv(os.path.join(output_folder, 'portfolio_total.csv'))
        daily_return = df['pct_change'].dropna()
        downside_returns = daily_return[daily_return < 0]
        downside_variance = downside_returns.var()
        # print(f"Daily Downside Variance: {downside_variance:.4f}")
        return downside_variance

    def annualized_downside_variance(self):
        annualized_downside_variance = self.daily_downside_variance() * 252
        # print(f"Annualized Downside Variance: {annualized_downside_variance:.4f}")
        return annualized_downside_variance

    def daily_downside_volatility(self):
        daily_downside_volatility = self.daily_downside_variance() ** 0.5
        # print(f"Daily Downside Volatility: {daily_downside_volatility:.4f}")
        return daily_downside_volatility

    def annualized_downside_volatility(self):
        annualized_downside_volatility = self.annualized_downside_variance() ** 0.5
        # print(f"Annualized Downside Volatility: {annualized_downside_volatility:.4f}")
        return annualized_downside_volatility

    def maximum_drawdown(self):
        # calculate the maximum drawdown
        df = pd.read_csv(os.path.join(output_folder, 'portfolio_total.csv'))
        daily_return = df['pct_change'].dropna()
        
        return daily_return.min()

# def daily_compounded_return():
#     df = pd.read_csv('output/portfolio_total.csv')
#     daily_changes = df['pct_change']
#     daily_compounded_return = (1 + daily_changes).prod() - 1

#     return daily_compounded_return

# def annualized_compounded_return():
#     annualized_return = (1 + daily_compounded_return())**252 - 1

#     return annualized_return

class Ratios:
    def __init__(self):
        pass

    def sharpe_ratio(self, risk_free_rate):
        df = pd.read_csv(os.path.join(output_folder, 'portfolio_total.csv'))
        daily_return = df['pct_change'].dropna()
        daily_sharpe_ratio = (daily_return.mean() - risk_free_rate/252) / daily_return.std()
        annualized_sharpe_ratio = daily_sharpe_ratio * (252 ** 0.5)

        return daily_sharpe_ratio, annualized_sharpe_ratio

    def sortino_ratio(self, risk_free_rate):
        df = pd.read_csv(os.path.join(output_folder, 'portfolio_total.csv'))
        daily_return = df['pct_change'].dropna()
        downside_returns = daily_return[daily_return < 0]
        daily_sortino_ratio = (daily_return.mean() - risk_free_rate/252) / downside_returns.std()
        annualized_sortino_ratio = daily_sortino_ratio * (252 ** 0.5)

        return daily_sortino_ratio, annualized_sortino_ratio
    
    def treynor_ratio(self, risk_free_return):
        market_comparison = MarketComparison()
        return market_comparison.portfolio_risk_premium(risk_free_return) / market_comparison.beta()

    def information_ratio(self, benchmark='custom'):
        # df = pd.read_csv('output/portfolio_total.csv')
        # daily_portfolio_return = df['pct_change'].dropna()
        # daily_benchmark_return = benchmark_df['pct_change'].dropna()
        benchmark_class = Benchmark(output_folder)
        _, annual_benchmark_return = benchmark_class.benchmark_average_return(benchmark)
        portfolio_performance = PortfolioPerformance(output_folder)
        # excess_returns = daily_portfolio_return - daily_benchmark_return
        excess_returns = portfolio_performance.annualized_average_return() - annual_benchmark_return
        # print("annualized_average_return of portfolio: ", annualized_average_return())
        # print("annual_benchmark_return: ", annual_benchmark_return)

        tracking_error = excess_returns.std() # this doesn't make sense rn since they're just scalars
        information_ratio = excess_returns.mean() / tracking_error

        return information_ratio

class MarketComparison:
    def __init__(self):
        pass

    def beta(self, benchmark='custom'):
        benchmark_class = Benchmark(output_folder)
        if benchmark == 'custom':
            benchmark_df = pd.read_csv(os.path.join(output_folder, 'custom_benchmark.csv'))
        else:
            benchmark_df = benchmark_class.get_spy_benchmark()
        
        df = pd.read_csv(os.path.join(output_folder, 'portfolio_total.csv'))
        daily_portfolio_return = df['pct_change'].dropna()
        daily_benchmark_var, _ = benchmark_class.benchmark_variance(benchmark)
        covariance = daily_portfolio_return.cov(benchmark_df['pct_change'])
        beta = covariance / daily_benchmark_var

        return beta
        

    def alpha(self, risk_free_rate, benchmark='custom'): 
        benchmark_class = Benchmark(output_folder)
        annual_benchmark_return = benchmark_class.benchmark_average_return(benchmark)[1]
        portfolio_performance = PortfolioPerformance(output_folder)
        print("benchmark: ", benchmark)
        print("annual_benchmark_return ", annual_benchmark_return)
        alpha = (portfolio_performance.annualized_average_return() - risk_free_rate) - self.beta() * (annual_benchmark_return - risk_free_rate)

        return alpha
        
    def portfolio_risk_premium(self, risk_free_return):
        portfolio_performance = PortfolioPerformance(output_folder)
        return portfolio_performance.annualized_average_return() - risk_free_return

    def risk_adjusted_return(self, risk_free_return):
        risk_metrics = RiskMetrics()
        benchmark = Benchmark(output_folder)
        benchmark_vol = benchmark.benchmark_volatility()[1]
        portfolio_volatility = risk_metrics.annualized_volatility()
        portfolio_risk_prem = self.portfolio_risk_premium(risk_free_return)
        risk_adjusted_return = portfolio_risk_prem * benchmark_vol / portfolio_volatility + risk_free_return
        
        return risk_adjusted_return



def main():
    market_values_file = os.path.join(output_folder, "market_values.csv")
    cash_file = os.path.join(output_folder, "cash.csv") 
    dividend_file = os.path.join(output_folder, "dividend_values.csv") 
    output_file = os.path.join(output_folder, "portfolio_total.csv") 
    THREE_MTH_TREASURY_RATE = 0.0436 # 3-month treasury rate
    FIVE_PERCENT = 0.05

    data_processor = DataProcessor(output_folder)
    benchmark = Benchmark(output_folder)
    portfolio_performance = PortfolioPerformance(output_folder)
    risk_metrics = RiskMetrics()
    ratios = Ratios()
    market_comparison = MarketComparison()

    # run these once only after running portfolio.py once
    data_processor.aggregate_data(market_values_file, cash_file, dividend_file, output_file)
    benchmark.create_custom_benchmark()
    period_metrics = portfolio_performance.calculate_period_performance()

    print(f"Total Return including dividends,{portfolio_performance.total_return()*100:.2f}%\n")
    print(f"Daily Average Return,{portfolio_performance.daily_average_return()*100:.4f}%\n")
    print(f"Annualized Average Return,{portfolio_performance.annualized_average_return()*100:.2f}%\n")
    print(f"Daily Variance,{risk_metrics.daily_variance()*100:.4f}%\n")
    print(f"Annualized Variance,{risk_metrics.annualized_variance()*100:.2f}%\n")
    print(f"Daily Volatility,{risk_metrics.daily_volatility()*100:.4f}%\n")
    print(f"Annualized Volatility,{risk_metrics.annualized_volatility()*100:.2f}%\n")
    print(f"Daily Downside Variance,{risk_metrics.daily_downside_variance()*100:.4f}%\n")
    print(f"Annualized Downside Variance,{risk_metrics.annualized_downside_variance()*100:.2f}%\n")
    print(f"Daily Downside Volatility,{risk_metrics.daily_downside_volatility()*100:.4f}%\n")
    print(f"Annualized Downside Volatility,{risk_metrics.annualized_downside_volatility()*100:.2f}%\n")
    print(f"Sharpe Ratio (Annualized),{ratios.sharpe_ratio(THREE_MTH_TREASURY_RATE)[1]:.2f}\n")
    print(f"Sortino Ratio (Annualized),{ratios.sortino_ratio(THREE_MTH_TREASURY_RATE)[1]:.2f}\n")
    print(f"Maximum Drawdown,{risk_metrics.maximum_drawdown()*100:.2f}%\n")

    print(f"Custom Benchmark Variance (Daily),{benchmark.benchmark_variance()[0]*100:.4f}%\n")
    print(f"SPY Benchmark Variance (Daily),{benchmark.benchmark_variance(benchmark='SPY')[0]*100:.4f}%\n")
    print(f"Custom Benchmark Variance (Annualized),{benchmark.benchmark_variance()[1]*100:.2f}%\n")
    print(f"SPY Benchmark Variance (Annualized),{benchmark.benchmark_variance(benchmark='SPY')[1]*100:.2f}%\n")

    print(f"Custom Benchmark Volatility (Daily),{benchmark.benchmark_volatility()[0]*100:.4f}%\n")
    print(f"SPY Benchmark Volatility (Daily),{benchmark.benchmark_volatility(benchmark='SPY')[0]*100:.4f}%\n")
    print(f"Custom Benchmark Volatility (Annualized),{benchmark.benchmark_volatility()[1]*100:.2f}%\n")
    print(f"SPY Benchmark Volatility (Annualized),{benchmark.benchmark_volatility(benchmark='SPY')[1]*100:.2f}%\n")

    print(f"Custom Benchmark Average Return (Daily),{benchmark.benchmark_average_return()[0]*100:.4f}%\n")
    print(f"SPY Benchmark Average Return (Daily),{benchmark.benchmark_average_return(benchmark='SPY')[0]*100:.4f}%\n")
    print(f"Custom Benchmark Average Return (Annualized),{benchmark.benchmark_average_return()[1]*100:.2f}%\n")
    print(f"SPY Benchmark Average Return (Annualized),{benchmark.benchmark_average_return(benchmark='SPY')[1]*100:.2f}%\n")

    print(f"Portfolio Beta,{market_comparison.beta():.4f}\n")
    print(f"Portfolio Alpha against custom benchmark,{100*market_comparison.alpha(THREE_MTH_TREASURY_RATE):.4f}%\n")
    print(f"Portfolio Alpha against SPY benchmark,{100*market_comparison.alpha(THREE_MTH_TREASURY_RATE, benchmark='SPY'):.4f}%\n")

    print(f"Portfolio Risk Premium,{market_comparison.portfolio_risk_premium(THREE_MTH_TREASURY_RATE)*100:.2f}%\n")
    print(f"Risk Adjusted Return (three month treasury rate),{market_comparison.risk_adjusted_return(THREE_MTH_TREASURY_RATE)*100:.2f}%\n")
    print(f"Treynor Ratio (three month treasury rate),{ratios.treynor_ratio(THREE_MTH_TREASURY_RATE):.2f}\n")
    # print(f"Information Ratio (Custom Benchmark),{information_ratio():.2f}\n")
    print("--- Portfolio Returns ---\n")
    print(f"1 Day Return,{period_metrics['1d'] * 100:.2f}%\n")
    print(f"1 Week Return,{period_metrics['1w'] * 100:.2f}%\n")
    print(f"1 Month Return,{period_metrics['1m'] * 100:.2f}%\n")
    print(f"Year-to-Date Return,{period_metrics['YTD'] * 100:.2f}%\n")
    print(f"1 Year Return,{period_metrics['1y'] * 100:.2f}%\n")
    print(f"Inception,{period_metrics['Inception'] * 100:.2f}%\n")

    # output all these calculations to a csv file
    with open(os.path.join(output_folder, 'performance_metrics.csv'), 'w') as f:
        f.write("Metric,Value\n")
        f.write(f"Total Return including dividends,{portfolio_performance.total_return()*100:.2f}%\n")
        f.write(f"Daily Average Return,{portfolio_performance.daily_average_return()*100:.4f}%\n")
        f.write(f"Annualized Average Return,{portfolio_performance.annualized_average_return()*100:.2f}%\n")
        f.write(f"Daily Variance,{risk_metrics.daily_variance()*100:.4f}%\n")
        f.write(f"Annualized Variance,{risk_metrics.annualized_variance()*100:.2f}%\n")
        f.write(f"Daily Volatility,{risk_metrics.daily_volatility()*100:.4f}%\n")
        f.write(f"Annualized Volatility,{risk_metrics.annualized_volatility()*100:.2f}%\n")
        f.write(f"Daily Downside Variance,{risk_metrics.daily_downside_variance()*100:.4f}%\n")
        f.write(f"Annualized Downside Variance,{risk_metrics.annualized_downside_variance()*100:.2f}%\n")
        f.write(f"Daily Downside Volatility,{risk_metrics.daily_downside_volatility()*100:.4f}%\n")
        f.write(f"Annualized Downside Volatility,{risk_metrics.annualized_downside_volatility()*100:.2f}%\n")
        f.write(f"Sharpe Ratio (Annualized),{ratios.sharpe_ratio(THREE_MTH_TREASURY_RATE)[1]:.2f}\n")
        f.write(f"Sortino Ratio (Annualized),{ratios.sortino_ratio(THREE_MTH_TREASURY_RATE)[1]:.2f}\n")
        f.write(f"Maximum Drawdown,{risk_metrics.maximum_drawdown()*100:.2f}%\n")

        f.write(f"Custom Benchmark Variance (Daily),{benchmark.benchmark_variance()[0]*100:.4f}%\n")
        f.write(f"SPY Benchmark Variance (Daily),{benchmark.benchmark_variance(benchmark='SPY')[0]*100:.4f}%\n")
        f.write(f"Custom Benchmark Variance (Annualized),{benchmark.benchmark_variance()[1]*100:.2f}%\n")
        f.write(f"SPY Benchmark Variance (Annualized),{benchmark.benchmark_variance(benchmark='SPY')[1]*100:.2f}%\n")

        f.write(f"Custom Benchmark Volatility (Daily),{benchmark.benchmark_volatility()[0]*100:.4f}%\n")
        f.write(f"SPY Benchmark Volatility (Daily),{benchmark.benchmark_volatility(benchmark='SPY')[0]*100:.4f}%\n")
        f.write(f"Custom Benchmark Volatility (Annualized),{benchmark.benchmark_volatility()[1]*100:.2f}%\n")
        f.write(f"SPY Benchmark Volatility (Annualized),{benchmark.benchmark_volatility(benchmark='SPY')[1]*100:.2f}%\n")

        f.write(f"Custom Benchmark Average Return (Daily),{benchmark.benchmark_average_return()[0]*100:.4f}%\n")
        f.write(f"SPY Benchmark Average Return (Daily),{benchmark.benchmark_average_return(benchmark='SPY')[0]*100:.4f}%\n")
        f.write(f"Custom Benchmark Average Return (Annualized),{benchmark.benchmark_average_return()[1]*100:.2f}%\n")
        f.write(f"SPY Benchmark Average Return (Annualized),{benchmark.benchmark_average_return(benchmark='SPY')[1]*100:.2f}%\n")
    
        f.write(f"Portfolio Beta,{market_comparison.beta():.4f}\n")
        f.write(f"Portfolio Alpha against custom benchmark,{100*market_comparison.alpha(THREE_MTH_TREASURY_RATE):.4f}%\n")
        f.write(f"Portfolio Alpha against SPY benchmark,{100*market_comparison.alpha(THREE_MTH_TREASURY_RATE, benchmark='SPY'):.4f}%\n")

        f.write(f"Portfolio Risk Premium,{market_comparison.portfolio_risk_premium(THREE_MTH_TREASURY_RATE)*100:.2f}%\n")
        f.write(f"Risk Adjusted Return (three month treasury rate),{market_comparison.risk_adjusted_return(THREE_MTH_TREASURY_RATE)*100:.2f}%\n")
        f.write(f"Treynor Ratio (three month treasury rate),{ratios.treynor_ratio(THREE_MTH_TREASURY_RATE):.2f}\n")
        # f.write(f"Information Ratio (Custom Benchmark),{information_ratio():.2f}\n")
        f.write("--- Portfolio Returns ---\n")
        f.write(f"1 Day Return,{period_metrics['1d'] * 100:.2f}%\n")
        f.write(f"1 Week Return,{period_metrics['1w'] * 100:.2f}%\n")
        f.write(f"1 Month Return,{period_metrics['1m'] * 100:.2f}%\n")
        f.write(f"Year-to-Date Return,{period_metrics['YTD'] * 100:.2f}%\n")
        f.write(f"1 Year Return,{period_metrics['1y'] * 100:.2f}%\n")
        f.write(f"Inception,{period_metrics['Inception'] * 100:.2f}%\n")

    data_processor.plot_portfolio_value()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 PerformanceTracker.py <folder_prefix>")
    folder_prefix = sys.argv[1]
    output_folder = os.path.join("data", folder_prefix, "output")
    os.makedirs(output_folder, exist_ok=True)
    main()

    # notes: % changes are only to 2 decimals in portfolio_total.csv
    # definitely something wrong here, possibly because of that.