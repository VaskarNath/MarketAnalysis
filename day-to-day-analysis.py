import requests
import json
import pandas as pd
import matplotlib.pyplot as plt
from typing import TextIO, List
import datetime as dt
from matplotlib import style
import pandas_datareader.data as web
from datetime import datetime, timedelta


def extract_symbols(f: TextIO) -> List[str]:
    """
    Given a csv file with delimeter "|", extract all the stock symbols

    :param: file with all the information
    :return: A list of all the stock symbols
    """

    df = pd.read_csv(f, delimiter="|")
    return df["Symbol"].tolist(), df["NASDAQ Symbol"].tolist()

def get_data(start, end, symbol):
    df = web.DataReader(symbol, 'yahoo', start, end)
    return df


def get_max_increase_from_yesterday():
    """
    Return the 10 stock that increased the most form past day to today
    """
    start = datetime.now() - timedelta(2)
    end = datetime.now()
    f = open("nasdaqtraded.txt")
    stock_symbols, nasdaq_stock_symbols = extract_symbols(f)

    result = {}

    for i in range(len(nasdaq_stock_symbols)):
        symbol = nasdaq_stock_symbols[i]
        if isinstance(symbol, str):
            if not symbol.isalpha():
                continue
        else:
            continue

        try:
            df = get_data(start, end, symbol)
        except:
            continue

        if len(df['Close'].tolist()) != 2:
            continue
        yes, td = df['Close'].tolist()[:]

        inc = (td - yes) / yes
        if len(result) < 100:
            result[symbol] = inc
        else:
            min = list(result.keys())[0]
            for key in result:
                if result[key] < result[min]:
                    min = key
            if result[min] > inc:
                result.pop(min)
                result[symbol] = inc
        print(result)
    return result

def get_min_increase_from_yesterday():
    """
    Return the 10 stock that decreased the most form past day to today
    """
    start = datetime.now() - timedelta(2)
    end = datetime.now()
    f = open("nasdaqtraded.txt")
    stock_symbols, nasdaq_stock_symbols = extract_symbols(f)

    result = {}

    for i in range(len(nasdaq_stock_symbols)):
        symbol = nasdaq_stock_symbols[i]
        if isinstance(symbol, str):
            if not symbol.isalpha():
                continue
        else:
            continue

        try:
            df = get_data(start, end, symbol)
        except:
            continue

        if len(df['Close'].tolist()) != 2:
            continue
        yes, td = df['Close'].tolist()[:]

        inc = (td - yes) / yes
        if len(result) < 100:
            result[symbol] = inc
        else:
            max = list(result.keys())[0]
            for key in result:
                if result[key] > result[max]:
                    max = key
            if result[max] > inc:
                result.pop(max)
                result[symbol] = inc
        print(result)
    return result

if __name__ == "__main__":
    result_max = get_max_increase_from_yesterday()
    result_min = get_min_increase_from_yesterday()

    date = now.strftime("%Y-%m-%d")
    pos_file = date + "-pos"
    neg_file = date + "-neg"

    with open(pos_file, 'w') as fp:
        json.dump(result_max, fp)

    with open(neg_file, 'w') as fp:
        json.dump(result_min, fp)
