"""Derive input CSVs from YAML portfolio definitions.

Reads `config/portfolio_definitions/<portfolio>.yaml`, normalizes transactions,
and writes sorted CSVs in `data/<portfolio>/input`:
  - trades.csv with headers: Date, Ticker, Currency, Quantity, Price (Buy/Sell only)
  - conversions.csv with headers: Date, Currency_From, Currency_To, Amount, Rate

Usage:
    python scripts/derive_trades_from_yaml.py [portfolio ...]
"""

import csv
import os
import sys
from typing import List, Dict, Any

import yaml

# Add project root to Python path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config.logging_config import get_logger

logger = get_logger(__name__)

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
    
    # Extract optional metadata fields
    sector = str(tx.get('sector', '')).strip()
    geography = str(tx.get('geography', '')).strip()
    asset_class = str(tx.get('asset_class', '')).strip()
    status = str(tx.get('status', '')).strip()

    return {
        'Date': date,
        'Ticker': ticker,
        'Currency': currency,
        'Quantity': quantity,
        'Price': price,
        'Sector': sector,
        'Geography': geography,
        'Asset_Class': asset_class,
        'Status': status,
    }


def _normalize_conversion_row(tx: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a conversion transaction into a standardized dict.

    Rate semantics: units of Currency_To per 1 unit of Currency_From.
    Example: USD->CAD at 1.3821 means 1 USD = 1.3821 CAD.
    """
    date = str(tx.get('date', '')).strip()
    currency_from = str(tx.get('currency_from', '')).strip().upper()
    currency_to = str(tx.get('currency_to', '')).strip().upper()
    amount = float(tx.get('amount'))
    rate_val = tx.get('conversion_rate')
    rate = float(rate_val) if rate_val is not None else float('nan')

    logger.info(f"Conversion parsed: {amount} {currency_from} -> {currency_to} at rate {rate}")

    return {
        'Date': date,
        'Currency_From': currency_from,
        'Currency_To': currency_to,
        'Amount': amount,
        'Rate': rate,
    }


def derive_trades_for_portfolio(portfolio_name: str) -> str:
    """Derive input CSVs (trades, conversions) from YAML and return trades path."""
    transactions = _load_transactions_from_yaml(portfolio_name)
    trade_rows: List[Dict[str, Any]] = []
    conversion_rows: List[Dict[str, Any]] = []

    for tx in transactions:
        tx_type = str(tx.get('type', '')).strip().lower()
        if tx_type == 'conversion':
            conversion_rows.append(_normalize_conversion_row(tx))
        else:
            trade_rows.append(_normalize_row(tx))

    # Sort rows deterministically
    trade_rows.sort(key=lambda r: (r['Date'], r['Ticker']))
    conversion_rows.sort(key=lambda r: (r['Date'], r['Currency_From'], r['Currency_To']))

    input_dir = os.path.join(PROJECT_ROOT, 'data', portfolio_name, 'input')
    os.makedirs(input_dir, exist_ok=True)
    output_csv = os.path.join(input_dir, 'trades.csv')
    conversions_csv = os.path.join(input_dir, 'conversions.csv')

    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f, fieldnames=['Date', 'Ticker', 'Currency', 'Quantity', 'Price', 'Sector', 'Geography', 'Asset_Class', 'Status']
        )
        writer.writeheader()
        for row in trade_rows:
            writer.writerow(row)

    with open(conversions_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f, fieldnames=['Date', 'Currency_From', 'Currency_To', 'Amount', 'Rate']
        )
        writer.writeheader()
        for row in conversion_rows:
            writer.writerow(row)

    return output_csv


def main(args: List[str]) -> None:
    portfolios = args or ['core', 'benchmark']
    for name in portfolios:
        path = derive_trades_for_portfolio(name)
        logger.info(f"Derived trades for '{name}' -> {path}")


if __name__ == '__main__':
    main(sys.argv[1:])


