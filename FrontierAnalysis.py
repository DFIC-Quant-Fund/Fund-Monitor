import os, sys
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf

'''
Calculates the efficient frontier (weightings) for a given portfolio of assets
1. Gets stock price data from yfinance
2. Calculates annualized returns, annualized standard deviation (volatility) and covariance matrix
3. Performs montecarlo simulation of different portfolio weightings and calculates sharpe ratio for each
4. Plots each portfolio on efficient frontier graph and returns the maximum sharpe and minimum volatility portfolio weightings
'''
class FrontierAnalysis:
    def __init__(self, tickers, start_date, end_date, risk_free_rate, num_simulations):
        self.tickers = tickers
        self.start_date = start_date
        self.end_date = end_date
        self.risk_free_rate = risk_free_rate
        self.num_simulations = num_simulations
        self.data = None
        self.returns = None
        self.annual_returns = {}
        self.annual_volatility = {}
        self.mean_returns_series = None
        self.cov_matrix = None
        self.results_frame = None
        self.max_sharpe_portfolio = None
        self.min_vol_portfolio = None

    def get_data(self):
        data = yf.download(self.tickers, start=self.start_date, end=self.end_date)
        self.data = data['Close']

    def normalized_return_graph(self):
        df = self.data.divide(self.data.iloc[0] / 100)
        plt.figure(figsize=(15, 6))
        for ticker in self.tickers:
            plt.plot(df[ticker], label=ticker)
        plt.legend(loc='upper left', fontsize=12)
        plt.ylabel('Price')
        plt.savefig('data/fund/output/returns.png')

    def calculate_metrics(self):
        # Calculate daily returns
        returns = self.data.pct_change()
        self.returns = returns.dropna()

        # Calculate annualized returns and volatility
        for ticker in self.tickers:
            self.annual_returns[ticker] = returns[ticker].mean() * 252
            self.annual_volatility[ticker] = returns[ticker].std() * np.sqrt(252)

        # Create Series objects for optimization
        self.mean_returns_series = pd.Series([self.annual_returns[t] for t in self.tickers], index=self.tickers)
        self.cov_matrix = self.returns[self.tickers].cov() * 252

    def portfolio_performance(self, weights, mean_returns, cov_matrix):
        weights_array = np.array(weights)
        returns_array = np.array(mean_returns)
        portfolio_return = np.sum(returns_array * weights_array)
        portfolio_volatility = np.sqrt(np.dot(weights_array.T, np.dot(cov_matrix, weights_array)))
        return portfolio_return, portfolio_volatility

    def monte_carlo_simulation(self):

        results = []

        for i in range(self.num_simulations):
            random_weights = np.random.random(len(self.tickers))
            random_weights /= np.sum(random_weights)
            simulated_return, simulated_vol = self.portfolio_performance(random_weights, self.mean_returns_series, self.cov_matrix)
            sharpe = (simulated_return - self.risk_free_rate) / simulated_vol
            results.append({
                'Volatility': simulated_vol,
                'Return': simulated_return,
                'Sharpe': sharpe,
                'Weights': {self.tickers[i]: random_weights[i]
                            for i in range(len(self.tickers))}
            })
        self.results_frame = pd.DataFrame(results)
        self.max_sharpe_portfolio = self.results_frame.iloc[self.results_frame['Sharpe'].idxmax()]
        self.min_vol_portfolio = self.results_frame.iloc[self.results_frame['Volatility'].idxmin()]

    def printing_results(self):

        print("Annualized Returns:")
        for ticker in self.tickers:
            print(f"{ticker}: {self.annual_returns[ticker] * 100:.2f}%")

        print("Annualized Standard Deviation:")
        for ticker in self.tickers:
            print(f"{ticker}: {self.annual_volatility[ticker] * 100:.2f}%")

        min_vol_weights = self.min_vol_portfolio['Weights']
        min_vol_allocation = pd.DataFrame.from_dict(min_vol_weights, orient='index', columns=['Allocation'])
        min_vol_allocation['Allocation'] = (min_vol_allocation['Allocation'] * 100).round(2)
        max_sharpe_weights = self.max_sharpe_portfolio['Weights']
        max_sharpe_allocation = pd.DataFrame.from_dict(max_sharpe_weights, orient='index', columns=['Allocation'])
        max_sharpe_allocation['Allocation'] = (max_sharpe_allocation['Allocation'] * 100).round(2)

        print("\nMinimum Volatility Portfolio:")
        print(min_vol_allocation)
        print(f"Expected annual return: {self.min_vol_portfolio['Return'] * 100:.2f}%")
        print(f"Expected volatility: {self.min_vol_portfolio['Volatility'] * 100:.2f}%")
        print(f"Sharpe Ratio: {self.min_vol_portfolio['Sharpe']:.3f}")

        print("\nMaximum Sharpe Ratio Portfolio:")
        print(max_sharpe_allocation)
        print(f"Expected annual return: {self.max_sharpe_portfolio['Return'] * 100:.2f}%")
        print(f"Expected volatility: {self.max_sharpe_portfolio['Volatility'] * 100:.2f}%")
        print(f"Sharpe Ratio: {self.max_sharpe_portfolio['Sharpe']:.3f}")

    def efficient_frontier_graph(self):
        plt.figure(figsize=(16, 9))
        plt.scatter(self.results_frame['Volatility'], self.results_frame['Return'], c=self.results_frame['Sharpe'], alpha=0.75, s=25)
        plt.colorbar(label='Sharpe Ratio')

        plt.scatter(self.max_sharpe_portfolio['Volatility'], self.max_sharpe_portfolio['Return'], c='green', marker='X', s=200,
                    label='Maximum Sharpe Ratio')
        plt.scatter(self.min_vol_portfolio['Volatility'], self.min_vol_portfolio['Return'], c='blue', marker='X', s=200,
                    label='Minimum Volatility')

        for ticker in self.tickers:
            plt.scatter(self.annual_volatility[ticker], self.annual_returns[ticker], s=150, label=ticker)

        plt.title('Efficient Frontier Graph')
        plt.xlabel('Annualized Standard Deviation (Volatility)')
        plt.ylabel('Annualized Return')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig('data/fund/output/efficient_frontier.png')

def main():
    # Constants
    risk_free_rate = 0.0275
    num_simulations = 50_000
    lookback_period_days = 365 * 3

    # Manually inputted portfolio funds/sectors
    TMT_fund = ['AAPL', 'EA', 'AMAT', 'VEEV', 'TMUS']
    industrial_fund = ['GSL', 'TEX', 'CEG', 'WSC']
    resource_fund = ['MP', 'DOLE']
    financial_fund = ['CG', 'APO', 'AER', 'MA', 'AMSF']
    macro_fund = ['AGG', 'SPY', 'SPSB']
    cnh_fund = ['ISRG', 'BLBD']

    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=lookback_period_days)
    analyzer = FrontierAnalysis(financial_fund, start_date, end_date, risk_free_rate, num_simulations)
    analyzer.get_data()
    #analyzer.normalized_return_graph()
    analyzer.calculate_metrics()
    analyzer.monte_carlo_simulation()
    analyzer.printing_results()
    analyzer.efficient_frontier_graph()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 PerformanceTracker.py <folder_prefix>")
    folder_prefix = sys.argv[1]
    output_folder = os.path.join("data", folder_prefix, "output")
    os.makedirs(output_folder, exist_ok=True)
    main()


