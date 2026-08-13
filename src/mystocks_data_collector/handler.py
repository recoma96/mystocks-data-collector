import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from mystocks_data_collector.modules.duckdb_client import connect_s3_duckdb
from mystocks_data_collector.modules.logics.pipeline import (
    collect_data_from_tossinvest,
    collect_orders_from_tossinvest,
    transactions_already_uploaded,
    update_datas,
    upload_histories_view,
    upload_position_view,
    upload_transactions,
    upload_transactions_view
)
from mystocks_data_collector.modules.logics.storage import write_orders_snapshots_to_s3, write_snapshots_to_s3
from mystocks_data_collector.modules.logics.transform import create_portfolio_by_api_response, create_transactions_by_api_responses
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
    await update_transactions(now)
    error_response = await update_status(now)
    if error_response:
        return error_response
    # 당일 오전 5시 이후에만 확인한다 -> 미국장은 5시에 종료하기 때문이다.
    if now.hour >= 5:
        generate_view(now)

    return create_response("Success", 200)

async def update_status(now: datetime) -> Dict[str, Any] | None:
    """현재 포트폴리오 및 비교군 실시간 상태 데이터 업데이트
    """
    if not is_us_trading_session(now):
        return create_response("휴장일 또는 주말이라 건너뜁니다", 200)

    s3_storage = S3Storage()

    error, api_responses = await collect_data_from_tossinvest()
    if error or api_responses is None:
        if error is None:
            error = "알 수 없는 에러"
        return create_response(error, 500)

    await write_snapshots_to_s3(s3_storage, api_responses)

    benchmarks, positions, portfolio = create_portfolio_by_api_response(*api_responses)

    update_datas(
        now,
        s3_storage=s3_storage,
        portfolio=portfolio,
        benchmarks=benchmarks,
        positions=positions,
    )

    return None


async def update_transactions(now: datetime) -> Dict[str, Any] | None:
    """어제자 매수/매도 주문건 업데이트
    """
    yesterday = now - timedelta(days=1)
    s3_storage = S3Storage()

    if transactions_already_uploaded(s3_storage, yesterday.date()):
        return None

    error, orders = await collect_orders_from_tossinvest(yesterday, yesterday)
    if error or orders is None:
        if error is None:
            error = "알 수 없는 에러"
        return create_response(error, 500)

    await write_orders_snapshots_to_s3(s3_storage, orders)

    transactions = create_transactions_by_api_responses(orders)

    upload_transactions(now, s3_storage, transactions)

    return None


def generate_view(now: datetime):
    """웹페이지에서 분석 사이트를 보여주기 위한 json가반의 view 파일 생성하기
    """
    s3_storage = S3Storage()
    with connect_s3_duckdb() as conn:
        data = upload_position_view(s3_storage, conn, now)
        if not data:
            return

        portfolio_data, portfolio_id = data
        upload_histories_view(s3_storage, conn, portfolio_data, portfolio_id, now)
        upload_transactions_view(s3_storage, conn, now)


def create_response(error: str, code: int = 500) -> Dict[str, Any]:
    return {
        "statusCode": code,
        "body": error,
    }
