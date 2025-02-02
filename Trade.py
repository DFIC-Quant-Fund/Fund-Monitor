class Trade:
    def __init__(self, ticker, date, quantity, price):
        self.ticker = ticker
        self.date = date
        self.quantity = quantity
        self.price = price

    def __repr__(self):
        return f"Trade(ticker={self.ticker}, date={self.date}, quantity={self.quantity}, price={self.price})"