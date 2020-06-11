import datetime

from typing import Optional

from pandas import DataFrame

import numpy as np

from tools.synced_list import SyncedList
from tools.messaging import Message, Listener
from data_requests import get_data


def rsi(symbol: str, start: datetime.datetime, end: datetime.datetime, period: int, local=False, dir="") -> Optional[DataFrame]:
    """
    Computes the RSI of period <period> for the given stock symbol for all trading days between <start> and <end>,
    inclusive. If <local>=True, assumes that <dir> is a string containing a path to a directory containing stock data.
    Files in this directory should be .csv's and have filename equal to the stock symbol whose data they are holding.
    This method assumes that the file <symbol>.csv exists in <dir>, if <local>=True.

    See tools.pull_data.py for an easy way of storing stock data locally like this
    """
    df = get_data(symbol, start, end, local=local, dir=dir)
    if df is None:
        return None

    df["Gain"] = np.nan
    df["Loss"] = np.nan
    # Fill in "Gain" and "Loss" columns
    for i in range(1, len(df.index)):
        diff = df["Adj Close"][df.index[i]] - df["Adj Close"][df.index[i - 1]]
        if diff >= 0:
            df.loc[df.index[i], "Gain"] = diff
            df.loc[df.index[i], "Loss"] = 0
        else:
            df.loc[df.index[i], "Gain"] = 0
            # When calculating RSI, we take losses as positive numbers
            df.loc[df.index[i], "Loss"] = -diff

    # Chop off the first row of the DataFrame, which has no Gain/Loss number
    df = df[df.index[1]:]

    # Create three empty columns: RSI, Average Gain, Average Loss
    df["RSI"] = np.nan
    df["Average Gain"] = np.nan
    df["Average Loss"] = np.nan

    sum_gain = 0
    sum_loss = 0
    for i in range(period):
        sum_gain += df["Gain"][df.index[i]]
        sum_loss += df["Loss"][df.index[i]]

    df.loc[df.index[period - 1], "Average Gain"] = sum_gain / 14
    df.loc[df.index[period - 1], "Average Loss"] = sum_loss / 14

    # The first RSI value is 100 - (100 / (1+ RS)), where RS = (Average Gain / Average Loss) over the first 14 days of
    # the window
    df.loc[df.index[period - 1], "RSI"] = 100 - 100 / (
            1 + (df["Average Gain"][df.index[period - 1]] / df["Average Loss"][df.index[period - 1]]))

    for i in range(period, len(df.index)):
        df.loc[df.index[i], "Average Gain"] = _exp_average(df["Average Gain"][df.index[i - 1]],
                                                       df["Gain"][df.index[i]], period)
        df.loc[df.index[i], "Average Loss"] = _exp_average(df["Average Loss"][df.index[i - 1]],
                                                       df["Loss"][df.index[i]], period)
        df.loc[df.index[i], "RSI"] = 100 - 100 / (1 + df["Average Gain"][df.index[i]] / df["Average Loss"][df.index[i]])

    return df.loc[start:end]


def _exp_average(previous: float, current: float, period: int) -> float:
    """
    Computes the exponential average used in the RSI calculation
    """
    return ((period - 1) * previous + current) / period


def check_overbought_oversold(symbols: SyncedList, start: datetime.datetime, end: datetime.datetime, period: int, listener: Listener):
    symbol = symbols.pop()
    while symbol is not None:
        msg = Message()
        msg.add_line("Checking " + symbol + "...")
        listener.send(msg)

        df = rsi(symbol, start, end, period)
        if df is not None:
            for date in df.index:
                if df["RSI"][date] >= 80:
                    msg = Message()
                    msg.add_line("=========================")
                    msg.add_line(symbol + " was overbought on " + str(date))
                    msg.add_line("=========================")
                    listener.send(msg)
                elif df["RSI"][date] <= 20:
                    msg = Message()
                    msg.add_line("=========================")
                    msg.add_line(symbol + " was oversold on " + str(date))
                    msg.add_line("=========================")
                    listener.send(msg)
        symbol = symbols.pop()


if __name__ == '__main__':
    symbols = []
    f = open("../s&p500_symbols.txt")
    for line in f:
        line = line.strip()
        symbols.append(line)

    lst = SyncedList(symbols)
    check_overbought_oversold(lst, datetime.datetime(2010, 1, 1), datetime.datetime(2019, 12, 31), 14, Listener())