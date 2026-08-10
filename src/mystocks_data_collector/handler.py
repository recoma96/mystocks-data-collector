import asyncio
from dataclasses import asdict
from datetime import date, timedelta, datetime
import logging
from typing import Any, Dict, List, Tuple

from mystocks_data_collector.config import Config
from mystocks_data_collector.modules.client.tossinvest_api.client import TossInvestAPI
from mystocks_data_collector.modules.exc import APIResponseError
from mystocks_data_collector.modules.logics.collection import get_benchmark_stocks_current_prices, get_orders_full
from mystocks_data_collector.modules.logics.storage import write_snapshots_to_s3
from mystocks_data_collector.modules.logics.transform import create_portpolio_by_api_repsonse
from mystocks_data_collector.modules.logics.upload import DataUpdater
from mystocks_data_collector.modules.storage import S3Storage
from mystocks_data_collector.modules.types import ApiRepsonses, BenchmarkPosition, PortpolioSnapshot, Position, Transaction
from mystocks_data_collector.modules.utils import is_us_trading_session, now_korea


logger = logging.getLogger(__name__)

def handler(event, context):
    _set_before_handler()
    asyncio.run(main())


def _set_before_handler():
    _set_logger()


def _set_logger():
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


async def main():
    now = now_korea()

    if not is_us_trading_session(now):
        return create_response("휴장일 또는 주말이라 건너뜁니다", 200)

    s3_storage = S3Storage()

    error, api_responses = await collect_data_from_tossinvest()
    if error:
        return create_response(error, 500)

    # await write_snapshots_to_s3(s3_storage, api_responses)

    benchmarks, positions, transactions, portpolio = create_portpolio_by_api_repsonse(*api_responses)

    update_datas(
        now,
        s3_storage=s3_storage,
        portpolio=portpolio,
        benchmarks=benchmarks,
        positions=positions,
        transactions=transactions,
    )

    return create_response("Success", 200)


async def collect_data_from_tossinvest() -> Tuple[str | None, ApiRepsonses | None]:
    today = now_korea()
    yesterday = today - timedelta(days=1)
    try:
        async with TossInvestAPI() as api:
            res = await api.get_oauth2_access_token()
            access_token = res.access_token
            api.update_headers({"Authorization": f"Bearer {access_token}"})

            return None, await asyncio.gather(
                get_benchmark_stocks_current_prices(api, list(Config.PEER_STOCKS.keys())),
                api.get_buying_power(),
                api.get_stocks(),
                get_orders_full(api, from_date=yesterday.date(), to_date=yesterday.date())
            )

    except APIResponseError as e:
        logger.exception("토스 API 요청 오류 응답: {status=%s}", e.status_code)
        return (e.response_body, None)

def update_datas(
        today: datetime,
        s3_storage: S3Storage,
        portpolio: PortpolioSnapshot,
        benchmarks: List[BenchmarkPosition],
        positions: List[Position],
        transactions: List[Transaction],
):
    uploader = DataUpdater(s3_storage)
    today_date = today.date()

    uploader.update_topic("portpolio", [asdict(portpolio)], today_date)
    uploader.update_topic("benchmarks",[asdict(data) for data in benchmarks], today_date)
    uploader.update_topic("positions", [asdict(data) for data in positions], today_date)

    # TODO 트랜잭션의 경우 1일 단위로 조회 
    #   -> 배치로 1일 이내 단위로 조회할 경우 동일 내역 겹칠 수 있어 별도 함수 생성
    

def create_response(error: str, code: int = 500) -> Dict[str, Any]:
    return {
        "statusCode": code,
        "body": error,
    }
