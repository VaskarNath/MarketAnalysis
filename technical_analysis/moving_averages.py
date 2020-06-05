import datetime
import sys
import threading
import time
from typing import Optional, List

import pandas as pd
from pandas import DataFrame

from data_requests import get_data
from tools.messaging import Listener, Message
from tools.synced_list import SyncedList

"""
The number of threads that this script will use to accomplish its task.
"""
NUM_THREADS = 3


def moving_average(symbol, start, end, n) -> Optional[pd.DataFrame]:
    """
    Return DataFrame containing an <n>-day moving average over the given range, from <start> to <end>. Note that
    depending on <n>, there will be days close to <start> that do not have entries as there aren't enough historical
    data points to compute a  moving average.

    The returned DataFrame has index "Date" and one column of data, "Average"
    """
    try:
        df = get_data(symbol, start, end)
        close_prices = DataFrame()
        close_prices["Average"] = df["Adj Close"].rolling(window=n).mean()

        return close_prices
    except KeyError:
        return None


def cross_above(symbol: str, listener: Listener, short: int, long: int) -> datetime.datetime:
    """
    Check for a cross by the <short>-day moving average above the <long>-day moving average
    within the last five days of trading. Returns the date on which the <short>-day average
    closed above the <long>-day average.
    """
    msg = Message()
    msg.add_line(f"Checking {symbol}...")
    listener.send(msg)

    # We use date subtraction for the start argument to ensure that there's enough data for the last 5 days of trading,
    # because weekends and holidays have the potential to lead us to fetch too few data points
    short_average = moving_average(symbol, datetime.datetime.today() - datetime.timedelta(7 + 2 * long),
                                   datetime.datetime.today(), short)
    long_average = moving_average(symbol, datetime.datetime.today() - datetime.timedelta(7 + 2 * long),
                                  datetime.datetime.today(), long)

    if short_average is not None and long_average is not None:

        days = short_average.tail(5).index

        for i in range(len(days) - 1):
            if (short_average["Average"][days[i]] <= long_average["Average"][days[i]]
                    and short_average["Average"][days[i + 1]] > long_average["Average"][days[i + 1]]):
                msg = Message()
                msg.add_line("============|============")
                msg.add_line("Cross above found: " + symbol)
                msg.add_line("On day " + str(days[i + 1]))
                msg.add_line("============|============")
                listener.send(msg)
                return days[i + 1]
    else:
        msg = Message()
        msg.add_line("******************************************************")
        msg.add_line("Couldn't get data for " + symbol)
        msg.add_line("******************************************************")
        listener.send(msg)


def check_for_cross(lst: SyncedList, listener: Listener, short: int, long: int):
    """
    Check for crosses of the <short>-day moving average above the <long>-day moving average in the last five days of
    trading. <lst> should be a SyncedList of stock symbols, and listener is what the threads spawned to accomplish the
    task will use to communicate with the console. 
    """
    symbol = lst.pop()
    while symbol is not None:
        cross_above(symbol, listener, short, long)
        symbol = lst.pop()


def analyze_symbols(lst: SyncedList, short: int, long: int) -> List[threading.Thread]:
    """
    Spawns NUM_THREADS threads to look for crosses in the given SyncedList of symbols. Returns a list of all threads
    spawned.
    """
    listener = Listener()

    threads = []
    # Start 5 different threads, each drawing from the same central list of symbols, to look for golden crosses
    for i in range(NUM_THREADS):
        x = threading.Thread(target=check_for_cross, args=(lst, listener, short, long))
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
    threads = analyze_symbols(lst, 20, 50)
    main_thread = threading.current_thread()
    for thread in threads:
        if thread is not main_thread:
            thread.join()

    end = time.time()

    print("Time taken: " + str(end - start))
