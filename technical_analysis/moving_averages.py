import datetime
import math
import sys
import threading
import time
from typing import Optional, List

import pandas as pd
import numpy as np
from pandas import DataFrame

sys.path.append("../")
from data_requests import get_data
from tools.messaging import Listener, Message
from tools.synced_list import SyncedList

"""
The number of threads that this script will use to accomplish its task.
"""
NUM_THREADS = 3

MACD_SHORT_AVERAGE = 12
MACD_LONG_AVERAGE = 26
MACD_SIGNAL_PERIOD = 9


def moving_average(symbol, start, end, n, local=False, dir="") -> Optional[pd.DataFrame]:
    """
    Return DataFrame containing an <n>-day moving average for each trading day between <start> and <end>, inclusive.
    Note: the range given by start and end doesn't have to include enough data points for a full <n>-day moving average.
    The method will fetch enough data to calculate the average for each trading data in the given range, and then
    truncate the returned result.

    If <local>=True, assumes that <dir> is a string containing a path to a directory containing stock data.
    Files in this directory should be .csv's and have filename equal to the stock symbol whose data they are holding.
    This method assumes that the file <symbol>.csv exists in <dir>, if <local>=True.

    The returned DataFrame has index "Date" and one column of data, "Average".

    Returns None in the event of an error fetching data.
    """
    try:
        # We get data from the given range to ensure that we are returned at least enough data points to calculate an
        # <n>-day moving average for the day <start>. We use n + 3*n/7 below because weekends and holidays take up
        # somewhat less than 3/7ths of all days
        df = get_data(symbol, start - datetime.timedelta(n + math.ceil((3 * n) / 7)), end, local=local, dir=dir)
        if df is None:
            return None
        average = DataFrame()
        average["Average"] = df["Adj Close"].rolling(window=n).mean()

        return average[start:end]
    except KeyError:
        return None


def EMA_from_symbol(symbol, start, end, n, local=False, dir="") -> Optional[DataFrame]:
    """
    Return a date-indexed DataFrame with one column: "EMA". "EMA" will contain an <n>-day exponential moving average of
    closing price, for the range of dates given by <start> and <end>.

    If <local>=True, assumes that <dir> is a string containing a path to a directory containing stock data.
    Files in this directory should be .csv's and have filename equal to the stock symbol whose data they are holding.
    This method assumes that the file <symbol>.csv exists in <dir>, if <local>=True.

    Returns None in the event of an error fetching data.
    """
    # We get data from the given range to ensure that we are returned at least enough data points to calculate an
    # <n>-day EMA for the day <start>. We use (n+1) + 3*(n+1)/7 below because weekends and holidays take up
    # somewhat less than 3/7ths of all days
    df = get_data(symbol, start - datetime.timedelta((n + 1) + math.ceil((3 * (n + 1)) / 7)), end, local=local, dir=dir)

    if df is None:
        return None

    average = DataFrame()
    average["Price"] = df["Adj Close"]
    EMA(average, "Price", "EMA", n)
    average.drop(labels="Price", axis=1, inplace=True)

    return average[start:end]


def EMA(df: DataFrame, column: str, result: str, n: int):
    """
    Takes the given DataFrame and adds a column to it equal to the <n>-day EMA of the column with the label given by
    <column>. The new column has label <result>. Assumes there are enough data points to calculate an <n>-day EMA.

    The first n-1 data points of the new <result> column will have value np.nan.
    """
    df[result] = np.nan

    total = 0
    for i in range(n):
        total += df[column][df.index[i]]

    # EMA is calculated by starting off with an n-day simple moving average
    df.loc[df.index[n - 1], result] = total / n

    smoothing = 2
    multiplier = smoothing / (1 + n)
    for i in range(n, len(df.index)):
        df.loc[df.index[i], result] = df[column][df.index[i]] * multiplier + df[result][df.index[i - 1]] * (
                    1 - multiplier)


