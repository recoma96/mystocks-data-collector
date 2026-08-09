from dataclasses import dataclass
import datetime
from typing import Dict, Tuple, TypeAlias
from uuid import UUID, uuid4


from mystocks_data_collector.modules.client.tossinvest_api.responses import TossInvestBuyingPowerResponse, TossInvestCurrentStockPriceResponse, TossInvestOrdersResponse, TossInvestStocksResponse


ApiRepsonses:  TypeAlias = Tuple[
    Dict[str, TossInvestCurrentStockPriceResponse],
    TossInvestBuyingPowerResponse,
    TossInvestStocksResponse,
    TossInvestOrdersResponse,
]

@dataclass
class BenchmarkPosition:
    id: UUID
    portpolio_id: UUID      # 포트폴리오 UID
    name: str               # 종목명
    ticker: str             # 티커명
    current_price: float     # 현재가
    log_date: datetime      # 로깅 시점
