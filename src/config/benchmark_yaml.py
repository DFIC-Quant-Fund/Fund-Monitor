"""Shared parsing for `config/portfolio_definitions/benchmark.yaml`.

Target allocations are expressed per line (e.g. 35%, 0.35, or 35 meaning 35%).
Initial quantities use `STARTING_CASH` in `portfolio_csv_builder` (same constant
as the derive script); rebalancing targets come from these YAML weights.
"""

from __future__ import annotations

import os
from typing import Any, Dict

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
