from pydantic import BaseModel, Field


class TossInvestCurrencyAmount(BaseModel):
    krw: float
    usd: float | None # 국장의 경우 null


class TossInvestPortfolioMarketValue(BaseModel):
    amount: TossInvestCurrencyAmount
    amount_after_cost: TossInvestCurrencyAmount = Field(alias="amountAfterCost")


class TossInvestPortfolioProfitLoss(BaseModel):
    amount: TossInvestCurrencyAmount
    amount_after_cost: TossInvestCurrencyAmount = Field(alias="amountAfterCost")
    rate: float
    rate_after_cost: float = Field(alias="rateAfterCost")


class TossInvestPortfolioDailyProfitLoss(BaseModel):
    amount: TossInvestCurrencyAmount
    rate: float


class TossInvestHoldingMarketValue(BaseModel):
    purchase_amount: float = Field(alias="purchaseAmount")
    amount: float
    amount_after_cost: float = Field(alias="amountAfterCost")


class TossInvestHoldingProfitLoss(BaseModel):
    amount: float
    amount_after_cost: float = Field(alias="amountAfterCost")
    rate: float
    rate_after_cost: float = Field(alias="rateAfterCost")


class TossInvestHoldingDailyProfitLoss(BaseModel):
    amount: float
    rate: float


class TossInvestHoldingCost(BaseModel):
    commission: float
    tax: float | None


class TossInvestHolding(BaseModel):
    symbol: str
    name: str
    market_country: str = Field(alias="marketCountry")
    currency: str
    quantity: float
    last_price: float = Field(alias="lastPrice")
    average_purchase_price: float = Field(alias="averagePurchasePrice")
    market_value: TossInvestHoldingMarketValue = Field(alias="marketValue")
    profit_loss: TossInvestHoldingProfitLoss = Field(alias="profitLoss")
    daily_profit_loss: TossInvestHoldingDailyProfitLoss = Field(alias="dailyProfitLoss")
    cost: TossInvestHoldingCost
