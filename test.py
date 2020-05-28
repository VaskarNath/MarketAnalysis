import requests
import json
import pandas as pd
import matplotlib.pyplot as plt
from typing import TextIO, List
import datetime as dt
from matplotlib import style
import pandas_datareader.data as web


def main():
    key = "OSO2MXY1UHSU2NLX"
    prefix = "https://www.alphavantage.co/query"
    response = requests.get(prefix, params={"apikey": key, "function":"TIME_SERIES_INTRADAY", "symbol":"AAPL", "interval":"60min", "outputsize":"full"});
    out = open("aapl.json", "w")
    out.write(response.text)
    out.close()

    f = open("aapl.json")
    graph_closing_prices(f, "60min")
    # TODO: add string parameter that specifies the interval

    # f = open("nasdaqtraded.txt")
    # print(extract_symbols(f))


def graph_closing_prices(f, interval: str) -> None:
    """
    Given a JSON file of a stock's data, graph the closing prices at
    minute-by-minute intervals

    :param f: JSON file with specific format
    :param interval: the interval time at which data points are gathered
    :return: void
    """

    stock_data = json.load(f)
    date = []
    value = []
    for key in stock_data["Time Series " + "(" + interval + ")"]:
        date.append(key[5:-3])
        value.append(float(stock_data["Time Series " + "(" + interval + ")"][key]["4. close"]))
    date.reverse()

    df = pd.DataFrame(list(zip(date, value)), columns=["time", "closing_price"])
    df.plot(x="time", y="closing_price")
    plt.gcf().autofmt_xdate()
    plt.title("Graph of Closing Prices for " + stock_data["Meta Data"]["2. Symbol"])
    plt.show()


def extract_symbols(f: TextIO) -> List[List[str]]:
    """
    Given a csv file with delimeter "|", extract all the stock symbols

    :param: file with all the information
    :return: A list of all the stock symbols
    """

    df = pd.read_csv(f, delimiter="|")
    return [df["Symbol"].tolist(), df["NASDAQ Symbol"].tolist()]

def get_data(start, end, symbol):
    style.use('ggplot')
    df = web.DataReader(symbol, 'yahoo', start, end)
    print(df.head(6))

if __name__ == "__main__":
    start = dt.datetime(2020, 5, 20)
    end = dt.datetime(2020, 5, 28)
    get_data(start, end, "GNUS")
    main()
