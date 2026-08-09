from typing import Dict
from uuid import UUID, uuid4

from mystocks_data_collector.config import Config
from mystocks_data_collector.modules.client.tossinvest_api.responses import TossInvestBuyingPowerResponse, TossInvestCurrentStockPriceResponse, TossInvestOrdersResponse, TossInvestStocksResponse
from mystocks_data_collector.modules.types import BenchmarkPosition


def create_portpolio_by_api_repsonse(
        res_benchmark_prices: Dict[str, TossInvestCurrentStockPriceResponse],
        res_buying_power: TossInvestBuyingPowerResponse,
        res_stocks: TossInvestStocksResponse,
        res_orders: TossInvestOrdersResponse,
):
    new_portpolio_id: UUID = uuid4()

    benchmark_positions = [
        BenchmarkPosition(
            id=uuid4(),
            portpolio_id=new_portpolio_id,
            name=Config.PEER_STOCKS[ticker],
            ticker=ticker,
            current_price=item.current_price,
            log_date=item.current_time,
        )
        for ticker, item
        in res_benchmark_prices.items()
    ]
