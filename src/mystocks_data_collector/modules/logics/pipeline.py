import asyncio
import json
import logging
from dataclasses import asdict
from datetime import date, datetime
from typing import List, Tuple

import duckdb

from mystocks_data_collector.config import Config
from mystocks_data_collector.modules.client.tossinvest_api.client import TossInvestAPI
from mystocks_data_collector.modules.constants import ETF_DISPLAY_NAMES
from mystocks_data_collector.modules.duckdb_client import fetch_latest_portfolio_snapshot, fetch_positions_snapshot
from mystocks_data_collector.modules.client.tossinvest_api.orders_responses import TossInvestOrder
from mystocks_data_collector.modules.exc import APIResponseError
from mystocks_data_collector.modules.logics.collection import get_benchmark_stocks_current_prices, get_orders_full
from mystocks_data_collector.modules.logics.upload import DataUpdater
from mystocks_data_collector.modules.storage import S3Storage
from mystocks_data_collector.modules.types import ApiResponses, BenchmarkPosition, PortfolioSnapshot, Position, Transaction


logger = logging.getLogger(__name__)


async def collect_data_from_tossinvest() -> Tuple[str | None, ApiResponses | None]:
    try:
        async with TossInvestAPI() as api:
            await _get_tossinvest_access_token(api)
            return None, await asyncio.gather(
                get_benchmark_stocks_current_prices(api, list(Config.peer_stocks().keys())),
                api.get_buying_power(),
                api.get_stocks(),
            )

    except APIResponseError as e:
        logger.exception("토스 API 요청 오류 응답: {status=%s}", e.status_code)
        return (e.response_body, None)


async def collect_orders_from_tossinvest(from_date: date, to_date: date) -> Tuple[str | None, List[TossInvestOrder] | None]:
    try:
        async with TossInvestAPI() as api:
            await _get_tossinvest_access_token(api)
            return None, await get_orders_full(api, from_date=from_date, to_date=to_date)
    except APIResponseError as e:
        logger.exception("토스 API 요청 오류 응답: {status=%s}", e.status_code)
        return (e.response_body, None)


def update_datas(
        today: datetime,
        s3_storage: S3Storage,
        portfolio: PortfolioSnapshot,
        benchmarks: List[BenchmarkPosition],
        positions: List[Position],
):
    uploader = DataUpdater(s3_storage)
    today_date = today.date()

    uploader.update_topic("portfolio", [asdict(portfolio)], today_date)
    uploader.update_topic("benchmarks",[asdict(data) for data in benchmarks], today_date)
    uploader.update_topic("positions", [asdict(data) for data in positions], today_date)


def upload_transactions(
    target_date: date,
    s3_storage: S3Storage,
    transactions: List[Transaction]
):
    uploader = DataUpdater(s3_storage)
    uploader.update_transaction(transactions, target_date)


def transactions_already_uploaded(s3_storage: S3Storage, t: date) -> bool:
    return DataUpdater(s3_storage).exists("transactions", t)


def upload_position_view(s3_storage: S3Storage, duck_conn: duckdb.DuckDBPyConnection, now: datetime) -> str | None:
    s3_view_key = f"view/positions/{now.strftime("%Y-%m-%d")}.json"
    if s3_storage.exists(s3_view_key):
        return None

    # 총 보유현금 및 투자금 등 총합 관련 데이터 추출
    date_str = now.date().strftime("%Y%m%d")
    portfolio = fetch_latest_portfolio_snapshot(duck_conn, date_str)
    if portfolio is None:
        return None

    portfolio_id = portfolio.pop("id")

    positions = fetch_positions_snapshot(duck_conn, portfolio_id, date_str)

    for position in positions:
        if position["ticker"] in ETF_DISPLAY_NAMES:
            position["name"] = ETF_DISPLAY_NAMES[position["ticker"]]

        if position["ticker"] == "SGOV": # 추후 BOXX 같은 다른 채권 ETF를 투자하게 될 경우 해당 코드를 수정할 것
            portfolio["sgovBalance"] = position["marketValueExcludingFees"]

    uploaded_data = {
        "updateDate": now.strftime("%Y-%d-%m %H:%M"),
        "portfolio": portfolio,
        "stocks": positions,
    }

    s3_storage.put_object(s3_view_key, json.dumps(uploaded_data, ensure_ascii=False, default=str))

    return portfolio_id


async def _get_tossinvest_access_token(api: TossInvestAPI):
    res = await api.get_oauth2_access_token()
    access_token = res.access_token
    api.update_headers({"Authorization": f"Bearer {access_token}"})
