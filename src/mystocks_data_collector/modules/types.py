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
    """수익 비교용 비교종목
    """
    id: UUID
    portpolio_id: UUID      # 포트폴리오 UID
    name: str               # 종목명
    ticker: str             # 티커명
    current_price: float     # 현재가
    log_date: datetime      # 로깅 시점


@dataclass
class Position:
    """보유 종목
    """
    id: UUID
    portpolio_id: UUID                  # 포트폴리오 UUID
    name: str                           # 종목명
    ticker: str                         # 티커명
    avg_purchase_price: float           # 평단가
    current_price: float                # 현재가
    quanity: float                      # 보유 주식 수
    cost_basis: float                   # 매수 금액
    market_value: float                 # 시장 평가 금액
    market_value_excluding_fees: float  # 수수료를 제외한 평가금액
    profit_amount: float                # 손익금액
    profit_amount_excluding_fees: float # 수수료를 제외한 손익금액
    profit_rate: float                  # 손익비율
    profit_rate_excluding_fees: float   # 수수료를 제외한 손익비율
    log_date: datetime

    def to_str(self):
        profit_amount_prefix = "-" if self.profit_amount_excluding_fees < 0 else "+"
        profit_rate_prefix = "-" if self.profit_rate_excluding_fees < 0 else "+"

        return (
            f"종목: {self.name} ({self.ticker})\n" +
            f"매수금액: ${self.cost_basis} ({self.quanity}주)\n" +
            f"평가금액(수수료제외): ${self.market_value_excluding_fees}\n" + 
            f"손익: {profit_amount_prefix}${abs(self.profit_amount_excluding_fees)} ({profit_rate_prefix}{abs(self.profit_rate_excluding_fees * 100)}%)\n"
        )
