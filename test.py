import requests
import json
import pandas as pd
import matplotlib.pyplot as plt


def main():
    key = "OSO2MXY1UHSU2NLX"
    prefix = "https://www.alphavantage.co/query"
    response = requests.get(prefix, params={"apikey": key, "function":"TIME_SERIES_INTRADAY", "symbol":"AAPL", "interval":"1min", "outputsize":"full"});
    out = open("aapl.json", "w")
    out.write(response.text)
    out.close()

    f = open("aapl.json")
    graph_closing_prices(f)
    # TODO: add string parameter that specifies the interval


def graph_closing_prices(f):
    """
    Given a JSON file of a stock's data, graph the closing prices at
    minute-by-minute intervals

    :param f: JSON file with specific format
    :return: void
    """

    stock_data = json.load(f)
    date = []
    value = []
    for key in stock_data["Time Series (1min)"]:
        date.append(key[5:-3])
        value.append(float(stock_data["Time Series (1min)"][key]["4. close"]))
    date.reverse()

    df = pd.DataFrame(list(zip(date, value)), columns=["time", "closing_price"])
    df.plot(x="time", y="closing_price")
    plt.gcf().autofmt_xdate()
    plt.title("Graph of Closing Prices for " + stock_data["Meta Data"]["2. Symbol"])
    plt.show()


if __name__ == "__main__":
    main()
