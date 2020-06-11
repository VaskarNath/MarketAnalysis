import datetime
import math
import sys
import threading
import time
from typing import Optional, List, Callable

import numpy as np
import pandas as pd
from pandas import DataFrame

sys.path.append("../")
from data_requests import get_data
from tools.messaging import Listener, Message
from tools.synced_list import SyncedList

"""
The number of threads that this script will use to accomplish its task.
"""
NUM_THREADS = 3

"""
The number of days used in calculating the short- and long-term moving averages, respecively, in check_for_cross 
"""
SHORT_MOVING_AVERAGE = 20
LONG_MOVING_AVERAGE = 50

"""
Constants used to tweak MACD and MACD Signal values 
"""
MACD_SHORT_AVERAGE = 12
MACD_LONG_AVERAGE = 26
MACD_SIGNAL_PERIOD = 9

"""
Define the types of analyses that analyze_symbols can run
"""
GOLDEN_CROSS = 0
MACD_SIGNAL_CROSS = 1


def moving_average(symbol, start, end, n, local=False, dir="") -> Optional[pd.DataFrame]:
    """
    Return a DataFrame containing an <n>-day moving average for each trading day between <start> and <end>, inclusive.
    Note: the range given by start and end doesn't have to include enough data points for a full <n>-day moving average.
    The method will try to fetch enough data to calculate the average for each trading data in the given range, and then
    truncate the returned result.

    RAISES NotEnoughDataError if there isn't enough historical data available to calculate a full <n>-day moving average
    for at least the first trading day in the range <start>-<end>

    If <local>=True, assumes that <dir> is a string containing a path to a directory containing stock data.
    Files in this directory should be .csv's and have filename equal to the stock symbol whose data they are holding.
    This method assumes that the file <symbol>.csv exists in <dir>, if <local>=True. Will return None if this is not the
    case.

    The returned DataFrame has index "Date" and one column of data, "Average".

    Returns None in the event of an error fetching data.
    """
    try:
        # We get data from the given range to ensure that we are returned at least enough data points to calculate an
        # <n>-day moving average for the day <start>. We use n + 3*n/7 below because weekends and holidays take up
        # somewhat less than 3/7ths of all days. Note that if there is not enough data to give us this full window,
        # get_data simply returns whatever it can
        df = get_data(symbol, start - datetime.timedelta(n + math.ceil((3 * n) / 7)), end, local=local, dir=dir)
        if df is None:
            return None

        # Count how many data points we have up to but not including <start> (or whatever the first trading day after
        # <start> is if <start> happens to be a weekend or holiday)
        num_preceding = 0
        while num_preceding < len(df.index) and df.index[num_preceding] < start:
            num_preceding += 1

        # Raise an error if there are fewer than <n> data points, because then we won't have enough data points to
        # calculate an n-day moving average on the first day of our range
        if num_preceding < n:
            raise NotEnoughDataError(
                f"Not enough data to calculate {n}-day moving average for {symbol} with range {start}-{end}")

        average = DataFrame()
        # Since we know we have enough data points, we can set window=n without worrying about the rows that will get
        # value NaN. This is because we know none of them are in the range we were given, and when we return below we
        # slice the DataFrame to only include this range.
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

    RAISES NotEnoughDataError if there isn't enough data available for the given symbol to calculate an <n>-day EMA
    value for the first day in the given range
    """
    # We get data from the given range to ensure that we are returned at least enough data points to calculate an
    # <n>-day EMA for the day <start>. We use (n+1) + 3*(n+1)/7 below because weekends and holidays take up
    # somewhat less than 3/7ths of all days
    df = get_data(symbol, start - datetime.timedelta((n + 1) + math.ceil((3 * (n + 1)) / 7)), end, local=local, dir=dir)

    if df is None:
        return None

    # Count the number of data points BEFORE <start> that we were able to fetch. To be able to calculate a bona fide
    # EMA for each trading day between <start> and <end>, we need at least n of these, because we need to start with an
    # n-day simple moving average before we can start calculating EMA.
    num_preceding = 0
    while num_preceding < len(df.index) and df.index[num_preceding] < start:
        num_preceding += 1

    if num_preceding < n:
        raise NotEnoughDataError(f"Not enough data to calculate {n}-day EMA for {symbol}")

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

    RAISES NotEnoughDataError if there are fewer than n+1 data points in df, as this is the bare minimum amount of data
    needed to calculate a single actual EMA value.
    """
    # We need to first have enough data points to calculate an <n>-day simple average before we can calculate our first
    # EMA value, so we need at least n+1 data points total.
    if len(df.index) < n + 1:
        raise NotEnoughDataError(f"Not enough data to calculate {n}-day EMA")
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
    """
    Computes MACD and Signal for the given symbol over the given range. The returned DataFrame has index "Date" and
    two columns: "MACD" and "Signal".

    If <local>=True, assumes that <dir> is a string containing a path to a directory containing stock data.
    Files in this directory should be .csv's and have filename equal to the stock symbol whose data they are holding.
    This method assumes that the file <symbol>.csv exists in <dir>, if <local>=True.

    RAISES NotEnoughDataError if there aren't enough historical data points to calculate MACD and Signal for every
    trading day between <start> and <end>.

    Returns None in the event of an error fetching data.
    """
    # We need to fetch enough data so that we can compute MACD for the range <start>-<end>. That means, including
    # weekends and holidays, we need at least MACD_LONG_AVERAGE + 3 * MACD_LONG_AVERAGE / 7 data points to be able
    # to calculate MACD for the first day of our range. But, we also need to fetch enough data points to then take an
    # EMA of the MACD, for the signal line, which is an MACD_SIGNAL_PERIOD-day EMA. So that's why we have the gross
    # timedelta here.
    price_data = get_data(symbol, start - datetime.timedelta(
        MACD_LONG_AVERAGE + 3 * MACD_LONG_AVERAGE / 7 + (MACD_SIGNAL_PERIOD + 1) + 3 * (MACD_SIGNAL_PERIOD) / 7), end,
                          local=local, dir=dir)

    if price_data is None:
        return None

    # Count how many data points we have before the first trading day in our range. We need to know if we have enough
    # to calculate what we need to calculate
    num_preceding = 0
    while num_preceding < len(price_data.index) and price_data.index[num_preceding] < start:
        num_preceding += 1

    if num_preceding < MACD_LONG_AVERAGE + MACD_SIGNAL_PERIOD:
        raise NotEnoughDataError(
            f"Not enough data points to calculate MACD and Signal for symbol {symbol} and range {start}-{end}")

    df = DataFrame()
    df["Price"] = price_data["Adj Close"]
    EMA(df, "Price", "Short", MACD_SHORT_AVERAGE)
    EMA(df, "Price", "Long", MACD_LONG_AVERAGE)
    df["MACD"] = df["Short"] - df["Long"]

    # So now we've got a DataFrame with columns "Price", "Short", "Long", and "MACD". Because "Short" and "Long" are
    # moving averages, calcualted using our EMA function, they each have some number of NaN values at the beginning.
    # And because "MACD" = "Short" - "Long", so does "MACD". That means that when we calculate an EMA of "MACD" below,
    # it'll get messed up unless we remove the NaN values. So we do that first.

    # Iterate until i points to the first row that contains an actual value for MACD
    i = 0
    while np.isnan(df["MACD"][df.index[i]]):
        i += 1

    # Chop off all the NaN values
    df = df[df.index[i]:]

    # Add the column "Signal" to the DataFrame as a MACD_SIGNAL_PERIOD EMA of the "MACD" column
    EMA(df, "MACD", "Signal", MACD_SIGNAL_PERIOD)

    df.drop(labels=["Short", "Long"], axis=1, inplace=True)
    return df[start:end]


