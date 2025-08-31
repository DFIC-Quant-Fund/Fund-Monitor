# ruff: noqa: E402
import unittest
import pandas as pd
import os
import sys

# Add the parent directory to sys.path - need to access files from tests folder
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from unittest.mock import patch
from src.controllers.market_comparison import MarketComparison  
from src.controllers.benchmark import Benchmark
from src.controllers.returns_calculator import ReturnsCalculator as PortfolioPerformance
from src.controllers.risk_metrics import RiskMetrics

class TestMarketComparison(unittest.TestCase):
    def setUp(self):
        # Set up output as fake (don't need to store anything)
        self.output_folder = "tests/mock_data"  # Assume mock data folder
        self.market_comparison = MarketComparison()

    # create objects, so when show up in code use these instead 
    @patch.object(Benchmark, 'benchmark_variance', return_value=(0.02, 5))  
    @patch.object(Benchmark, 'get_spy_benchmark')
    # When pandas.read_csv is called ignore it - use mock returns 
    @patch('pandas.read_csv')
    def test_beta(self, mock_read_csv, mock_get_spy_benchmark, mock_benchmark_variance):
        # Mock portfolio data
        mock_portfolio_returns = pd.DataFrame({'pct_change': [0.01, 0.02, -0.01, 0.03, 0.02]})  # Portfolio returns
        mock_benchmark_returns = pd.DataFrame({'pct_change': [0.005, 0.01, -0.005, 0.015, 0.01]})  # Benchmark returns
        # fake csv read 
        mock_read_csv.side_effect = [mock_portfolio_returns, mock_benchmark_returns]

        # Calculate expected beta manually
        covariance = mock_portfolio_returns['pct_change'].cov(mock_benchmark_returns['pct_change'])
        expected_beta = covariance / 0.02  # mock_benchmark_variance returns 0.02

        # Call the beta method
        beta_value = self.market_comparison.beta()

        # Assert that the beta value is a float and matches the expected value
        self.assertIsInstance(beta_value, float)
        self.assertEqual(beta_value, expected_beta)
    
    # create objects, so when show up in code use these instead 
    @patch.object(PortfolioPerformance, 'annualized_average_return', return_value=0.08)
    @patch.object(Benchmark, 'benchmark_average_return', return_value=(0.01, 0.07))
    @patch.object(MarketComparison, 'beta', return_value=1.2)
    def test_alpha(self, mock_beta, mock_benchmark_avg_return, mock_annualized_avg_return):

        risk_free_rate = 0.02  # 2% risk-free rate

        # Calculate expected alpha manually
        expected_alpha = (0.08 - risk_free_rate) - 1.2 * (0.07 - risk_free_rate)

        # Call the alpha method
        alpha_value = self.market_comparison.alpha(risk_free_rate)

        self.assertEqual(alpha_value, expected_alpha)

    @patch.object(PortfolioPerformance, 'annualized_average_return', return_value=0.08)
    def test_portfolio_risk_premium(self, mock_annualized_avg_return):
       
        risk_free_return = 0.02  # 2% risk-free return

        # Calculate expected risk premium manually
        expected_risk_premium = 0.08 - risk_free_return

        # Call the portfolio_risk_premium method
        risk_premium = self.market_comparison.portfolio_risk_premium(risk_free_return)


        self.assertEqual(risk_premium, expected_risk_premium)

    @patch.object(RiskMetrics, 'annualized_volatility', return_value=0.15)
    @patch.object(Benchmark, 'benchmark_volatility', return_value=(0.01, 0.12))
    @patch.object(MarketComparison, 'portfolio_risk_premium', return_value=0.06)
    def test_risk_adjusted_return(self, mock_risk_premium, mock_benchmark_vol, mock_portfolio_vol):
        
        risk_free_return = 0.02  # 2% risk-free return

        # Calculate expected risk-adjusted return manually
        expected_risk_adj_return = 0.06 * 0.12 / 0.15 + risk_free_return

        # Call the risk_adjusted_return method
        risk_adj_return = self.market_comparison.risk_adjusted_return(risk_free_return)

        self.assertEqual(risk_adj_return, expected_risk_adj_return)

if __name__ == '__main__':
    # unittest.main() automatically finds and runs all functions that start with test_
    unittest.main()