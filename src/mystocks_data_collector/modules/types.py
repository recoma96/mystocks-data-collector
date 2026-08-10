from dataclasses import dataclass
import datetime
from enum import auto
from typing import Dict, List, Tuple, TypeAlias
from uuid import UUID


from mystocks_data_collector.modules.client.tossinvest_api.orders_responses import TossInvestOrder
from mystocks_data_collector.modules.client.tossinvest_api.responses import (
    TossInvestBuyingPowerResponse, 
    TossInvestCurrentStockPriceResponse, 
    TossInvestStocksResponse
)


ApiRepsonses:  TypeAlias = Tuple[
    Dict[str, TossInvestCurrentStockPriceResponse],
    TossInvestBuyingPowerResponse,
    TossInvestStocksResponse,
    List[TossInvestOrder],
]


class TransactionType:
    BUY = auto()
    SELL = auto()


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


@dataclass
class Transaction:
    id: UUID
    portpolio_id: int           # 포트폴리오 UUID
    order_id: str               # 토스에서 제공하는 ID
    ticker: str                 # 티커명
    type: TransactionType       # 판매/구매
    order_amount: float         # 주문 금액
    order_quanity: float        # 주문 개수(주)
    filled_amount: float        # 최종 체결 금액
    avg_price: float            # 판매 당시 평단가
    filled_at: datetime         # 최종 결제 시간
    log_date: datetime

    def to_str(self):
        type_korean = "매도" if self.type == TransactionType.SELL else "매수"
        return (
            f"체결날짜: {self.filled_at}",
            f"티커명: {self.ticker}",
            f"${self.filled_amount} ({self.order_quanity}주) {type_korean}",
            f"평단가: ${self.avg_price}"   
        )


@dataclass
class PortpolioSnapshot:
    """
    보유 투자금 및 현금 상태
    """
    id: UUID
    total_asset_value: float                        # 달러 계좌에 있는 총 금액
    cash_balance: float                             # 보유 현금
    positions_cost_basis: float                     # 투자원금
    positions_cost_basis_excluding_fees: float      # 수수료를 제외한 투자원금
    positions_market_value: float                   # 평가금액
    positions_market_value_excluding_fees: float    # 수수료를 제외한 평가금액
    profit_amount: float                            # 손익금액
    profit_amount_excluding_fees: float             # 수수료를 제외한 손익금액
    profit_rate: float                              # 손익비율
    profit_rate_excluding_fees: float               # 투자금액을 제외한 손익비율
    log_date: datetime

