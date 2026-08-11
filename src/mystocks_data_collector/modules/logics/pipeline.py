import asyncio
import logging
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from mystocks_data_collector.config import Config
from mystocks_data_collector.modules.client.tossinvest_api.client import TossInvestAPI
from mystocks_data_collector.modules.client.tossinvest_api.orders_responses import TossInvestOrder
from mystocks_data_collector.modules.exc import APIResponseError
from mystocks_data_collector.modules.logics.collection import get_benchmark_stocks_current_prices, get_orders_full
from mystocks_data_collector.modules.logics.upload import DataUpdater
from mystocks_data_collector.modules.storage import S3Storage
from mystocks_data_collector.modules.types import ApiRepsonses, BenchmarkPosition, PortpolioSnapshot, Position, Transaction
from mystocks_data_collector.modules.utils import now_korea


logger = logging.getLogger(__name__)


async def collect_data_from_tossinvest() -> Tuple[str | None, ApiRepsonses | None]:
    try:
        async with TossInvestAPI() as api:
            await _get_tossinvest_access_token(api)
            return None, await asyncio.gather(
                get_benchmark_stocks_current_prices(api, list(Config.PEER_STOCKS.keys())),
                api.get_buying_power(),
                api.get_stocks(),
            )

    except APIResponseError as e:
        logger.exception("토스 API 요청 오류 응답: {status=%s}", e.status_code)
        return (e.response_body, None)


async def collect_orders_from_tossinvest(today: datetime) -> List[TossInvestOrder]:
    yesterday = today - timedelta(days=1)
    try:
        async with TossInvestAPI() as api:
            await _get_tossinvest_access_token(api)
            return await get_orders_full(api, from_date=yesterday.date(), to_date=yesterday.date()) # TODO 인자는 바뀔 수 있음
    except APIResponseError as e:
        logger.exception("토스 API 요청 오류 응답: {status=%s}", e.status_code)
        return (e.response_body, None)


def update_datas(
        today: datetime,
        s3_storage: S3Storage,
        portpolio: PortpolioSnapshot,
        benchmarks: List[BenchmarkPosition],
        positions: List[Position],
):
    uploader = DataUpdater(s3_storage)
    today_date = today.date()

    uploader.update_topic("portpolio", [asdict(portpolio)], today_date)
    uploader.update_topic("benchmarks",[asdict(data) for data in benchmarks], today_date)
    uploader.update_topic("positions", [asdict(data) for data in positions], today_date)


def create_response(error: str, code: int = 500) -> Dict[str, Any]:
    return {
        "statusCode": code,
        "body": error,
    }


async def _get_tossinvest_access_token(api: TossInvestAPI):
    res = await api.get_oauth2_access_token()
    access_token = res.access_token
    api.update_headers({"Authorization": f"Bearer {access_token}"})
