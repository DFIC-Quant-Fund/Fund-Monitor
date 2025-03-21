import csv, os

'''
Modifies trades.csv input file 
Trades: Date, Ticker, Currency, Quantity, Price 
'''

input_folder = 'data/fund/input'
def add_trade(date, ticker, currency, quantity, price):
    new_row = [date, ticker, currency, quantity, price]
    with open(os.path.join(input_folder, 'trades.csv'), mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(new_row)

def delete_trade(date, ticker, currency, quantity, price):
    old_row = [date, ticker, currency, quantity, price]
    with open(os.path.join(input_folder, 'trades.csv'), mode="r", newline="") as f:
        reader = csv.reader(f)
        rows = [i for i in reader if i != old_row]
    with open(os.path.join(input_folder, 'trades.csv'), mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(rows)

def modify_trade():
    pass


def main():
    add_trade('2025-02-01', 'NVDA', 'USD', '61', '122.19')
    delete_trade('2023-12-28','XIU.TO','CAD','-111','31.9')


main()
