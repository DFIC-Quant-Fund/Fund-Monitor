import os
import sys
import yaml
from performance import (
    DataProcessor, 
    Benchmark, 
    PortfolioPerformance, 
    RiskMetrics, 
    MarketComparison,
    Ratios
)

'''
FILE PURPOSE: RUNS TO FILL SECONDARY OUtPUT TABLES (ones that require calcuation - getting calc from performance files)
Uses all files in performance folder 
run every day (second thing run in github actions - after portfolio (which updates output most tables)) 
'''

def main():
    market_values_file = os.path.join(output_folder, "market_values.csv")
    cash_file = os.path.join(output_folder, "cash.csv") 
    dividend_file = os.path.join(output_folder, "dividend_values.csv") 
    output_file = os.path.join(output_folder, "portfolio_total.csv") 
    THREE_MTH_TREASURY_RATE = 0.0436 # 3-month treasury rate
    FIVE_PERCENT = 0.05

    # Load config file
    config_path = os.path.join('portfolios', f'dfic_{output_folder.split('/')[1]}.yaml')
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        sys.exit(1)

    data_processor = DataProcessor(output_folder)
    benchmark = Benchmark(output_folder)
    portfolio_performance = PortfolioPerformance(output_folder)
    risk_metrics = RiskMetrics(output_folder)
    market_comparison = MarketComparison(output_folder)
    ratios = Ratios(output_folder)

    # run these once only after running portfolio.py once
    data_processor.aggregate_data(market_values_file, cash_file, dividend_file, output_file)
    benchmark.create_custom_benchmark()
    period_metrics = portfolio_performance.calculate_period_performance()

    # Fixed income tickers from config
    #TODO: sector naming inconsistent (pull this from db instead)
    fi_tickers = [security['ticker'] for security in config['securities'] if security.get('sector') == 'Fixed Income']

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

    print("--- Benchmark Info ---\n")
    print(f"Custom Benchmark Variance (Daily),{benchmark.benchmark_variance()[0]*100:.4f}%\n")
    print(f"SPY Variance (Daily),{benchmark.benchmark_variance(benchmark='SPY')[0]*100:.4f}%\n")
    print(f"Custom Benchmark Variance (Annualized),{benchmark.benchmark_variance()[1]*100:.2f}%\n")
    print(f"SPY Variance (Annualized),{benchmark.benchmark_variance(benchmark='SPY')[1]*100:.2f}%\n")
    print(f"Custom Benchmark Volatility (Daily),{benchmark.benchmark_volatility()[0]*100:.4f}%\n")
    print(f"SPY Volatility (Daily),{benchmark.benchmark_volatility(benchmark='SPY')[0]*100:.4f}%\n")
    print(f"Custom Benchmark Volatility (Annualized),{benchmark.benchmark_volatility()[1]*100:.2f}%\n")
    print(f"SPY Volatility (Annualized),{benchmark.benchmark_volatility(benchmark='SPY')[1]*100:.2f}%\n")
    print(f"Custom Benchmark Average Return (Daily),{benchmark.benchmark_average_return()[0]*100:.4f}%\n")
    print(f"SPY Average Return (Daily),{benchmark.benchmark_average_return(benchmark='SPY')[0]*100:.4f}%\n")
    print(f"Custom Benchmark Average Return (Annualized),{benchmark.benchmark_average_return()[1]*100:.2f}%\n")
    print(f"SPY Average Return (Annualized),{benchmark.benchmark_average_return(benchmark='SPY')[1]*100:.2f}%\n")
    print(f"Custom Benchmark Inception Return,{benchmark.benchmark_inception_return() * 100:.2f}%\n")
    print(f"SPY Inception Return,{benchmark.spy_inception_return() * 100:.2f}%\n")

    print(f"Portfolio Beta,{market_comparison.beta():.4f}\n")
    print(f"Portfolio Alpha against custom benchmark,{100*market_comparison.alpha(THREE_MTH_TREASURY_RATE):.4f}%\n")
    print(f"Portfolio Alpha against SPY,{100*market_comparison.alpha(THREE_MTH_TREASURY_RATE, benchmark='SPY'):.4f}%\n")

    print(f"Portfolio Risk Premium,{market_comparison.portfolio_risk_premium(THREE_MTH_TREASURY_RATE)*100:.2f}%\n")
    print(f"Risk Adjusted Return (three month treasury rate),{market_comparison.risk_adjusted_return(THREE_MTH_TREASURY_RATE)*100:.2f}%\n")
    print(f"Treynor Ratio (three month treasury rate),{ratios.treynor_ratio(THREE_MTH_TREASURY_RATE):.2f}\n")
    daily_ir, annual_ir = ratios.information_ratio()
    print(f"Information Ratio (Daily),{daily_ir:.4f}\n")
    print(f"Information Ratio (Annualized),{annual_ir:.2f}\n")

    print("--- Fixed Income Info ---\n")
    fi_stats_df = portfolio_performance.get_fixed_income_info(fi_tickers)
    print(f"{fi_stats_df}\n")

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
        f.write(f"SPY Variance (Daily),{benchmark.benchmark_variance(benchmark='SPY')[0]*100:.4f}%\n")
        f.write(f"Custom Benchmark Variance (Annualized),{benchmark.benchmark_variance()[1]*100:.2f}%\n")
        f.write(f"SPY Variance (Annualized),{benchmark.benchmark_variance(benchmark='SPY')[1]*100:.2f}%\n")
        f.write(f"Custom Benchmark Volatility (Daily),{benchmark.benchmark_volatility()[0]*100:.4f}%\n")
        f.write(f"SPY Volatility (Daily),{benchmark.benchmark_volatility(benchmark='SPY')[0]*100:.4f}%\n")
        f.write(f"Custom Benchmark Volatility (Annualized),{benchmark.benchmark_volatility()[1]*100:.2f}%\n")
        f.write(f"SPY Volatility (Annualized),{benchmark.benchmark_volatility(benchmark='SPY')[1]*100:.2f}%\n")
        f.write(f"Custom Benchmark Average Return (Daily),{benchmark.benchmark_average_return()[0]*100:.4f}%\n")
        f.write(f"SPY Average Return (Daily),{benchmark.benchmark_average_return(benchmark='SPY')[0]*100:.4f}%\n")
        f.write(f"Custom Benchmark Average Return (Annualized),{benchmark.benchmark_average_return()[1]*100:.2f}%\n")
        f.write(f"SPY Average Return (Annualized),{benchmark.benchmark_average_return(benchmark='SPY')[1]*100:.2f}%\n")
        f.write(f"Custom Benchmark Inception Return,{benchmark.benchmark_inception_return() * 100:.2f}%\n")
        f.write(f"SPY Inception Return,{benchmark.spy_inception_return() * 100:.2f}%\n")
    
        f.write(f"Portfolio Beta,{market_comparison.beta():.4f}\n")
        f.write(f"Portfolio Alpha against custom benchmark,{100*market_comparison.alpha(THREE_MTH_TREASURY_RATE):.4f}%\n")
        f.write(f"Portfolio Alpha against SPY,{100*market_comparison.alpha(THREE_MTH_TREASURY_RATE, benchmark='SPY'):.4f}%\n")

        f.write(f"Portfolio Risk Premium,{market_comparison.portfolio_risk_premium(THREE_MTH_TREASURY_RATE)*100:.2f}%\n")
        f.write(f"Risk Adjusted Return (three month treasury rate),{market_comparison.risk_adjusted_return(THREE_MTH_TREASURY_RATE)*100:.2f}%\n")
        f.write(f"Treynor Ratio (three month treasury rate),{ratios.treynor_ratio(THREE_MTH_TREASURY_RATE):.2f}\n")
        f.write(f"Information Ratio (vs. Custom Benchmark, daily),{daily_ir:.4f}\n")
        f.write(f"Information Ratio (vs. Custom Benchmark, annual),{annual_ir:.2f}\n")

        # Fixed Income Metrics
        for ticker in fi_tickers:
            f.write(f"{ticker} Current Mkt Value,{fi_stats_df.loc[ticker, 'Market Value']:.2f}\n")
            f.write(f"{ticker} Fixed Income Mkt Share,{fi_stats_df.loc[ticker, 'Total Market Share']*100:.2f}%\n")
            f.write(f"{ticker} USD FI Mkt Share,{fi_stats_df.loc[ticker, 'USD Market Share']*100:.2f}%\n")
        
        # Portfolio Return Metrics
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