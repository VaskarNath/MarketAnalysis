import datetime
import pandas_datareader.data as web
import pandas as pd


def get_data(symbol: str, start:datetime.datetime, end: datetime.datetime, local=False, dir=""):
    """
    Gets data for the given symbol according to the given range, either locally or from Yahoo's finance API.

    If <local>=True, assumes that <dir> is a string containing a path to a directory containing stock data.
    Files in this directory should be .csv's and have filename equal to the stock symbol whose data they are holding.
    This method assumes that the file <symbol>.csv exists in <dir>, if <local>=True.

    Returns none and prints a message if there is an error accessing data.
    """
    if local:
        try:
            df = pd.read_csv(f"{dir}/{symbol}.csv", parse_dates=True, index_col=0)
        except FileNotFoundError:
            print(f"No file to open for {symbol}")
            return None
    else:
        try:
            # The first RSI value in a series is calculated using a simple average of the first <period> data points.
            # Resultant RSI values use an exponential average. So we get enough data to allow for a buffer of
            # <period> data points (adding 3 * period / 7 to compensate for holidays and weekends) plus a further
            # buffer of 300 days, averaging out to about 214 days of trading, to ensure accuracy.
            df = get_data(symbol, start - datetime.timedelta(period + math.ceil(3 * period / 7) + 300), end)
        except KeyError:
            print("KeyError getting RSI data for " + symbol)
            return None

    return df