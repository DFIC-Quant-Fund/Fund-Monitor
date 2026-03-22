"""Derive input CSVs from YAML portfolio definitions.

Reads `config/portfolio_definitions/<portfolio>.yaml`, normalizes transactions,
and writes sorted CSVs in `data/<portfolio>/input`:
  - trades.csv with headers: Date, Ticker, Currency, Quantity, Price (Buy/Sell only)
  - conversions.csv with headers: Date, Currency_From, Currency_To, Amount, Rate

Benchmark: when a Buy lists `target_allocation` (e.g. 35% or 0.35), quantity
uses `STARTING_CASH` from `portfolio_csv_builder` (same as the simulation):
notional CAD = STARTING_CASH * weight, then converted to shares using the row
`price` and USD/CAD (CAD=X) on that date.

Usage:
    python scripts/derive_trades_from_yaml.py [portfolio ...]
"""

import csv
import os
import sys
from typing import Any, Dict, List

import pandas as pd
import yaml
import yfinance as yf

# Add project root to Python path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config.benchmark_yaml import parse_allocation_fraction
from src.config.logging_config import get_logger

try:
    from src.models.portfolio_csv_builder import STARTING_CASH
except ImportError:
    from models.portfolio_csv_builder import STARTING_CASH

logger = get_logger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

_usd_cad_cache: Dict[str, float] = {}


def _usd_cad_rate_on_date(trade_date: str) -> float:
    """CAD per USD (Yahoo CAD=X close), first session on or after trade_date."""
    if trade_date in _usd_cad_cache:
        return _usd_cad_cache[trade_date]
    dt = pd.Timestamp(trade_date)
    hist = yf.Ticker("CAD=X").history(start=dt, end=dt + pd.Timedelta(days=7))
    if hist.empty:
        raise ValueError(f"No USD/CAD (CAD=X) data on or after {trade_date}")
    rate = float(hist["Close"].iloc[0])
    _usd_cad_cache[trade_date] = rate
    logger.info(f"USD/CAD (CAD=X) for {trade_date}: {rate:.6f}")
    return rate


def _load_portfolio_yaml(portfolio_name: str) -> dict:
    yaml_path = os.path.join(
        PROJECT_ROOT,
        "config",
        "portfolio_definitions",
        f"{portfolio_name}.yaml",
    )
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(
            f"YAML not found for portfolio '{portfolio_name}': {yaml_path}"
        )

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    transactions = data.get("transactions", []) or []
    if not isinstance(transactions, list):
        raise ValueError(f"'transactions' must be a list in {yaml_path}")
    return data


def _quantity_from_target_allocation(
    tx: Dict[str, Any],
    starting_cash: float,
) -> float:
    """Notional in CAD = starting_cash * weight; convert to share quantity."""
    weight = parse_allocation_fraction(tx.get("target_allocation"))
    value_cad = starting_cash * weight
    price = float(tx.get("price"))
    if price <= 0:
        raise ValueError(f"Invalid price for {tx.get('ticker')}: {price}")
    currency = str(tx.get("currency", "")).strip().upper()
    date = str(tx.get("date", "")).strip()

    if currency == "USD":
        usd_cad = _usd_cad_rate_on_date(date)
        return value_cad / (price * usd_cad)
    if currency == "CAD":
        return value_cad / price
    raise ValueError(
        f"Unsupported currency for target_allocation sizing: {currency!r} "
        f"(ticker {tx.get('ticker')})"
    )


def _normalize_row(tx: Dict[str, Any], quantity: float) -> Dict[str, Any]:
    tx_type = str(tx.get("type", "")).strip().lower()
    date = str(tx.get("date", "")).strip()
    ticker = str(tx.get("ticker", "")).strip()
    currency = str(tx.get("currency", "")).strip().upper()
    price = float(tx.get("price"))
    if tx_type == "sell":
        quantity = -abs(quantity)
    else:
        quantity = abs(quantity)

    sector = str(tx.get("sector", "")).strip()
    geography = str(tx.get("geography", "")).strip()
    asset_class = str(tx.get("asset_class", "")).strip()
    status = str(tx.get("status", "")).strip()

    return {
        "Date": date,
        "Ticker": ticker,
        "Currency": currency,
        "Quantity": quantity,
        "Price": price,
        "Sector": sector,
        "Geography": geography,
        "Asset_Class": asset_class,
        "Status": status,
    }


def _normalize_conversion_row(tx: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a conversion transaction into a standardized dict.

    Rate semantics: units of Currency_To per 1 unit of Currency_From.
    Example: USD->CAD at 1.3821 means 1 USD = 1.3821 CAD.
    """
    date = str(tx.get("date", "")).strip()
    currency_from = str(tx.get("currency_from", "")).strip().upper()
    currency_to = str(tx.get("currency_to", "")).strip().upper()
    amount = float(tx.get("amount"))
    rate_val = tx.get("conversion_rate")
    rate = float(rate_val) if rate_val is not None else float("nan")

    logger.info(
        f"Conversion parsed: {amount} {currency_from} -> {currency_to} at rate {rate}"
    )

    return {
        "Date": date,
        "Currency_From": currency_from,
        "Currency_To": currency_to,
        "Amount": amount,
        "Rate": rate,
    }


def derive_trades_for_portfolio(portfolio_name: str) -> str:
    """Derive input CSVs (trades, conversions) from YAML and return trades path."""
    data = _load_portfolio_yaml(portfolio_name)
    transactions = data.get("transactions", []) or []

    trade_rows: List[Dict[str, Any]] = []
    conversion_rows: List[Dict[str, Any]] = []

    for tx in transactions:
        tx_type = str(tx.get("type", "")).strip().lower()
        if tx_type == "conversion":
            conversion_rows.append(_normalize_conversion_row(tx))
            continue

        has_alloc = tx.get("target_allocation") is not None
        has_qty = tx.get("quantity") is not None

        if has_alloc and has_qty:
            logger.warning(
                f"Transaction {tx.get('ticker')} has both quantity and target_allocation; "
                "using target_allocation."
            )

        if has_alloc:
            qty = _quantity_from_target_allocation(tx, STARTING_CASH)
        elif has_qty:
            qty = float(tx.get("quantity"))
        else:
            raise ValueError(
                f"Buy/Sell must have either quantity or target_allocation "
                f"(ticker {tx.get('ticker')}, portfolio '{portfolio_name}')"
            )

        trade_rows.append(_normalize_row(tx, qty))

    trade_rows.sort(key=lambda r: (r["Date"], r["Ticker"]))
    conversion_rows.sort(key=lambda r: (r["Date"], r["Currency_From"], r["Currency_To"]))

    input_dir = os.path.join(PROJECT_ROOT, "data", portfolio_name, "input")
    os.makedirs(input_dir, exist_ok=True)
    output_csv = os.path.join(input_dir, "trades.csv")
    conversions_csv = os.path.join(input_dir, "conversions.csv")

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "Date",
                "Ticker",
                "Currency",
                "Quantity",
                "Price",
                "Sector",
                "Geography",
                "Asset_Class",
                "Status",
            ],
        )
        writer.writeheader()
        for row in trade_rows:
            writer.writerow(row)

    with open(conversions_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["Date", "Currency_From", "Currency_To", "Amount", "Rate"]
        )
        writer.writeheader()
        for row in conversion_rows:
            writer.writerow(row)

    return output_csv


def main(args: List[str]) -> None:
    portfolios = args or ["core", "benchmark"]
    for name in portfolios:
        path = derive_trades_for_portfolio(name)
        logger.info(f"Derived trades for '{name}' -> {path}")


if __name__ == "__main__":
    main(sys.argv[1:])
