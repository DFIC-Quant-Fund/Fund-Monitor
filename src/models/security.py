class Security:
    def __init__(self, ticker: str, sector: str, geography: str, currency: str, status: str = 'open'):
        self.ticker = ticker
        self.sector = sector
        self.geography = geography
        self.currency = currency
        self.status = status
        
    def get_ticker(self) -> str:
        return self.ticker
    
    def get_sector(self) -> str:
        return self.sector
    
    def get_geography(self) -> str:
        return self.geography
    
    def get_currency(self) -> str:
        return self.currency
    
    def get_status(self) -> str:
        return self.status

    def set_sector(self, sector: str):
        self.sector = sector

    def set_geography(self, geography: str):
        self.geography = geography

    def set_status(self, status: str):
        self.status = status