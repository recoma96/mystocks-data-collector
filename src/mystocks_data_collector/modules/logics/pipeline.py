import asyncio
import json
import logging
from dataclasses import asdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple

import duckdb

from mystocks_data_collector.config import Config
from mystocks_data_collector.modules.client.tossinvest_api.client import TossInvestAPI
from mystocks_data_collector.modules.constants import ETF_DISPLAY_NAMES
from mystocks_data_collector.modules.duckdb_client import fetch_latest_benchmark_price_snapshot, fetch_latest_portfolio_snapshot, fetch_positions_snapshot, fetch_transactions_single_day_snapshot
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


def upload_position_view(s3_storage: S3Storage, duck_conn: duckdb.DuckDBPyConnection, now: datetime) -> Tuple[Dict, str] | None:
    s3_view_key = f"view/positions/{now.strftime("%Y-%m-%d")}.json"
    if s3_storage.exists(s3_view_key):
        return None

    # 총 보유현금 및 투자금 등 총합 관련 데이터 추출
    date_str = now.date().strftime("%Y%m%d")
    portfolio = fetch_latest_portfolio_snapshot(duck_conn, date_str)
    if portfolio is None:
        return None

    portfolio_id: str = portfolio.pop("id")

    positions = fetch_positions_snapshot(duck_conn, portfolio_id, date_str)

    for position in positions:
        if position["ticker"] in ETF_DISPLAY_NAMES:
            position["name"] = ETF_DISPLAY_NAMES[position["ticker"]]

        if position["ticker"] == "SGOV": # 추후 BOXX 같은 다른 채권 ETF를 투자하게 될 경우 해당 코드를 수정할 것
            portfolio["sgovBalance"] = position["marketValueExcludingFees"]

    uploaded_data: Dict = {
        "updateDate": now.strftime("%Y-%m-%d %H:%M"),
        "portfolio": portfolio,
        "stocks": positions,
    }

    s3_storage.put_object(s3_view_key, json.dumps(uploaded_data, ensure_ascii=False, default=str))

    return uploaded_data, portfolio_id


def upload_histories_view(
        s3_storage: S3Storage,
        duck_conn: duckdb.DuckDBPyConnection,
        portfolio_data: Dict,
        portfolio_id: int,
        now: datetime
):
    VIEW_KEY_FORMAT = "view/histories/{}.json"
    
    s3_view_key = VIEW_KEY_FORMAT.format(now.strftime("%Y-%m-%d"))
    if s3_storage.exists(s3_view_key):
        return None

    uploaded_data: Dict = { # 초기화
        "myPortfolio": {},
        "histories": [],
        "benchMarks": []
    }

    # 과거 view.json에 누적으로 쌓기 위함
    yesterday = now - timedelta(days=1)
    s3_yesterday_view_key = VIEW_KEY_FORMAT.format(yesterday.strftime("%Y-%m-%d"))
    if s3_storage.exists(s3_yesterday_view_key):
        yesterday_view_bytes = s3_storage.get_object(s3_yesterday_view_key)
        if yesterday_view_bytes is not None:
            uploaded_data = json.loads(yesterday_view_bytes)

    # 오늘자 SGOV 데이터 찾기
    sgov_value = 0
    for stock in portfolio_data["stocks"]:
        if stock["ticker"] == "SGOV":
            sgov_value = stock["marketValueExcludingFees"]

    portfolio_data = portfolio_data["portfolio"]

    # myPortfolio 수정
    uploaded_data["myPortfolio"] = {
        "current": {
            "totalValue": portfolio_data["totalValue"],
            "profitAmountExcludingFees": portfolio_data["profitAmountExcludingFees"],
            "profitRateExcludingFees": (int(portfolio_data["profitAmountExcludingFees"]) / int(portfolio_data["totalValue"])) * 100,   
        }
    }

    # histories 수정
    uploaded_data["histories"].append({
        "date": now.strftime("%Y-%m-%d"),
        "cash": portfolio_data["cashBalance"],
        "sgov": sgov_value,
        "investments": portfolio_data["positionsMarketValue"] - sgov_value,
        "profitRateExcludingFees": uploaded_data["myPortfolio"]["current"]["profitRateExcludingFees"],
    })

    # benchmarks 조회 및 수정
    latest_benchmarks_raw = fetch_latest_benchmark_price_snapshot(duck_conn, portfolio_id, now.strftime("%Y%m%d"))
    latest_benchmark_prices = { e["ticker"]: e["current_price"] for e in latest_benchmarks_raw }

    # TODO 더이상 비교군에 포함되지 않은 종목을 삭제해야 하나
    # 최소 몇개월간 VOO, QQQ, QLD로 진행할 예정이므로 해당 로직은 추후 추가 예정

    # 기존 benchmark history에 추가
    yesterday_benckmark_tickers = [benchmark["ticker"] for benchmark in uploaded_data["benchMarks"]]

    for benchmark in uploaded_data["benchMarks"]:
        if benchmark["ticker"] in latest_benchmark_prices.keys():
            benchmark["histories"].append({
                "date": now.strftime("%Y-%m-%d"),
                "price": latest_benchmark_prices[benchmark["ticker"]],
                "profitRate": (((latest_benchmark_prices[benchmark["ticker"]] - benchmark["histories"][0]["price"]) / benchmark["histories"][0]["price"])) * 100
            })

    for latest_benchmark_ticker, latest_price in latest_benchmark_prices.items():
        if latest_benchmark_ticker not in yesterday_benckmark_tickers:
            uploaded_data["benchMarks"].append({
                "ticker": latest_benchmark_ticker,
                "name": Config.peer_stocks()[latest_benchmark_ticker],
                "histories": [{
                    "date": now.strftime("%Y-%m-%d"),
                    "price": latest_price,
                    "profitRate": 0,
                }]
            })

    s3_storage.put_object(s3_view_key, json.dumps(uploaded_data, ensure_ascii=False, default=str))


def upload_transactions_view(
        s3_storage: S3Storage,
        duck_conn: duckdb.DuckDBPyConnection,
        now: datetime
):
    yesterday = now - timedelta(days=1)
    VIEW_KEY_FORMAT = "view/transactions/{}.json"
    
    s3_view_key = VIEW_KEY_FORMAT.format(yesterday.strftime("%Y-%m"))
    uploaded_data = {
        "date": yesterday.strftime("%Y-%m"),
        "histories": []
    }
    if s3_storage.exists(s3_view_key):
        uploaded_data_bytes = s3_storage.get_object(s3_view_key)
        if uploaded_data_bytes is not None:
            uploaded_data = json.loads(uploaded_data_bytes)

    today_transactions = fetch_transactions_single_day_snapshot(duck_conn, yesterday.strftime("%Y%m%d"))

    for transaction in today_transactions:
        uploaded_data["histories"].append({
            "type": transaction["type"].lower(),
            "ticker": transaction["ticker"],
            "quantity": transaction["quantity"],
            "amount": transaction["amount"],
            "filledAt": transaction["filledAt"].strftime("%Y-%m-%d %H:%M:%S")
        })

    s3_storage.put_object(s3_view_key, json.dumps(uploaded_data, ensure_ascii=False, default=str))


async def _get_tossinvest_access_token(api: TossInvestAPI):
    res = await api.get_oauth2_access_token()
    access_token = res.access_token
    api.update_headers({"Authorization": f"Bearer {access_token}"})
