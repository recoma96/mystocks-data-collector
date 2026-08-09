import os
import logging

class Config:
    S3_BUCKET = os.getenv("S3_BUCKET")
    AWS_REGION_NAME = os.getenv("AWS_REGION_NAME", "ap-northeast-2")
    TOSSINVEST_CLIENT_ID = os.getenv("TOSSINVEST_CLIENT_ID")
    TOSSINVEST_CLIENT_SECRET = os.getenv("TOSSINVEST_CLIENT_SECRET")
    LOGGING_LEVEL = { "INFO": logging.INFO, "DEBUG": logging.DEBUG }.get(os.getenv("LOGGING_LEVEL", "INFO"))
    PEER_STOCKS = {ticker: name for ticker, name in zip(
        os.getenv("PEER_STOCKS_TICKER").split(","),
        os.getenv("PEER_STOCKS_NAME").split(",")
    )}
