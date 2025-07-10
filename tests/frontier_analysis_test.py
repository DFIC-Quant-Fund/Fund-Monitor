# import unittest
# from unittest.mock import patch
# import numpy as np
# import pandas as pd
# from datetime import datetime, timedelta
# import sys
# import os
# # Add the parent directory to sys.path - need to access files from tests folder
# parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# sys.path.append(parent_dir)

# from services.frontier_analysis import FrontierAnalysis
# import yfinance as yf

# class TestFrontierAnalysis(unittest.TestCase):
#     # Runs before each test to create a FrontierAnalysis instance + set up other variables 
#     # setup special method in unittest.TestCase
#     def setUp(self):
#         print("setting up")
#         self.portfolio = 'TestPortfolio'
#         self.tickers = ['AAPL', 'GOOG', 'MSFT']
#         self.start_date = datetime(2023, 1, 1)  
#         self.end_date = datetime(2024, 1, 1)
#         self.risk_free_rate = 0.0275
#         self.num_simulations = 50_000

#         # Initialize the FrontierAnalysis instance
#         self.analyzer = FrontierAnalysis(self.portfolio, self.tickers, self.start_date, self.end_date, self.risk_free_rate, self.num_simulations)

#         # Mock data for testing
#         self.mock_data = pd.DataFrame({
#             ('Close', 'AAPL'): [150, 152, 155],
#             ('Close', 'GOOG'): [2800, 2825, 2840],
#             ('Close', 'MSFT'): [300, 305, 310]
#         }, index=pd.date_range(self.start_date, periods=3))

#         # Populate the analyzer's data attribute for testing
#         self.analyzer.data = self.mock_data['Close']

#     # not actually calling yf download - use of mock data 
#     # use of patch to do that - replaces yf.download() with mock_yf_download inside the test
#     @patch("yfinance.download")  # Corrected the module name to "yfinance.download"
#     def test_get_data(self, mock_yf_download):
#         print("get_data test")
#         # whenever yf.download() is called, returning mocked data instead of fetching real stock prices
#         mock_yf_download.return_value = self.mock_data
#         self.analyzer.get_data()

#         # checking storage of data in analysis + confirming format (checking AAPL in cols)
#         self.assertIsNotNone(self.analyzer.data)
#         self.assertEqual(len(self.analyzer.data), 3)
#         self.assertIn('AAPL', self.analyzer.data.columns)

#     def test_calculate_metrics(self):
#         print("calc metric test")
#         # want to compare function with current logic 
#         # ensure logically output is the same even if new elements/methods added in frontier calc metrics 

#         # Manually calculate the daily returns
#         returns = self.analyzer.data.pct_change().dropna()

#         # Manually calculate annualized returns and volatility
#         expected_annual_returns = {}
#         expected_annual_volatility = {}
#         for ticker in self.analyzer.tickers:
#             expected_annual_returns[ticker] = returns[ticker].mean() * 252
#             expected_annual_volatility[ticker] = returns[ticker].std() * np.sqrt(252)

#         # Call calculate_metrics
#         self.analyzer.calculate_metrics()

#         # some values have been stored in matrix
#         self.assertIsNotNone(self.analyzer.cov_matrix)

#         # checking if values are calculated correctly based on current logic, comparing each ticker (up to 6 decimal places)
#         for ticker in self.analyzer.tickers:
#             self.assertAlmostEqual(self.analyzer.annual_returns[ticker], expected_annual_returns[ticker], places=6)
#             self.assertAlmostEqual(self.analyzer.annual_volatility[ticker], expected_annual_volatility[ticker], places=6)

#     def test_portfolio_performance(self):
#         print("portfolio perform test")
#         # fake inputs
#         weights = [0.4, 0.3, 0.3]
#         mean_returns = [0.1, 0.08, 0.12]  #
#         cov_matrix = np.array([[0.02, 0.01, 0.015],
#                             [0.01, 0.03, 0.02],
#                             [0.015, 0.02, 0.025]])  
              
#         portfolio_return_manual = np.sum(np.array(mean_returns) * np.array(weights))
#         portfolio_volatility_manual = np.sqrt(np.dot(np.array(weights).T, np.dot(cov_matrix, np.array(weights))))

#         # Call the method to calculate the portfolio performance with real function 
#         portfolio_return, portfolio_volatility = self.analyzer.portfolio_performance(weights, mean_returns, cov_matrix)

#         # Compare the "manually" calculated return with called
#         self.assertEqual(portfolio_return, portfolio_return_manual)
#         self.assertEqual(portfolio_volatility, portfolio_volatility_manual)

#     # don't want to test with real random values - using patch to ensure consistency 
#     @patch("numpy.random.random")
#     def test_monte_carlo_simulation(self, mock_random):
#         print("monte carlo test")
#         # Mock "random" weights for during the test - lambda used to ensure behaviour is like random 
#         mock_random.side_effect = lambda size: np.array([0.5, 0.3, 0.2])[:size]

#         # Mock mean returns and covariance matrix
#         self.analyzer.mean_returns_series = pd.Series([0.1, 0.08, 0.12], index=self.tickers)
#         self.analyzer.cov_matrix = np.array([[0.02, 0.01, 0.015],
#                                             [0.01, 0.03, 0.02],
#                                             [0.015, 0.02, 0.025]])

#         # Manually calculate the expected portfolio return and volatility using the weights and the provided cov_matrix
#         random_weights = np.array([0.5, 0.3, 0.2]) # Mocked weights - same as what was created before 
#         random_weights /= random_weights.sum()  # Normalize weights - done in frontier so to remain consistent 
#         simulated_return, simulated_volatility = self.analyzer.portfolio_performance(random_weights, self.analyzer.mean_returns_series, self.analyzer.cov_matrix)
#         sharpe_ratio = (simulated_return - self.risk_free_rate) / simulated_volatility

#         # Manually creating a result dictionary to compare with the function's output
#         expected_result = {
#             'Volatility': simulated_volatility,
#             'Return': simulated_return,
#             'Sharpe': sharpe_ratio,
#             'Weights': {self.tickers[i]: random_weights[i] for i in range(len(self.tickers))}
#         }
#         expected_results_frame = pd.DataFrame([expected_result])
#         sharpe_idx = expected_results_frame['Sharpe'].idxmax()
#         expected_sharpe = expected_results_frame.loc[sharpe_idx]
#         vol_idx = expected_results_frame['Volatility'].idxmin()
#         expected_vol = expected_results_frame.loc[vol_idx]

#         # Perform the Monte Carlo simulation and assert consistency
#         self.analyzer.monte_carlo_simulation()

#         # Check that the results DataFrame is not empty
#         self.assertFalse(self.analyzer.results_frame.empty)
#         # Check that the results contain the 'Sharpe' column
#         self.assertIn('Sharpe', self.analyzer.results_frame.columns)

#         # Check if the manually calculated Sharpe ratio is consistent with the function's results
#         self.assertEqual(self.analyzer.max_sharpe_portfolio['Sharpe'], expected_sharpe['Sharpe'])
#         self.assertEqual(self.analyzer.min_vol_portfolio['Volatility'], expected_vol['Volatility'])


# if __name__ == '__main__':
#     # unittest.main() automatically finds and runs all functions that start with test_
#     unittest.main()