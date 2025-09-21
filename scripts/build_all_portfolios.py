"""Build all configured portfolios.

This script:
- Derives trades CSVs from YAML via `scripts/derive_trades_from_yaml.py`
- Invokes `src/models/portfolio_csv_builder.py` for each portfolio.

Usage:
    python scripts/build_all_portfolios.py
"""

import os
import sys
import subprocess


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def run_builder(portfolio_name: str) -> None:
    # Fix the import warning by running the file directly instead of as a module
    script_path = os.path.join(PROJECT_ROOT, 'src', 'models', 'portfolio_csv_builder.py')
    cmd = [sys.executable, script_path, portfolio_name]
    print(f"\n=== Building '{portfolio_name}' via portfolio_csv_builder ===")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        raise SystemExit(f"Build failed for portfolio: {portfolio_name} (exit code {result.returncode})")


def main() -> None:
    portfolios = ['core', 'benchmark']
    # Derive trades.csv from YAML before building
    derive_cmd = [sys.executable, os.path.join(PROJECT_ROOT, 'scripts', 'derive_trades_from_yaml.py')] + portfolios
    print("\n=== Deriving trades from YAML ===")
    result = subprocess.run(derive_cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        raise SystemExit(f"Derive trades step failed (exit code {result.returncode})")
    for p in portfolios:
        run_builder(p)
    print("\nAll portfolios built successfully.")


if __name__ == '__main__':
    main()


