import datetime
import pandas_datareader.data as web


def get_data(symbol: str, start:datetime.datetime, end: datetime.datetime):
    # TODO: Investigate what Yahoo's API does for symbols it doesn't recognize
    return web.DataReader(symbol, 'yahoo', start, end)