class NotEnoughDataError(Exception):
    """
    This class exists to be raised by methods that make a calculation based on historical data, in the event that they
    are asked to compute values for a period for which there aren't enough data points. For example, a 10-day moving
    average starting on a Friday for which data only goes back as far as Monday.
    """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


def MACD_signal(symbol: str, listener: Listener, start: datetime.datetime, end: datetime.datetime, local=False,
                dir="") -> \
        List[datetime.datetime]:
    """
    Look for the MACD of the given stock to cross above its signal line WHILE price is also above the 200-day EMA.
    Return a list of all days that are the endpoints of such crosses. That is, the list of all days between <start> and
    <end> where MACD was above its signal line having been below it the day before.

    If <local>=True, assumes that <dir> is a string containing a path to a directory containing stock data.
    Files in this directory should be .csv's and have filename equal to the stock symbol whose data they are holding.
    This method assumes that the file <symbol>.csv exists in <dir>, if <local>=True.

    Prints a message to the console using <listener> and returns an empty list if not enough data could be found to
    compute the necessary values.
    """
    try:
        macd = MACD(symbol, start, end, local=local, dir=dir)
    except NotEnoughDataError as e:
        msg = Message()
        msg.add_line(str(e))
        listener.send(msg)

        return []

    # Get a 200-day EMA of price
    data = get_data(symbol, start, end, local=local, dir=dir)
    if data is None:
        return []

    EMA(data, "Adj Close", "EMA", 200)

    signals = []
    for i in range(1, len(macd.index)):
        day_before = macd.index[i - 1]
        day = macd.index[i]
        if macd["MACD"][day] > macd["Signal"][day] and macd["MACD"][day_before] <= macd["Signal"][day_before] and \
                data["Adj Close"][day] > data["EMA"][day]:
            signals.append(day)

    return signals


