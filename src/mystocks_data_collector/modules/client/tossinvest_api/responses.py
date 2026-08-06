from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from mystocks_data_collector.modules.client.tossinvest_api.holdings_responses import (
    TossInvestCurrencyAmount,
    TossInvestPortfolioMarketValue,
    TossInvestPortfolioProfitLoss,
    TossInvestPortfolioDailyProfitLoss,
    TossInvestHolding,
)
from mystocks_data_collector.modules.client.tossinvest_api.orders_responses import TossInvestOrder


class TossInvestOauth2AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int # 만료 기한을 정수형으로 표현


class TossInvestCurrentStockPriceResponse(BaseModel):
    ticker: str
    current_price: float
    current_time: datetime


class TossInvestBuyingPowerResponse(BaseModel):
    cash_buying_power: float


class TossInvestStocksResponse(BaseModel):
    total_purchase_amount: TossInvestCurrencyAmount = Field(alias="totalPurchaseAmount")
    market_value: TossInvestPortfolioMarketValue = Field(alias="marketValue")
    profit_loss: TossInvestPortfolioProfitLoss = Field(alias="profitLoss")
    daily_profit_loss: TossInvestPortfolioDailyProfitLoss = Field(alias="dailyProfitLoss")
    items: List[TossInvestHolding]


class TossInvestOrdersResponse(BaseModel):
    has_next: bool = Field(alias="hasNext")
    next_cursor: str | None = Field(alias="nextCursor")
    orders: List[TossInvestOrder]
