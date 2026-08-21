import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List

from mystocks_data_collector.config import Config
from mystocks_data_collector.modules.client.tossinvest_api.orders_responses import TossInvestOrder
from mystocks_data_collector.modules.storage import S3Storage
from mystocks_data_collector.modules.types import ApiResponses


async def write_snapshots_to_s3(
        s3_storage: S3Storage,
        api_responses: ApiResponses
) -> None:
    res_benchmark_prices, res_buying_power, res_stocks = api_responses

    await asyncio.gather(
        asyncio.to_thread(
            s3_storage.write_snapshot,
            "benchmark_prices",
            {ticker: item.model_dump() for ticker, item in res_benchmark_prices.items()},
        ),
        asyncio.to_thread(
            s3_storage.write_snapshot, "buying_power", res_buying_power.model_dump()
        ),
        asyncio.to_thread(
            s3_storage.write_snapshot, "stocks", res_stocks.model_dump()
        ),
    )


async def write_orders_snapshots_to_s3(s3_storage: S3Storage, orders: List[TossInvestOrder]) -> None:
    return await asyncio.to_thread(
        s3_storage.write_snapshot,
        "orders",
        [item.model_dump() for item in orders]
    )


def fetch_latest_view_before(s3_storage: S3Storage, key_format: str, now: datetime) -> Dict | None:
    """key_format(날짜별 view 키, "view/histories/{}.json" 형태)을 기준으로 now 이전 날짜 중
    가장 최근에 존재하는 view를 최대 MAX_VIEW_LOOKBACK_DAYS일 전까지 거슬러 올라가며 찾는다.
    주말/휴장일이 겹쳐 어제자 파일이 없는 경우를 대비한 것.
    """
    # TODO: 15일을 초과하는 갭에는 대응 못 함 - 더 나은 방안 추후 고안 필요
    for days_ago in range(1, Config.MAX_VIEW_LOOKBACK_DAYS + 1):
        target_date = now - timedelta(days=days_ago)
        key = key_format.format(target_date.strftime("%Y-%m-%d"))
        if not s3_storage.exists(key):
            continue

        body = s3_storage.get_object(key)
        if body is not None:
            return json.loads(body)

    return None