def golden_cross(symbol: str, listener: Listener, short: int, long: int, start: datetime.datetime,
                 end: datetime.datetime, local=False, dir="") -> List[datetime.datetime]:
    """
    Check for crosses by the <short>-day moving average above the <long>-day moving average some time between <start>
    and <end>. The returned list contains all days on which the short-term average closed ABOVE the long-term average,
    having been below the long-term average on the previous day.

    If <local>=True, assumes that <dir> is a string containing a path to a directory containing stock data.
    Files in this directory should be .csv's and have filename equal to the stock symbol whose data they are holding.
    This method assumes that the file <symbol>.csv exists in <dir>, if <local>=True.
    """
    msg = Message()

    try:
        short_average = moving_average(symbol, start, end, short, local=local, dir=dir)
        long_average = moving_average(symbol, start, end, long, local=local, dir=dir)
    except NotEnoughDataError as e:
        msg.add_line(str(e))
        listener.send(msg)

        return []

    if short_average is not None and long_average is not None:

        days = short_average.index

        crosses = []
        for i in range(len(days) - 1):
            if (short_average["Average"][days[i]] <= long_average["Average"][days[i]]
                    and short_average["Average"][days[i + 1]] > long_average["Average"][days[i + 1]]):
                crosses.append(days[i + 1])

        return crosses
    else:
        msg.add_line("******************************************************")
        msg.add_line(f"Couldn't get data for {symbol}")
        msg.add_line("******************************************************")
        listener.send(msg)

        return []


def check_for_crosses(lst: SyncedList, listener: Listener, start: datetime.datetime, end: datetime.datetime):
    """
    Check for crosses of the <short>-day moving average above the <long>-day moving average in the last five days of
    trading. <lst> should be a SyncedList of stock symbols, and <listener> is what the threads spawned to accomplish the
    task will use to communicate with the console. 
    """
    msg = Message()
    symbol = lst.pop()
    while symbol is not None:
        msg.add_line("Analyzing symbol...")
        listener.send(msg)
        msg.reset()

        crosses = golden_cross(symbol, listener, SHORT_MOVING_AVERAGE, LONG_MOVING_AVERAGE, start, end)
        for cross in crosses:
            msg.add_line("=========================================")
            msg.add_line(f"Cross above for {symbol} on {cross}")
            listener.send(msg)
            msg.reset()

        symbol = lst.pop()


def check_for_MACD_signal_crosses(lst: SyncedList, listener: Listener, start: datetime.datetime,
                                  end: datetime.datetime):
    """
    Check each stock symbol in the given SyncedList for crosses of the MACD above its signal line while price is above
    its 200-day EMA during the period from <start> to <end>. Print a message to the console for each such cross found.
    """
    symbol = lst.pop()
    msg = Message()

    while symbol is not None:
        msg.add_line(f"Analyzing {symbol}...")
        listener.send(msg)
        msg.reset()
        signals = MACD_signal(symbol, start, end, local=True, dir="../data")

        for signal in signals:
            msg.add_line("======================================")
            msg.add_line(f"Signal on {signal} for {symbol}")
            msg.add_line("======================================")
            listener.send(msg)
            msg.reset()

        symbol = lst.pop()


def analyze_symbols(lst: SyncedList, start: datetime.datetime, end: datetime.datetime,
                    func: Callable[[SyncedList, Listener, datetime.datetime, datetime.datetime], None]) -> \
        List[threading.Thread]:
    """
    Spawns NUM_THREADS threads to analyze the given list of symbols. <func> is the method that each thread will run.
    It's signature should match the above. It should take a SyncedList of symbols to analyze, a Listener object with
    which to communicate with the console, and two dates: a start date for analysis and an end date for analysis. It
    should return nothing.
    """
    listener = Listener()

    threads = []
    # Start NUM_THREADS different threads, each drawing from the same central list of symbols, to look for golden
    # crosses
    for i in range(NUM_THREADS):
        x = threading.Thread(target=func, args=(lst, Listener, start, end))
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
    threads = analyze_symbols(lst, datetime.datetime.today() - datetime.timedelta(7), datetime.datetime.today(),
                              check_for_crosses)
    main_thread = threading.current_thread()
    for thread in threads:
        if thread is not main_thread:
            thread.join()

    end = time.time()

    print("Time taken: " + str(end - start))
