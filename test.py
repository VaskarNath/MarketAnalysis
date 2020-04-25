import requests

def main():
    key = "OSO2MXY1UHSU2NLX"
    prefix = "https://www.alphavantage.co/query"
    response = requests.get(prefix, params={"apikey": key, "function":"TIME_SERIES_INTRADAY", "symbol":"AAPL", "interval":"1min", "outputsize":"full"});
    out = open("aapl out", "w")
    out.write(response.text)
    

if __name__ == "__main__":
    main()
