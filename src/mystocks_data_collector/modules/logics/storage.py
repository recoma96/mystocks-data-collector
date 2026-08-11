import asyncio
from typing import List

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
