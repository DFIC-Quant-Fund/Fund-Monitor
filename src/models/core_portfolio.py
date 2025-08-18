import os
from typing import List
import pandas as pd
from .portfolio_base import PortfolioBase


class CorePortfolio(PortfolioBase):
    def __init__(self, start_date: str, end_date: str, starting_cash: float, folder_prefix: str = "core"):
        super().__init__(start_date, end_date, starting_cash, folder_prefix)



