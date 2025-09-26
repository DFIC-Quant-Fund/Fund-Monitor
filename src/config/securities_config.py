"""
Securities configuration loader.

This module loads the authoritative securities configuration from core.yaml
and provides a clean interface for accessing fund, sector, and geography information.
"""

import yaml
from typing import Dict, List, Optional, NamedTuple
from enum import Enum
from .logging_config import get_logger

class Fund(Enum):
    """Fund classifications from core.yaml"""
    MACRO_FUND = "Macro Fund"
    INDUSTRIALS_FUND = "Industrials Fund"
    RESOURCES_FUND = "Resources Fund"
    C_AND_H_FUND = "C&H Fund"
    TMT_FUND = "TMT Fund"
    FINANCIALS_FUND = "Financials Fund"

class AuthoritativeSector(Enum):
    """Authoritative sector classifications from core.yaml"""
    FIXED_INCOME = "Fixed Income"
    EQUITY = "Equity"
    INDUSTRIALS = "Industrials"
    UTILITIES = "Utilities"
    MATERIALS = "Materials"
    CONSUMER_STAPLES = "Consumer Staples"
    REAL_ESTATE = "Real Estate"
    CONSUMER_DISCRETIONARY = "Consumer Discretionary"
    HEALTHCARE = "Healthcare"
    FINANCIALS = "Financials"
    TECHNOLOGY = "Technology"
    COMMUNICATION_SERVICES = "Communication Services"

class Geography(Enum):
    """Geography classifications from core.yaml"""
    CAN = "CAN"
    US = "US"

class SecurityInfo(NamedTuple):
    """Security information from core.yaml"""
    ticker: str
    fund: Fund
    sector: AuthoritativeSector
    geography: Geography

class SecuritiesConfig:
    """Configuration loader for securities data"""
    
    def __init__(self, config_path: str = "config/portfolio_definitions/core.yaml"):
        self.config_path = config_path
        self._securities_data: Dict[str, SecurityInfo] = {}
        self._funds_data: Dict[str, str] = {}
        self.logger = get_logger(__name__)
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Load funds data
            if 'funds' in config:
                for fund in config['funds']:
                    self._funds_data[fund['name']] = fund.get('thesis', '')
            
            # Load securities data
            if 'securities' in config:
                for security in config['securities']:
                    if isinstance(security, dict) and 'ticker' in security:
                        try:
                            security_info = SecurityInfo(
                                ticker=security['ticker'],
                                fund=Fund(security['fund']),
                                sector=AuthoritativeSector(security['sector']),
                                geography=Geography(security['geography'])
                            )
                            self._securities_data[security['ticker']] = security_info
                        except (ValueError, KeyError) as e:
                            self.logger.warning(f"Could not parse security {security.get('ticker', 'unknown')}: {e}")
                            
        except Exception as e:
            self.logger.exception(f"Error loading securities config: {e}")
    
    def get_security_info(self, ticker: str) -> Optional[SecurityInfo]:
        """Get security information for a ticker"""
        return self._securities_data.get(ticker)
    
    def get_sector_for_ticker(self, ticker: str) -> Optional[AuthoritativeSector]:
        """Get authoritative sector for a ticker"""
        security_info = self.get_security_info(ticker)
        return security_info.sector if security_info else None
    
    def get_fund_for_ticker(self, ticker: str) -> Optional[Fund]:
        """Get fund for a ticker"""
        security_info = self.get_security_info(ticker)
        return security_info.fund if security_info else None
    
    def get_geography_for_ticker(self, ticker: str) -> Optional[Geography]:
        """Get geography for a ticker"""
        security_info = self.get_security_info(ticker)
        return security_info.geography if security_info else None
    
    def get_all_securities(self) -> Dict[str, SecurityInfo]:
        """Get all securities information"""
        return self._securities_data.copy()
    
    def get_securities_by_fund(self, fund: Fund) -> List[SecurityInfo]:
        """Get all securities for a specific fund"""
        return [info for info in self._securities_data.values() if info.fund == fund]
    
    def get_securities_by_sector(self, sector: AuthoritativeSector) -> List[SecurityInfo]:
        """Get all securities for a specific sector"""
        return [info for info in self._securities_data.values() if info.sector == sector]
    
    def get_fund_thesis(self, fund_name: str) -> str:
        """Get fund thesis"""
        return self._funds_data.get(fund_name, "")
    
    def get_all_funds(self) -> Dict[str, str]:
        """Get all funds and their theses"""
        return self._funds_data.copy()

# Global instance
securities_config = SecuritiesConfig()
