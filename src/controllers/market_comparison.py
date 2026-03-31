"""
Market comparison metrics module.

This module calculates metrics that compare portfolio performance against market benchmarks.
It provides methods for:
- Beta calculation: Portfolio volatility relative to benchmark
- Alpha calculation: Excess return relative to benchmark
- Risk premium calculations
- Risk-adjusted return metrics
- Fama-French 3-factor model analysis

This module focuses on comparative analysis and assumes benchmark data is available.
"""

import pandas as pd
import numpy as np
import getFamaFrenchFactors as gff
from .benchmark import Benchmark
from .returns_calculator import ReturnsCalculator
from .risk_metrics import RiskMetrics
from ..config.logging_config import get_logger
from functools import lru_cache

# Set up logger for this module
logger = get_logger(__name__)


class MarketComparison:
    def __init__(self, df=None, useSpy: bool = False, risk_free_rate: float = 0.02):
        # Mirror Benchmark's constructor pattern: local path constant via Benchmark and a chosen source
        self.benchmark_instance = Benchmark(useSpy=useSpy)
        self.df = df
        self.RISK_FREE_RATE = risk_free_rate

    def beta(self):
        # Use the configured benchmark instance
        benchmark_df = self.benchmark_instance.benchmark_df

        daily_portfolio_return = self.df["pct_change"].dropna()

        # Handle empty or NaN values in benchmark pct_change
        if "pct_change" in benchmark_df.columns:
            daily_benchmark_return = benchmark_df["pct_change"].dropna()
        else:
            # If pct_change column doesn't exist, calculate it
            benchmark_df["pct_change"] = benchmark_df["Total Mkt Val"].pct_change()
            daily_benchmark_return = benchmark_df["pct_change"].dropna()

        # Align on dates to ensure matching observations
        aligned = daily_portfolio_return.align(daily_benchmark_return, join="inner")
        daily_portfolio_return, daily_benchmark_return = aligned
        if len(daily_portfolio_return) == 0:
            return 0.0

        daily_benchmark_var, _ = self.benchmark_instance.benchmark_variance()
        if daily_benchmark_var == 0:
            return 0.0  # Avoid division by zero

        covariance = daily_portfolio_return.cov(daily_benchmark_return)
        beta = covariance / daily_benchmark_var

        return beta

    def alpha(self):
        try:
            benchmark_returns = self.benchmark_instance.benchmark_average_return()
            annual_benchmark_return = benchmark_returns[1]  # Get the annualized return

            # Load portfolio data for ReturnsCalculator
            portfolio_performance = ReturnsCalculator(self.df)

            logger.debug(f"annual_benchmark_return: {annual_benchmark_return}")
            beta_value = self.beta()
            alpha = (
                portfolio_performance.annualized_average_return() - self.RISK_FREE_RATE
            ) - beta_value * (annual_benchmark_return - self.RISK_FREE_RATE)
            return alpha
        except Exception as e:
            logger.exception(f"Could not calculate alpha: {e}")
            return 0.0

    def portfolio_risk_premium(self):
        try:
            # Load portfolio data for ReturnsCalculator
            portfolio_performance = ReturnsCalculator(self.df)
            return (
                portfolio_performance.annualized_average_return() - self.RISK_FREE_RATE
            )
        except Exception as e:
            logger.exception(f"Could not calculate portfolio risk premium: {e}")
            return 0.0

    def treynor_ratio(self):
        try:
            return self.portfolio_risk_premium() / self.beta()
        except Exception as e:
            logger.exception(f"Could not calculate treynor ratio: {e}")
            return 0.0

    def information_ratio(self):
        try:
            # Read portfolio returns
            daily_portfolio_returns = self.df["pct_change"].dropna()
            daily_benchmark_returns = self.benchmark_instance.benchmark_df[
                "pct_change"
            ].dropna()

            # Align on dates to avoid NaNs due to mismatch
            aligned = daily_portfolio_returns.align(
                daily_benchmark_returns, join="inner"
            )
            daily_portfolio_returns, daily_benchmark_returns = aligned
            if len(daily_portfolio_returns) == 0:
                return 0.0, 0.0

            # Excess returns and IR
            excess_returns = daily_portfolio_returns - daily_benchmark_returns
            daily_information_ratio = excess_returns.mean() / excess_returns.std()
            annualized_information_ratio = daily_information_ratio * (252**0.5)
            return daily_information_ratio, annualized_information_ratio
        except Exception as e:
            logger.exception(f"Could not calculate information ratio: {e}")
            return 0.0, 0.0

    def risk_adjusted_return(self):
        try:
            risk_metrics = RiskMetrics(self.df, self.RISK_FREE_RATE)
            benchmark_vol = self.benchmark_instance.benchmark_volatility()[1]
            portfolio_volatility = risk_metrics.annualized_volatility()
            portfolio_risk_prem = self.portfolio_risk_premium()
            risk_adjusted_return = (
                portfolio_risk_prem * benchmark_vol / portfolio_volatility
                + self.RISK_FREE_RATE
            )

            return risk_adjusted_return
        except Exception as e:
            logger.exception(f"Could not calculate risk adjusted return: {e}")
            return 0.0

    @lru_cache(maxsize=1)
    def _get_monthly_returns_aligned_with_ff3(self):
        """
        Helper method to convert daily portfolio data to monthly returns
        and align with Fama-French 3-factor data.

        Returns:
            DataFrame with columns: Date, portfolio_return, Mkt-RF, SMB, HML, RF
        """
        try:
            # Get Fama-French 3-factor monthly data
            ff3_df = gff.famaFrench3Factor(frequency="m")
            if "date_ff_factors" in ff3_df.columns and "Date" not in ff3_df.columns:
                ff3_df.rename(columns={"date_ff_factors": "Date"}, inplace=True)
            ff3_df["Date"] = pd.to_datetime(ff3_df["Date"])

            # Convert daily portfolio data to monthly
            portfolio_df = self.df.copy()
            if "Date" not in portfolio_df.columns:
                portfolio_df.reset_index(inplace=True)

            portfolio_df["Date"] = pd.to_datetime(portfolio_df["Date"])
            portfolio_df.set_index("Date", inplace=True)

            # Resample to month-end and calculate monthly returns
            # Use the portfolio value column (adjust based on your column name)
            value_col = (
                "Total_Portfolio_Value"
                if "Total_Portfolio_Value" in portfolio_df.columns
                else "Total Mkt Val"
            )
            monthly_values = portfolio_df[value_col].resample("ME").last()
            monthly_returns = monthly_values.pct_change().dropna()

            # Create DataFrame with monthly returns
            monthly_portfolio_df = pd.DataFrame(
                {
                    "Date": monthly_returns.index,
                    "portfolio_return": monthly_returns.values,
                }
            )

            # Merge with FF3 factors on Date
            merged_df = pd.merge(monthly_portfolio_df, ff3_df, on="Date", how="inner")

            # Keep only required columns and coerce to numeric
            required_cols = ["portfolio_return", "Mkt-RF", "SMB", "HML", "RF"]
            for col in required_cols:
                if col not in merged_df.columns:
                    logger.warning(f"Missing expected FF3 column: {col}")
                    return pd.DataFrame()
                merged_df[col] = pd.to_numeric(merged_df[col], errors="coerce")
            merged_df = merged_df.dropna(subset=required_cols)

            # Factor feeds can come in either decimal (0.01) or percent (1.0) units.
            # Normalize to decimals so portfolio and factors use consistent units.
            factor_cols = ["Mkt-RF", "SMB", "HML", "RF"]
            max_abs_factor = merged_df[factor_cols].abs().max().max()
            if pd.notna(max_abs_factor) and max_abs_factor > 1:
                merged_df[factor_cols] = merged_df[factor_cols] / 100.0

            logger.debug(f"Aligned {len(merged_df)} months of data for FF3 analysis")
            return merged_df

        except Exception as e:
            logger.exception(f"Could not align monthly returns with FF3 factors: {e}")
            return pd.DataFrame()

    @lru_cache(maxsize=1)
    def _ff3_regression_results(self):
        """
        Fit the canonical Fama-French 3-factor regression:
            (Rp - Rf) = alpha + b_m*(Mkt-RF) + b_s*SMB + b_h*HML + e

        Returns:
            dict with keys:
                market_factor, size_factor, value_factor, alpha, r_squared, observations
            or {} when data is insufficient.
        """
        try:
            merged_df = self._get_monthly_returns_aligned_with_ff3()
            if merged_df.empty:
                return {}

            min_observations = 12
            if len(merged_df) < min_observations:
                logger.warning(
                    f"Insufficient data for FF3 regression: {len(merged_df)} observations "
                    f"(need at least {min_observations})"
                )
                return {}

            y = (merged_df["portfolio_return"] - merged_df["RF"]).to_numpy(dtype=float)
            x_factors = merged_df[["Mkt-RF", "SMB", "HML"]].to_numpy(dtype=float)
            x = np.column_stack(
                [np.ones(len(x_factors)), x_factors]
            )  # intercept + 3 factors

            # OLS coefficients via least squares
            coefs, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
            alpha, beta_mkt, beta_smb, beta_hml = coefs

            y_hat = x @ coefs
            residuals = y - y_hat
            ss_res = float(np.sum(residuals**2))
            ss_tot = float(np.sum((y - y.mean()) ** 2))
            r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

            return {
                "market_factor": float(beta_mkt),
                "size_factor": float(beta_smb),
                "value_factor": float(beta_hml),
                "alpha": float(alpha),  # monthly alpha (decimal)
                "r_squared": float(r_squared),
                "observations": int(len(merged_df)),
            }
        except Exception as e:
            logger.exception(f"Could not fit FF3 regression: {e}")
            return {}

    def fama_french_3factor_regression(self):
        """Public wrapper returning FF3 regression outputs."""
        return self._ff3_regression_results()

    def market_factor(self):
        """
        Calculate the market factor (beta) using Fama-French methodology.

        This measures the portfolio's sensitivity to overall market movements.

        Returns:
            float: Market factor (beta_market)
                  > 1.0 = More volatile than market
                  < 1.0 = Less volatile than market
                  = 1.0 = Moves with market
        """
        try:
            results = self._ff3_regression_results()
            return float(results.get("market_factor", 0.0))

        except Exception as e:
            logger.exception(f"Could not calculate market factor: {e}")
            return 0.0

    def size_factor(self):
        """
        Calculate the size factor (SMB - Small Minus Big).

        This measures the portfolio's tilt toward small-cap or large-cap stocks.

        Returns:
            float: Size factor (beta_SMB)
                  > 0 = Small-cap tilt (outperforms when small caps beat large caps)
                  < 0 = Large-cap tilt (outperforms when large caps beat small caps)
                  ≈ 0 = Neutral to size
        """
        try:
            results = self._ff3_regression_results()
            return float(results.get("size_factor", 0.0))

        except Exception as e:
            logger.exception(f"Could not calculate size factor: {e}")
            return 0.0

    def value_factor(self):
        """
        Calculate the value factor (HML - High Minus Low).

        This measures the portfolio's tilt toward value or growth stocks.

        Returns:
            float: Value factor (beta_HML)
                  > 0 = Value tilt (outperforms when value beats growth)
                  < 0 = Growth tilt (outperforms when growth beats value)
                  ≈ 0 = Neutral to value/growth
        """
        try:
            results = self._ff3_regression_results()
            return float(results.get("value_factor", 0.0))

        except Exception as e:
            logger.exception(f"Could not calculate value factor: {e}")
            return 0.0
