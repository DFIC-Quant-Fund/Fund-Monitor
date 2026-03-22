# ruff: noqa: E402
"""Unit tests for portfolio risk metrics (RiskMetrics)."""
import importlib
import numbers
import os
import sys
import types
import unittest

import pandas as pd

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import RiskMetrics without loading controllers/__init__.py (that pulls in
# market_comparison → getFamaFrenchFactors, which may be missing in some envs).
_src_path = os.path.join(parent_dir, "src")
_controllers_path = os.path.join(_src_path, "controllers")
if "src" not in sys.modules:
    _src_pkg = types.ModuleType("src")
    _src_pkg.__path__ = [_src_path]
    sys.modules["src"] = _src_pkg
if "src.controllers" not in sys.modules:
    _ctrl_pkg = types.ModuleType("src.controllers")
    _ctrl_pkg.__path__ = [_controllers_path]
    sys.modules["src.controllers"] = _ctrl_pkg

RiskMetrics = importlib.import_module("src.controllers.risk_metrics").RiskMetrics


def _returns_df(pct_change_values):
    """Build a DataFrame with 'pct_change' column as expected by RiskMetrics."""
    n = len(pct_change_values)
    return pd.DataFrame({"pct_change": pct_change_values}, index=range(n))


class TestRiskMetricsVarianceVolatility(unittest.TestCase):
    """Tests for variance and volatility calculations."""

    def setUp(self):
        self.returns = [0.02, -0.01, 0.03, 0.01, -0.005, 0.015, 0.02]
        self.df = _returns_df(self.returns)
        self.risk_metrics = RiskMetrics(self.df, risk_free_rate=0.02)

    def test_daily_variance(self):
        daily_returns = self.df["pct_change"].dropna()
        expected = daily_returns.var()
        self.assertAlmostEqual(self.risk_metrics.daily_variance(), expected, places=10)
        self.assertIsInstance(self.risk_metrics.daily_variance(), (float, numbers.Real))

    def test_annualized_variance(self):
        expected = self.risk_metrics.daily_variance() * 252
        self.assertAlmostEqual(
            self.risk_metrics.annualized_variance(), expected, places=10
        )

    def test_daily_volatility(self):
        daily_returns = self.df["pct_change"].dropna()
        expected = daily_returns.std()
        self.assertAlmostEqual(
            self.risk_metrics.daily_volatility(), expected, places=10
        )

    def test_annualized_volatility(self):
        expected = self.risk_metrics.annualized_variance() ** 0.5
        self.assertAlmostEqual(
            self.risk_metrics.annualized_volatility(), expected, places=10
        )


class TestRiskMetricsDownside(unittest.TestCase):
    """Tests for downside variance and volatility."""

    def setUp(self):
        self.returns = [0.01, -0.02, 0.015, -0.01, 0.02]
        self.df = _returns_df(self.returns)
        self.risk_metrics = RiskMetrics(self.df, risk_free_rate=0.02)

    def test_daily_downside_variance(self):
        daily_return = self.df["pct_change"].dropna()
        downside = daily_return[daily_return < 0]
        expected = downside.var()
        self.assertAlmostEqual(
            self.risk_metrics.daily_downside_variance(), expected, places=10
        )

    def test_annualized_downside_variance(self):
        expected = self.risk_metrics.daily_downside_variance() * 252
        self.assertAlmostEqual(
            self.risk_metrics.annualized_downside_variance(), expected, places=10
        )

    def test_daily_downside_volatility(self):
        expected = self.risk_metrics.daily_downside_variance() ** 0.5
        self.assertAlmostEqual(
            self.risk_metrics.daily_downside_volatility(), expected, places=10
        )

    def test_annualized_downside_volatility(self):
        expected = self.risk_metrics.annualized_downside_variance() ** 0.5
        self.assertAlmostEqual(
            self.risk_metrics.annualized_downside_volatility(), expected, places=10
        )


class TestRiskMetricsDrawdown(unittest.TestCase):
    """Tests for maximum drawdown (min daily return)."""

    def test_maximum_drawdown(self):
        returns = [0.01, -0.03, 0.02, -0.01]
        df = _returns_df(returns)
        rm = RiskMetrics(df, risk_free_rate=0.02)
        self.assertAlmostEqual(rm.maximum_drawdown(), -0.03, places=10)


class TestRiskMetricsSharpeSortino(unittest.TestCase):
    """Tests for Sharpe and Sortino ratios."""

    def setUp(self):
        self.returns = [0.01, -0.005, 0.02, 0.015, -0.01, 0.02]
        self.df = _returns_df(self.returns)
        self.risk_metrics = RiskMetrics(self.df, risk_free_rate=0.02)

    def test_sharpe_ratio_returns_tuple(self):
        result = self.risk_metrics.sharpe_ratio(0.02)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        daily_sharpe, annualized_sharpe = result
        self.assertIsInstance(daily_sharpe, numbers.Real)
        self.assertIsInstance(annualized_sharpe, numbers.Real)

    def test_sharpe_ratio_formula(self):
        daily_return = self.df["pct_change"].dropna()
        rf_daily = 0.02 / 252
        expected_daily = (daily_return.mean() - rf_daily) / daily_return.std()
        expected_annual = expected_daily * (252 ** 0.5)
        daily_sharpe, annualized_sharpe = self.risk_metrics.sharpe_ratio(0.02)
        self.assertAlmostEqual(daily_sharpe, expected_daily, places=10)
        self.assertAlmostEqual(annualized_sharpe, expected_annual, places=10)

    def test_sortino_ratio_returns_tuple(self):
        result = self.risk_metrics.sortino_ratio(0.02)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_sortino_ratio_formula(self):
        daily_return = self.df["pct_change"].dropna()
        downside = daily_return[daily_return < 0]
        rf_daily = 0.02 / 252
        expected_daily = (daily_return.mean() - rf_daily) / downside.std()
        expected_annual = expected_daily * (252 ** 0.5)
        daily_sortino, annualized_sortino = self.risk_metrics.sortino_ratio(0.02)
        self.assertAlmostEqual(daily_sortino, expected_daily, places=10)
        self.assertAlmostEqual(annualized_sortino, expected_annual, places=10)


class TestRiskMetricsEdgeCases(unittest.TestCase):
    """Edge cases: single return, risk_free_rate."""

    def test_single_return_variance_is_nan(self):
        df = _returns_df([0.01])
        rm = RiskMetrics(df, risk_free_rate=0.02)
        var = rm.daily_variance()
        self.assertTrue(pd.isna(var))

    def test_risk_free_rate_stored(self):
        df = _returns_df([0.01, -0.01])
        rm = RiskMetrics(df, risk_free_rate=0.03)
        self.assertEqual(rm.RISK_FREE_RATE, 0.03)


if __name__ == "__main__":
    unittest.main()
