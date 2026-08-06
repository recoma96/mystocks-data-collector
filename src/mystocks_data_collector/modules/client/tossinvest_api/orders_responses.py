from datetime import datetime
from enum import auto

from pydantic import BaseModel, Field

from mystocks_data_collector.modules.client.enum import UpperCaseStrEnum


class TossInvestOrderSide(UpperCaseStrEnum):
    BUY = auto()
    SELL = auto()


class TossInvestOrderStatus(UpperCaseStrEnum):
    PENDING = auto()
    PENDING_CANCEL = auto()
    PENDING_REPLACE = auto()
    PARTIAL_FILLED = auto()
    FILLED = auto()
    CANCELED = auto()
    REJECTED = auto()
    CANCEL_REJECTED = auto()
    REPLACE_REJECTED = auto()
    REPLACED = auto()


class TossInvestOrder(BaseModel):
    currency: str
    execution: TossInvestExecution
    ordered_at: datetime = Field(alias="orderedAt")
    order_id: str = Field(alias="orderId")
    order_type: str = Field(alias="orderType")
    quantity: float
    side: TossInvestOrderSide
    symbol: str
    time_in_force: str = Field(alias="timeInForce")
    canceled_at: datetime | None = Field("canceledAt")
    order_amount: float | None = Field("orderAmount")
    price: float | None


class TossInvestExecution(BaseModel):
    average_filled_price: float = Field(alias="averageFilledPrice")
    commission: float
    filled_amount: float = Field(alias="filledAmount")
    filled_at: datetime = Field(alias="filledAt")
    filled_quantity: float = Field(alias="filledQuantity")
    settlement_date: datetime = Field("settlementDate")
    tax: float
