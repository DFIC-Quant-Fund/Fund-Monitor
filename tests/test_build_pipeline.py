# ruff: noqa: E402
"""Unit tests for the build pipeline: derive_trades_from_yaml and build_all_portfolios."""
import csv
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import yaml

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)


class TestDeriveTradesFromYaml(unittest.TestCase):
    """Tests for scripts/derive_trades_from_yaml.py."""

    def _import_derive_module(self):
        scripts_dir = os.path.join(parent_dir, "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import derive_trades_from_yaml as mod
        return mod

    def test_load_transactions_from_yaml_missing_file(self):
        mod = self._import_derive_module()
        with self.assertRaises(FileNotFoundError) as ctx:
            mod._load_transactions_from_yaml("nonexistent_portfolio_xyz")
        self.assertIn("nonexistent_portfolio_xyz", str(ctx.exception))

    def test_load_transactions_from_yaml_invalid_structure(self):
        mod = self._import_derive_module()
        with tempfile.TemporaryDirectory() as tmp:
            yaml_path = os.path.join(tmp, "bad.yaml")
            with open(yaml_path, "w") as f:
                f.write("transactions: not_a_list")
            with patch.object(mod, "PROJECT_ROOT", tmp):
                # Config dir is tmp, so path becomes tmp/config/portfolio_definitions/bad.yaml
                config_dir = os.path.join(tmp, "config", "portfolio_definitions")
                os.makedirs(config_dir, exist_ok=True)
                bad_yaml = os.path.join(config_dir, "bad.yaml")
                with open(bad_yaml, "w") as f:
                    f.write("transactions: not_a_list")
            with patch.object(mod, "PROJECT_ROOT", tmp):
                with self.assertRaises(ValueError) as ctx:
                    mod._load_transactions_from_yaml("bad")
                self.assertIn("list", str(ctx.exception))

    def test_normalize_row_buy(self):
        mod = self._import_derive_module()
        tx = {
            "type": "Buy",
            "date": "2023-01-15",
            "ticker": "AAPL",
            "currency": "USD",
            "price": 150.0,
            "quantity": 10,
            "sector": "Tech",
            "geography": "US",
            "asset_class": "Equity",
        }
        row = mod._normalize_row(tx)
        self.assertEqual(row["Date"], "2023-01-15")
        self.assertEqual(row["Ticker"], "AAPL")
        self.assertEqual(row["Currency"], "USD")
        self.assertEqual(row["Price"], 150.0)
        self.assertEqual(row["Quantity"], 10)

    def test_normalize_row_sell_negative_quantity(self):
        mod = self._import_derive_module()
        tx = {
            "type": "Sell",
            "date": "2023-02-01",
            "ticker": "GOOG",
            "currency": "USD",
            "price": 140.0,
            "quantity": 5,
        }
        row = mod._normalize_row(tx)
        self.assertEqual(row["Quantity"], -5)

    def test_normalize_conversion_row(self):
        mod = self._import_derive_module()
        tx = {
            "date": "2024-01-10",
            "currency_from": "USD",
            "currency_to": "CAD",
            "amount": 1000.0,
            "conversion_rate": 1.35,
        }
        row = mod._normalize_conversion_row(tx)
        self.assertEqual(row["Date"], "2024-01-10")
        self.assertEqual(row["Currency_From"], "USD")
        self.assertEqual(row["Currency_To"], "CAD")
        self.assertEqual(row["Amount"], 1000.0)
        self.assertEqual(row["Rate"], 1.35)

    def test_derive_trades_for_portfolio_writes_csvs(self):
        mod = self._import_derive_module()
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = os.path.join(tmp, "config", "portfolio_definitions")
            os.makedirs(config_dir, exist_ok=True)
            yaml_path = os.path.join(config_dir, "unittest_port.yaml")
            yaml_content = {
                "portfolio": {"name": "unittest_port"},
                "transactions": [
                    {
                        "type": "Buy",
                        "date": "2023-06-01",
                        "ticker": "SPY",
                        "currency": "USD",
                        "price": 400.0,
                        "quantity": 10,
                        "sector": "ETF",
                        "geography": "US",
                        "asset_class": "Equity",
                    },
                    {
                        "type": "Conversion",
                        "date": "2023-07-01",
                        "currency_from": "USD",
                        "currency_to": "CAD",
                        "amount": 500.0,
                        "conversion_rate": 1.32,
                    },
                ],
            }
            with open(yaml_path, "w") as f:
                yaml.dump(yaml_content, f, default_flow_style=False)

            with patch.object(mod, "PROJECT_ROOT", tmp):
                out_path = mod.derive_trades_for_portfolio("unittest_port")

            self.assertTrue(os.path.isabs(out_path) or "unittest_port" in out_path)
            self.assertTrue(os.path.exists(out_path))

            input_dir = os.path.join(tmp, "data", "unittest_port", "input")
            self.assertTrue(os.path.isdir(input_dir))
            trades_csv = os.path.join(input_dir, "trades.csv")
            conversions_csv = os.path.join(input_dir, "conversions.csv")

            self.assertTrue(os.path.exists(trades_csv))
            with open(trades_csv) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["Ticker"], "SPY")
            self.assertEqual(float(rows[0]["Quantity"]), 10)

            self.assertTrue(os.path.exists(conversions_csv))
            with open(conversions_csv) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["Currency_From"], "USD")
            self.assertEqual(rows[0]["Currency_To"], "CAD")


class TestBuildAllPortfolios(unittest.TestCase):
    """Tests for scripts/build_all_portfolios.py."""

    def _import_build_module(self):
        scripts_dir = os.path.join(parent_dir, "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import build_all_portfolios as mod
        return mod

    @patch("subprocess.run")
    def test_main_calls_derive_then_builder(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        mod = self._import_build_module()
        mod.main()
        self.assertGreaterEqual(mock_run.call_count, 1)
        # First call should be derive_trades_from_yaml
        first_call_args = mock_run.call_args_list[0][0][0]
        self.assertIn("derive_trades_from_yaml", os.path.basename(first_call_args[1]))

    @patch("subprocess.run")
    def test_run_builder_invokes_portfolio_csv_builder(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        mod = self._import_build_module()
        mod.run_builder("core")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertIn("portfolio_csv_builder", os.path.basename(cmd[1]))
        self.assertEqual(cmd[2], "core")
        self.assertEqual(mock_run.call_args[1]["cwd"], mod.PROJECT_ROOT)

    @patch("subprocess.run")
    def test_run_builder_raises_on_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        mod = self._import_build_module()
        with self.assertRaises(SystemExit):
            mod.run_builder("core")
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_main_raises_when_derive_fails(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        mod = self._import_build_module()
        with self.assertRaises(SystemExit):
            mod.main()
        # Should have exited on first (derive) step
        self.assertEqual(mock_run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
