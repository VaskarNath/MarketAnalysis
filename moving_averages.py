import datetime
import matplotlib.pyplot as plt
import sys
import pandas as pd
from pandas import DataFrame
from matplotlib import style
from data_requests import get_data

"""
Return the n-day simple moving average for the given security, over the given range
as a DataFrame with index "Date" and one column "Average"
"""


def moving_average(symbol, start, end, n):
    df = get_data(symbol, start, end)

    close_prices = DataFrame()
    close_prices["Average"] = df["Adj Close"].rolling(window=n).mean()

    return close_prices


"""
Check for a cross by the short-day moving average above the long-day moving average
within the last five days of trading. Returns the date on which the short-day average
closed above the long-day average.
"""
def cross_above(symbol: str, short: int, long: int) -> datetime.datetime:
    print(f"Checking {symbol}...")

    # We use date subtraction for the start argument to ensure that there's enough data for the last 5 days of trading,
    # because weekends and holidays have the potential to lead us to fetch too few data points
    short_average = moving_average(symbol, datetime.datetime.today() - datetime.timedelta(7 + 2*long),
                                   datetime.datetime.today(), short)
    long_average = moving_average(symbol, datetime.datetime.today() - datetime.timedelta(7 + 2*long),
                                  datetime.datetime.today(), long)

    days = short_average.tail(5).index

    for i in range(len(days) - 1):
        if (short_average["Average"][days[i]] <= long_average["Average"][days[i]]
                and short_average["Average"][days[i + 1]] > long_average["Average"][days[i + 1]]):
            print("============|============")
            print("Cross above found: " + symbol)
            print("On day " + str(days[i+1]))
            print("============|============")
            return days[i+1]


def symbols_from_json():
    f = open()

"""
This script is run by passing in one command-line argument: the name of the source file from which it loads all the
stock tickers for analysis. This file should be a .csv file, and the list of stock tickers should be under a column
named "Symbol"
"""
if __name__ == '__main__':
    now = datetime.datetime.now()
    print(f"Started {now.hour}:{now.minute}:{now.second}")
    style.use("fivethirtyeight")

    securities = pd.read_csv(sys.argv[1])["Symbol"].to_list()

    for symbol in securities:
        if(symbol.isalpha()):
            cross_above(symbol, 20, 50)

    now = datetime.datetime.now()
    print(f"Finished {now.hour}:{now.minute}:{now.second}")