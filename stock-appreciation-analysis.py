import requests
import json
import pandas as pd
import matplotlib.pyplot as plt
from typing import TextIO, List
import datetime as dt
from matplotlib import style
import pandas_datareader.data as web
from datetime import datetime, timedelta
import optparse

"""
Defining parsed objects to take in as commandline arguments
"""

parser = optparse.OptionParser()

parser.add_option('-q', '--query',
        action="store", dest="query",
        help="query file", default="spam")

parser.add_option('-s', '--start',
        action="store", dest="start",
        help="start date", default="spam")

parser.add_option('-e', '--end',
        action="store", dest="end",
        help="end date", default="spam")

parser.add_option('-x', '--top_x',
        action="store", dest="x",
        help="top x to track", default="spam")

options, args = parser.parse_args()

def extract_symbols(f: TextIO) -> List[str]:
    """
    Given a csv file with delimeter "|", extract all the stock symbols

    :param: file with all the information
    :return: A list of all the stock symbols
    """

    df = pd.read_csv(f, delimiter="|")
    return df["NASDAQ Symbol"].tolist()

def get_data(start, end, symbol):
    df = web.DataReader(symbol, 'yahoo', start, end)
    return df


def get_max_and_min_increase(query_file: TextIO, start, end, x):
    """
    Return the top <x> stocks in <query_file> that increased the most from <start> to <end>
    """

    stock_symbols = extract_symbols(f)

    result_pos = {}
    result_neg = {}

    for i in range(len(stock_symbols)):
        symbol = stock_symbols[i]
        if isinstance(symbol, str):
            if not symbol.isalpha():
                print("skipped stock: symbol not all alpha")
                continue
        else:
            print("skipped stock: symbol not even string")
            continue

        try:
            df = get_data(start, end, symbol)
        except:
            print("skipped stock: could not find data :(")
            continue

        if len(df['Close'].tolist()) < 2:
            print("skipped stock: Not enough data :(")
            continue
        yes, td = df['Close'].tolist()[0],  df['Close'].tolist()[-1]

        inc = (td - yes) / yes

        if len(result_neg) < x:
            result_neg[symbol] = inc
            result_pos[symbol] = inc
        else:
            max = list(result_neg.keys())[0]
            min = list(result_pos.keys())[0]
            for key in result_pos:
                if result_pos[key] < result_pos[min]:
                    min = key
            for key in result_neg:
                if result_neg[key] > result_neg[max]:
                    max = key
            if result_pos[min] < inc:
                result_pos.pop(min)
                result_pos[symbol] = inc
            if result_neg[max] > inc:
                result_neg.pop(max)
                result_neg[symbol] = inc
        print(result_pos, result_neg)
    return result_pos, result_neg


if __name__ == "__main__":

    # formatting parsed arguments
    start = datetime.strptime(options.start, '%Y %m %d')
    end = datetime.strptime(options.end, '%Y %m %d')
    f = options.query
    x = int(options.x)

    result_pos, result_neg = get_max_and_min_increase(f, start, end, x)

    pos_file = options.start + "-" + options.end + "-pos"
    neg_file = options.start + "-" + options.end + "-neg"
    #
    with open(pos_file, 'w') as fp:
        json.dump(result_pos, fp)

    with open(neg_file, 'w') as fp:
        json.dump(result_neg, fp)
