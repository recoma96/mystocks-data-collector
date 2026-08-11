import asyncio
import logging
from datetime import datetime

from mystocks_data_collector.modules.logics.pipeline import (
    collect_data_from_tossinvest,
    create_response,
    update_datas
)
from mystocks_data_collector.modules.logics.storage import write_snapshots_to_s3
from mystocks_data_collector.modules.logics.transform import create_portpolio_by_api_repsonse
from mystocks_data_collector.modules.storage import S3Storage
from mystocks_data_collector.modules.utils import is_us_trading_session, now_korea


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

    await update_status(now)

    return create_response("Success", 200)


async def update_status(now: datetime):
    if not is_us_trading_session(now):
        return create_response("휴장일 또는 주말이라 건너뜁니다", 200)

    s3_storage = S3Storage()

    error, api_responses = await collect_data_from_tossinvest()
    if error:
        return create_response(error, 500)

    await write_snapshots_to_s3(s3_storage, api_responses)

    benchmarks, positions, portpolio = create_portpolio_by_api_repsonse(*api_responses)

    update_datas(
        now,
        s3_storage=s3_storage,
        portpolio=portpolio,
        benchmarks=benchmarks,
        positions=positions,
    )
