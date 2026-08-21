import os
import logging


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"필수 환경변수 '{name}'가 설정되지 않았습니다. .env 파일을 확인하세요.")
    return value


class Config:
    AWS_REGION_NAME = os.getenv("AWS_REGION_NAME", "ap-northeast-2")
    TOSSINVEST_CLIENT_ID = os.getenv("TOSSINVEST_CLIENT_ID")
    TOSSINVEST_CLIENT_SECRET = os.getenv("TOSSINVEST_CLIENT_SECRET")
    LOGGING_LEVEL = { "INFO": logging.INFO, "DEBUG": logging.DEBUG }.get(os.getenv("LOGGING_LEVEL", "INFO"), logging.INFO)
    MAX_VIEW_LOOKBACK_DAYS = 15

    @classmethod
    def s3_bucket(cls) -> str:
        """S3 버킷명. 실제 사용 시점에만 검증됨"""
        return _require_env("S3_BUCKET")

    @classmethod
    def peer_stocks(cls) -> dict[str, str]:
        """비교군(벤치마크) 티커 -> 이름 매핑. 둘 중 하나라도 미설정이면 빈 dict, 개수가 안 맞으면 에러"""
        tickers_raw = os.getenv("PEER_STOCKS_TICKER")
        names_raw = os.getenv("PEER_STOCKS_NAME")

        if not tickers_raw or not names_raw:
            return {}

        tickers = tickers_raw.split(",")
        names = names_raw.split(",")

        if len(tickers) != len(names):
            raise RuntimeError(
                f"PEER_STOCKS_TICKER({len(tickers)}개)와 PEER_STOCKS_NAME({len(names)}개)의 개수가 다릅니다."
            )

        return dict(zip(tickers, names))
