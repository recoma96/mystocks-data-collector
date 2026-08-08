from typing import Dict, List
import asyncio

from mystocks_data_collector.modules.client.tossinvest_api.client import TossInvestAPI
from mystocks_data_collector.modules.client.tossinvest_api.responses import TossInvestCurrentStockPriceResponse


async def get_benchmark_stocks_current_prices(
        api: TossInvestAPI, benchmark_stock_tickers: List[str]
) -> Dict[str, TossInvestCurrentStockPriceResponse]:
    stocks = await asyncio.gather(
        *[api.get_current_stock_price(ticker) for ticker in benchmark_stock_tickers]
    )

    return {stock.ticker: stock for stock in stocks if stock is not None}
