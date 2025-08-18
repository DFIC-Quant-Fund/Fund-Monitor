import os
import sys
import subprocess


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def run_builder(portfolio_name: str) -> None:
    cmd = [sys.executable, '-m', 'src.models.portfolio_csv_builder', portfolio_name]
    print(f"\n=== Building '{portfolio_name}' via portfolio_csv_builder ===")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        raise SystemExit(f"Build failed for portfolio: {portfolio_name} (exit code {result.returncode})")


def main() -> None:
    portfolios = ['core', 'benchmark']
    for p in portfolios:
        run_builder(p)
    print("\nAll portfolios built successfully.")


if __name__ == '__main__':
    main()


