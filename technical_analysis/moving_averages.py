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


def moving_average(symbol, start, end, n, local=False, dir="") -> Optional[pd.DataFrame]:
    """
    Return DataFrame containing an <n>-day moving average for each trading data between <start> and <end>, inclusive.
    Note: the range given by start and end doesn't have to include enough data points for a full <n>-day moving average.
    The method will fetch enough data to calculate the average for each trading data in the given range, and then
    truncate the returned result.

    If <local>=True, assumes that <dir> is a string containing a path to a directory containing stock data.
    Files in this directory should be .csv's and have filename equal to the stock symbol whose data they are holding.
    This method assumes that the file <symbol>.csv exists in <dir>, if <local>=True.

    The returned DataFrame has index "Date" and one column of data, "Average"
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
    # We get data from the given range to ensure that we are returned at least enough data points to calculate an
    # <n>-day EMA for the day <start>. We use n + 3*n/7 below because weekends and holidays take up
    # somewhat less than 3/7ths of all days
    df = get_data(symbol, start - datetime.timedelta((n+1) + math.ceil((3 * (n+1)) / 7)), end, local=local, dir=dir)

    if df is None:
        return None

    # EMA is calculated by starting off with an n-day simple moving average
    average = DataFrame()
    average["Price"] = df["Adj Close"]
    EMA(average, "Price", n)

    return average[start:end]

def EMA(df: DataFrame, column: str, n: int):
    """
    Takes the given DataFrame and adds a column to it equal to the <n>-day EMA of the column with the label given by
    <column>
    """
    df["EMA"] = np.nan

    total = 0
    for i in range(n):
        total += df[column][df.index[i]]

    df.loc[df.index[n-1], "EMA"] = total / n

    smoothing = 2
    multiplier = smoothing / (1+n)
    for i in range(n, len(df.index)):
        df.loc[df.index[i], "EMA"] = df[column][df.index[i]] * multiplier + df["EMA"][df.index[i-1]] * (1 - multiplier)

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

                crosses.append(days[i+1])

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
