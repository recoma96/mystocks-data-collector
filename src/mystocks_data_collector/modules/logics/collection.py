from datetime import date
from typing import Dict, List
import asyncio

from mystocks_data_collector.modules.client.tossinvest_api.client import TossInvestAPI, TossInvestOrderStatus
from mystocks_data_collector.modules.client.tossinvest_api.orders_responses import TossInvestOrder
from mystocks_data_collector.modules.client.tossinvest_api.responses import TossInvestCurrentStockPriceResponse


async def get_benchmark_stocks_current_prices(
        api: TossInvestAPI, benchmark_stock_tickers: List[str]
) -> Dict[str, TossInvestCurrentStockPriceResponse]:
    stocks = await asyncio.gather(
        *[api.get_current_stock_price(ticker) for ticker in benchmark_stock_tickers]
    )

    return {stock.ticker: stock for stock in stocks if stock is not None}


async def get_orders_full(
        api: TossInvestAPI,
        from_date: date,
        to_date: date,
        status: TossInvestOrderStatus = TossInvestOrderStatus.CLOSED,
        limit: int = 20,
) -> List[TossInvestOrder]:
    current_cursor: str | None = None
    cnt = 0
    orders: List[TossInvestOrder] = []

    while (cnt == 0 or current_cursor is not None):
        response = await api.get_orders(
            from_date=from_date, to_date=to_date, status=status, limit=limit, cursor=current_cursor
        )

        orders.extend(response.orders)

        current_cursor = response.next_cursor
        cnt += 1

    return orders
