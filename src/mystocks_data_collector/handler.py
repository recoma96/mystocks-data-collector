import asyncio
from datetime import timedelta
import logging
from typing import Any, Dict, Tuple

from mystocks_data_collector.config import Config
from mystocks_data_collector.modules.client.tossinvest_api.client import TossInvestAPI
from mystocks_data_collector.modules.exc import APIResponseError
from mystocks_data_collector.modules.logics.collection import get_benchmark_stocks_current_prices, get_orders_full
from mystocks_data_collector.modules.logics.transform import create_portpolio_by_api_repsonse
from mystocks_data_collector.modules.types import ApiRepsonses
from mystocks_data_collector.modules.utils import now_korea


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
    # TODO 주말 및 휴장일 제외 로직 필요

    error, api_responses = await collect_data_from_tossinvest()
    if error:
        return create_response(error, 500)

    benchmarks, positions, transactions, portpolio = create_portpolio_by_api_repsonse(*api_responses)

    return create_response("Success", 200)


async def collect_data_from_tossinvest() -> Tuple[str | None, ApiRepsonses | None]:
    today = now_korea()
    try:
        async with TossInvestAPI() as api:
            res = await api.get_oauth2_access_token()
            access_token = res.access_token
            api.update_headers({"Authorization": f"Bearer {access_token}"})

            return None, await asyncio.gather(
                get_benchmark_stocks_current_prices(api, list(Config.PEER_STOCKS.keys())),
                api.get_buying_power(),
                api.get_stocks(),
                get_orders_full(api, from_date=today.date(), to_date=today.date())
            )

    except APIResponseError as e:
        logger.exception("토스 API 요청 오류 응답: {status=%s}", e.status_code)
        return (e.response_body, None)


def create_response(error: str, code: int = 500) -> Dict[str, Any]:
    return {
        "statusCode": code,
        "body": error,
    }
