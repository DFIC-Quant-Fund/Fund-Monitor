"""Shared parsing for `config/portfolio_definitions/benchmark.yaml`.

Target allocations are expressed per line (e.g. 35%, 0.35, or 35 meaning 35%).
Initial quantities use `STARTING_CASH` in `portfolio_csv_builder` (same constant
as the derive script); rebalancing targets come from these YAML weights.
"""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Any, Dict, Optional

import yaml

BENCHMARK_YAML_REL = ("config", "portfolio_definitions", "benchmark.yaml")


def _benchmark_yaml_path(project_root: str) -> str:
    return os.path.join(project_root, *BENCHMARK_YAML_REL)


def parse_allocation_fraction(value: Any) -> float:
    """Return weight in (0, 1], e.g. 35% -> 0.35, 0.35 -> 0.35, 35 -> 0.35."""
    if value is None:
        raise ValueError("target_allocation is missing")
    if isinstance(value, (int, float)):
        x = float(value)
        if x > 1.0:
            return x / 100.0
        return x
    s = str(value).strip()
    if s.endswith("%"):
        return float(s[:-1].strip()) / 100.0
    x = float(s)
    if x > 1.0:
        return x / 100.0
    return x


def _load_raw(project_root: str) -> dict:
    path = _benchmark_yaml_path(project_root)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Benchmark YAML not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_benchmark_target_weights(project_root: str) -> Dict[str, float]:
    """Ticker -> target weight (sum ~ 1) from Buy rows with `target_allocation`."""
    data = _load_raw(project_root)
    txs = data.get("transactions") or []
    weights: Dict[str, float] = {}
    for tx in txs:
        if str(tx.get("type", "")).strip().lower() != "buy":
            continue
        if tx.get("target_allocation") is None:
            continue
        ticker = str(tx.get("ticker", "")).strip()
        if not ticker:
            continue
        w = parse_allocation_fraction(tx.get("target_allocation"))
        weights[ticker] = weights.get(ticker, 0.0) + w

    if not weights:
        return {}

    s = sum(weights.values())
    if abs(s - 1.0) > 0.02:
        raise ValueError(
            f"Benchmark target allocations must sum to 1.0 (got {s:.6f}); "
            "check config/portfolio_definitions/benchmark.yaml"
        )
    if abs(s - 1.0) > 1e-6:
        weights = {k: v / s for k, v in weights.items()}
    return weights


def _display_asset_class_label(asset_class: str) -> str:
    """Short labels for UI (e.g. ETF Equity -> Equity)."""
    if not asset_class or not str(asset_class).strip():
        return "Other"
    a = str(asset_class).strip()
    lower = a.lower()
    if "fixed income" in lower:
        return "Fixed Income"
    if "equity" in lower:
        return "Equity"
    return a


def format_benchmark_target_allocation_caption(project_root: str) -> Optional[str]:
    """Return a line like 'Target Allocation: 70% Equity, 30% Fixed Income', or None."""
    try:
        data = _load_raw(project_root)
    except OSError:
        return None
    txs = data.get("transactions") or []
    by_class: Dict[str, float] = defaultdict(float)
    for tx in txs:
        if str(tx.get("type", "")).strip().lower() != "buy":
            continue
        if tx.get("target_allocation") is None:
            continue
        ac = tx.get("asset_class") or tx.get("sector") or ""
        label = _display_asset_class_label(str(ac))
        by_class[label] += parse_allocation_fraction(tx.get("target_allocation"))

    if not by_class:
        return None

    total = sum(by_class.values())
    if total <= 0:
        return None

    # Descending by weight, then label
    items = sorted(by_class.items(), key=lambda x: (-x[1], x[0]))
    parts: list[str] = []
    for label, frac in items:
        pct = 100.0 * frac / total
        if abs(pct - round(pct)) < 0.05:
            parts.append(f"{int(round(pct))}% {label}")
        else:
            parts.append(f"{pct:.1f}% {label}")
    return "Target Allocation: " + ", ".join(parts)
