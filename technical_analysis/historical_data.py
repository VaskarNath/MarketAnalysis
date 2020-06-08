import threading
import sys

sys.path.append("../")
from technical_analysis.rsi import rsi
from tools.synced_list import SyncedList
from tools.messaging import Listener
from tools.messaging import Message
from technical_analysis.moving_averages import cross_above
from typing import List
import datetime as dt


class IndicatorResultTracker:
    """
    A class to be used to store data investigating the relationship between some kind of statistical event, and the
    price of a security some number of days down the line.

    For example, I was interested in how good of an indicator an RSI reading of < 20 was as a sign of price increase.
    So, I thought, why not analyze a whole bunch of historical data, looking for periods of consecutive days on which
    the RSI of a company was below 20, then closed above 20. After such an event is found, compare the price in the
    days following the close above 20 to the price on the day of the close above 20. See how likely it is that the price
    increased after 1 day, or 2 days, or 3 days, etc. Then see what the average change was, relative to the price on
    the close above 20 day, 1 day after the close, 2 days, etc. So I created this object to help me do that by looking
    at a bunch of different stocks.
    """
    def __init__(self, days: int):
        """
        Initialize this tracker to be able to record data for up to <days> days after an occurrence
        """
        self._num_increases = [0] * days
        self._occurrences = 0
        self._changes = [0] * days
        self._num_changes = [0] * days
        self._lock = threading.Lock()

    def record_occurrence(self):
        """
        Record an occurrence of the statistical event
        """
        with self._lock:
            self._occurrences += 1

    def record_change(self, change: float, day: int):
        """
        Record that, <day> days after an event, the price of a security had changed by <change>. <change> should be the
        percentage change as a decimal.

        For example, if a golden cross occurred on Monday and the closing price on that day as $10, and on Friday the
        closing price was $15, that would be recorded as a change of 0.5 (50%), 4 days after the event.
        """
        with self._lock:
            self._changes[day - 1] += change
            self._num_changes[day - 1] += 1
            if change > 0:
                self._num_increases[day - 1] += 1

    def summarize(self):
        """
        Summarize the data stored in this object. Prints the total number of occurrences that this object
        has been notified of. Also prints the probability of an increase in price after n days, for 1 <= n <= <days>,
        where <days> is the argument that was passed to the constructor of this object. Also prints the average CHANGE
        in price after n days for 1 <= n <= <days>.
        """
        print(f"Total Occurrences: {self._occurrences}")
        print("Probability of Increase after N Days:")
        for i in range(len(self._num_increases)):
            print(f"{i + 1} : {100 * (self._num_increases[i] / self._occurrences)}%")

        print("Average Change after N Days:")
        for i in range(len(self._changes)):
            print(f"{i + 1} : {100 * (self._changes[i] / self._occurrences)}%")

        print("Alternative:")
        for i in range(len(self._changes)):
            print(f"{i + 1} : {100 * (self._changes[i] / self._num_changes[i])}%")

        print("Number of Changes:")
        print(self._num_changes)


def analyze(symbol: str, tracker: IndicatorResultTracker, days: int, listener: Listener):
    """
    Analyzes the past 10 years of price data of the given stock symbol. Computes the standard 14-day period RSI for the
    interval ranging from January 1st, 2010 to December 31, 2019. Then, searches for periods where the stock was
    "oversold"; for our purposes, that means an RSI of 20 or less. Searches for periods containing some number of
    consecutive days on which the RSI remained below 20, followed immediately by a day on which the RSI was above 20.
    Examines the closing prices of the 10 days following this latter day, to see how frequently price increases follow
    a period of "oversold"-ness, and what the average price change is 1,2,3,... and 10 days after a period of
    "oversold"-ness.

    Uses the above class, IndicatorResultTracker, to keep track of the relevant data.
    """
    msg = Message()
    # msg.add_line(f"Analyzing {symbol}")
    # listener.send(msg)

    df_rsi = rsi(symbol, dt.datetime(2010, 1, 1), dt.datetime(2019, 12, 31), 14, local=True, dir="../data")

    last_was_oversold = False
    if df_rsi is not None:
        for i in range(len(df_rsi.index)):
            date = df_rsi.index[i]
            if df_rsi["RSI"][date] <= 20:
                if not last_was_oversold:
                    last_was_oversold = True

                msg.add_line("=====================================")
                msg.add_line(f"{symbol} was oversold on {date}")
                msg.add_line("=====================================")
            else:
                if last_was_oversold:
                    listener.send(msg)
                    msg.reset()
                    last_was_oversold = False

                    tracker.record_occurrence()

                    listener.send(msg)
                    msg.reset()
                    j = i+1
                    while j <= i + days and j < len(df_rsi.index):
                        change = (df_rsi["Adj Close"][df_rsi.index[j]] - df_rsi["Adj Close"][df_rsi.index[i]]) / df_rsi["Adj Close"][
                            df_rsi.index[i]]
                        msg.add_line(f"Recording change for {symbol} of {format(change, '.5f')} on day {j-i}")
                        tracker.record_change(change, j - i)
                        j += 1

                    listener.send(msg)
                    msg.reset()


def _analyze_thread(symbols: SyncedList, tracker: IndicatorResultTracker, days: int, listener: Listener):
    symbol = symbols.pop()
    while symbol is not None:
        msg = Message()
        msg.add_line(f"Thread {threading.currentThread()} analyzing {symbol}")
        listener.send(msg)
        analyze(symbol, tracker, days, listener)
        symbol = symbols.pop()


def analyze_symbols(symbols: SyncedList, days: int):
    threads = []
    tracker = IndicatorResultTracker(days)
    listener = Listener()

    for i in range(6):
        x = threading.Thread(target=_analyze_thread, args=(symbols, tracker, days, listener))
        x.start()
        threads.append(x)

    for thread in threads:
        thread.join()

    tracker.summarize()


if __name__ == '__main__':
    f = open("../s&p500_symbols.txt")

    symbols = []
    for line in f:
        line = line.strip()
        symbols.append(line)

    synced = SyncedList(symbols)

    analyze_symbols(synced, 10)