def MACD(symbol: str, start: datetime.datetime, end: datetime.datetime, local=False, dir="") -> Optional[DataFrame]:
    # We need to fetch enough data so that we can compute MACD for the range <start>-<end>. That means, including
    # weekends and holidays, we need at least MACD_LONG_AVERAGE + 3 * MACD_LONG_AVERAGE / 7 data points to be able
    # to calculate MACD for the first day of our range. But, we also need enough data points to then take an EMA of the
    # MACD, for the signal line, of length MACD_SIGNAL_PERIOD. So we need to fetch extra data to compute enough MACD
    # points to also do that.
    price_data = get_data(symbol, start - datetime.timedelta(MACD_LONG_AVERAGE + 3 * MACD_LONG_AVERAGE / 7 + (MACD_SIGNAL_PERIOD+1) + 3*(MACD_SIGNAL_PERIOD) / 7 ), end,
                          local=local, dir=dir)

    if price_data is None:
        return None

    df = DataFrame()
    df["Price"] = price_data["Adj Close"]
    EMA(df, "Price", "Short", MACD_SHORT_AVERAGE)
    EMA(df, "Price", "Long", MACD_LONG_AVERAGE)
    df["MACD"] = df["Short"] - df["Long"]

    # So now we've got a DataFrame with columns "Price", "Short", "Long", and "MACD". Because "Short" and "Long" are
    # moving averages, they each have some number of NaN values at the beginning. And because "MACD" = "Short" - "Long",
    # so does "MACD". That means that when we calculate an EMA of "MACD" below, it'll get messed up unless we remove the
    # NaN values. So we do that first.

    # Iterate until i points to the first row that contains an actual value for MACD
    i = 0
    while np.isnan(df["MACD"][df.index[i]]):
        i += 1

    # Chop off all the NaN values
    df = df[df.index[i]:]

    EMA(df, "MACD", "Signal", MACD_SIGNAL_PERIOD)

    df.drop(labels=["Short", "Long"], axis=1, inplace=True)
    return df[start:end]


def cross_above(symbol: str, listener: Listener, short: int, long: int, start: datetime.datetime,
                end: datetime.datetime, local=False, dir="") -> List[datetime.datetime]:
    """
    Check for a cross by the <short>-day moving average above the <long>-day moving average some time between <start>
    and <end>. Prints a message to the console whenever a cross is found, identifying the day on which the short-term
    moving average closed above the long-term moving average. Each such day is also added to a list, which is returned
    by the method.

    If <local>=True, assumes that <dir> is a string containing a path to a directory containing stock data.
    Files in this directory should be .csv's and have filename equal to the stock symbol whose data they are holding.
    This method assumes that the file <symbol>.csv exists in <dir>, if <local>=True.
    """
    msg = Message()
    msg.add_line(f"Checking {symbol}...")
    listener.send(msg)

    short_average = moving_average(symbol, start, end, short, local=local, dir=dir)
    long_average = moving_average(symbol, start, end, long, local=local, dir=dir)

    if short_average is not None and long_average is not None:

        days = short_average.index

        crosses = []
        for i in range(len(days) - 1):
            if (short_average["Average"][days[i]] <= long_average["Average"][days[i]]
                    and short_average["Average"][days[i + 1]] > long_average["Average"][days[i + 1]]):
                msg.reset()
                msg.add_line("============|============")
                msg.add_line("Cross above found: " + symbol)
                msg.add_line("On day " + str(days[i + 1]))
                msg.add_line("============|============")
                listener.send(msg)

                crosses.append(days[i + 1])

        return crosses
    else:
        msg.reset()
        msg.add_line("******************************************************")
        msg.add_line("Couldn't get data for " + symbol)
        msg.add_line("******************************************************")
        listener.send(msg)
        return []


def check_for_cross(lst: SyncedList, listener: Listener, short: int, long: int, start: datetime.datetime,
                    end: datetime.datetime):
    """
    Check for crosses of the <short>-day moving average above the <long>-day moving average in the last five days of
    trading. <lst> should be a SyncedList of stock symbols, and listener is what the threads spawned to accomplish the
    task will use to communicate with the console. 
    """
    symbol = lst.pop()
    while symbol is not None:
        cross_above(symbol, listener, short, long, start, end)
        symbol = lst.pop()


def analyze_symbols(lst: SyncedList, short: int, long: int, start: datetime.datetime, end: datetime.datetime) -> List[
    threading.Thread]:
    """
    Spawns NUM_THREADS threads to look for crosses in the given SyncedList of symbols. Returns a list of all threads
    spawned.
    """
    listener = Listener()

    threads = []
    # Start NUM_THREADS different threads, each drawing from the same central list of symbols, to look for golden
    # crosses
    for i in range(NUM_THREADS):
        x = threading.Thread(target=check_for_cross, args=(lst, listener, short, long, start, end))
        x.start()
        threads.append(x)

    return threads


"""
This script is run by passing in one command-line argument: the name of the source file from which it loads all the
stock tickers for analysis. This file should simply contain a list of stock tickers, with one ticker per line.
"""
if __name__ == '__main__':
    securities = []

    f = open(sys.argv[1], "r")
    for line in f:
        line = line.strip()
        securities.append(line)

    lst = SyncedList(securities)

    start = time.time()
    threads = analyze_symbols(lst, 20, 50, datetime.datetime.today() - datetime.timedelta(7), datetime.datetime.today())
    main_thread = threading.current_thread()
    for thread in threads:
        if thread is not main_thread:
            thread.join()

    end = time.time()

    print("Time taken: " + str(end - start))
