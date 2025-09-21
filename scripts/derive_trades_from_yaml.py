"""Derive `data/<portfolio>/input/trades.csv` from YAML portfolio definitions.

Reads `config/portfolio_definitions/<portfolio>.yaml`, normalizes transactions,
and writes a sorted CSV with headers: Date, Ticker, Currency, Quantity, Price.

Usage:
    python scripts/derive_trades_from_yaml.py [portfolio ...]
"""

import csv
import os
import sys
from typing import List, Dict, Any

import yaml


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def _load_transactions_from_yaml(portfolio_name: str) -> List[Dict[str, Any]]:
    yaml_path = os.path.join(
        PROJECT_ROOT,
        'config',
        'portfolio_definitions',
        f'{portfolio_name}.yaml',
    )
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"YAML not found for portfolio '{portfolio_name}': {yaml_path}")

    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}

    transactions = data.get('transactions', []) or []
    if not isinstance(transactions, list):
        raise ValueError(f"'transactions' must be a list in {yaml_path}")
    return transactions


def _normalize_row(tx: Dict[str, Any]) -> Dict[str, Any]:
    tx_type = str(tx.get('type', '')).strip().lower()
    date = str(tx.get('date', '')).strip()
    ticker = str(tx.get('ticker', '')).strip()
    currency = str(tx.get('currency', '')).strip().upper()
    price = float(tx.get('price'))
    quantity = float(tx.get('quantity'))
    if tx_type == 'sell':
        quantity = -abs(quantity)
    else:
        quantity = abs(quantity)
    return {
        'Date': date,
        'Ticker': ticker,
        'Currency': currency,
        'Quantity': quantity,
        'Price': price,
    }


def derive_trades_for_portfolio(portfolio_name: str) -> str:
    """Derive trades.csv from YAML for a given portfolio and return output path."""
    transactions = _load_transactions_from_yaml(portfolio_name)
    rows = [_normalize_row(tx) for tx in transactions]

    # Sort rows deterministically by Date then Ticker
    rows.sort(key=lambda r: (r['Date'], r['Ticker']))

    input_dir = os.path.join(PROJECT_ROOT, 'data', portfolio_name, 'input')
    os.makedirs(input_dir, exist_ok=True)
    output_csv = os.path.join(input_dir, 'trades.csv')

    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f, fieldnames=['Date', 'Ticker', 'Currency', 'Quantity', 'Price']
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    return output_csv


def main(args: List[str]) -> None:
    portfolios = args or ['core', 'benchmark']
    for name in portfolios:
        path = derive_trades_for_portfolio(name)
        print(f"Derived trades for '{name}' -> {path}")


if __name__ == '__main__':
    main(sys.argv[1:])


