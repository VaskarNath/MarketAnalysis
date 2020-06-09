import datetime as dt
from typing import List
import time
import sys
sys.path.append("../")
from data_requests import get_data
from tools.synced_list import SyncedList
from tools.messaging import Message, Listener
import threading
import os
import sys


def save(symbol: str, start: dt.datetime, end: dt.datetime, listener: Listener) -> None:
    """
    Saves all price data associated with the given symbol as a .csv file in the data directory.
    The .csv file shares the same name as the symbol, and if a file already exists with that name it will be overwritten
    """
    df = get_data(symbol, start, end)

    if df is None:
        msg = Message()
        msg.add_line("*****************************")
        msg.add_line(f"KeyError fetching data for {symbol}")
        msg.add_line("*****************************")
        listener.send(msg)
        return

    f = open("../data/" + symbol + ".csv", "w")
    df.to_csv(f)


def save_symbols(symbols: SyncedList, start: dt.datetime, end: dt.datetime, listener: Listener):
    msg = Message()

    symbol = symbols.pop()
    while symbol is not None:
        msg.reset()
        msg.add_line("Saving " + symbol + "...")
        listener.send(msg)
        save(symbol, start, end, listener)
        symbol = symbols.pop()


if __name__ == '__main__':
    """
    A quick script I wrote to pull data from the internet and save it, one .csv file per symbol, in a folder.
    Currently fetches data from January 1st, 2010 to today.
    
    Usage: py pull_data.py <dest_folder> <symbols_list>
    
    <dest_folder> is the path to the folder that should contain the produced .csv files. If this folder doesn't
    exist, it will be created.
    
    <symbols_list> should be a file containing a list of stock symbols, with one per line
    """
    start = time.time()
    if len(sys.argv) != 3:
        print("Usage: py pull_data.py <dest_folder> <symbols_list>")
        sys.exit(1)

    try:
        os.mkdir(sys.argv[1])
        print(f"Created folder \"{sys.argv[1]}\"")
    except FileExistsError:
        print(f"Folder \"{sys.argv[1]}\" already exists. Continuing...")

    try:
        source = open(sys.argv[2])
    except OSError:
        print(f"Couldn't open source file {sys.argv[2]}")
        sys.exit(1)

    symbols = []
    for symbol in source:
        symbol = symbol.strip()
        if symbol.isalpha():
            symbols.append(symbol)

    synced = SyncedList(symbols)

    threads = []
    for i in range(2):
        x = threading.Thread(target=save_symbols, args=(synced, dt.datetime(2010, 1, 1), dt.datetime.today(), Listener()))
        x.start()
        threads.append(x)

    for thread in threads:
        thread.join()

    end = time.time()
    print("Time taken: " + str(end-start))