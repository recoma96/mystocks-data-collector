from datetime import datetime

import pytest

from mystocks_data_collector.modules.client.tossinvest_api.orders_responses import TossInvestOrder
from mystocks_data_collector.modules.client.tossinvest_api.responses import (
    TossInvestBuyingPowerResponse,
    TossInvestCurrentStockPriceResponse,
    TossInvestStocksResponse,
)
from mystocks_data_collector.modules.logics.transform import (
    create_portfolio_by_api_response,
    create_transactions_by_api_responses,
)
from mystocks_data_collector.modules.types import TransactionType


def _make_stocks_response() -> TossInvestStocksResponse:
    return TossInvestStocksResponse(**{
        "totalPurchaseAmount": {"krw": 0, "usd": 6500.0},
        "marketValue": {
            "amount": {"krw": 0, "usd": 7200.0},
            "amountAfterCost": {"krw": 0, "usd": 7050.0},
        },
        "profitLoss": {
            "amount": {"krw": 0, "usd": 700.0},
            "amountAfterCost": {"krw": 0, "usd": 550.0},
            "rate": 0.1077,
            "rateAfterCost": 0.0846,
        },
        "dailyProfitLoss": {"amount": {"krw": 0, "usd": 100.0}, "rate": 0.0141},
        "items": [
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "marketCountry": "US",
                "currency": "USD",
                "quantity": 10,
                "lastPrice": 178.5,
                "averagePurchasePrice": 155.3,
                "marketValue": {"purchaseAmount": 1553.0, "amount": 1785.0, "amountAfterCost": 1771.43},
                "profitLoss": {"amount": 232.0, "amountAfterCost": 218.43, "rate": 0.1494, "rateAfterCost": 0.1406},
                "dailyProfitLoss": {"amount": 25.0, "rate": 0.0142},
                "cost": {"commission": 3.57, "tax": 10.0},
            }
        ],
    })


def _make_order(order_id: str, side: str) -> TossInvestOrder:
    return TossInvestOrder(**{
        "currency": "USD",
        "execution": {
            "averageFilledPrice": 178.5,
            "commission": 1.0,
            "filledAmount": 1785.0,
            "filledAt": "2026-08-11T10:00:00",
            "filledQuantity": 10,
            "settlementDate": "2026-08-13T00:00:00",
            "tax": 0.5,
        },
        "orderedAt": "2026-08-11T09:55:00",
        "orderId": order_id,
        "orderType": "MARKET",
        "quantity": 10,
        "side": side,
        "symbol": "AAPL",
        "timeInForce": "DAY",
        "canceledAt": None,
        "orderAmount": 1785.0,
        "price": None,
    })


def test_create_portfolio_by_api_response_calculates_expected_values(monkeypatch: pytest.MonkeyPatch):
    # 실제 .env에 의존하지 않도록, 이 테스트에서만 쓸 값을 직접 주입
    monkeypatch.setenv("PEER_STOCKS_TICKER", "QQQ")
    monkeypatch.setenv("PEER_STOCKS_NAME", "테스트벤치마크")
    ticker = "QQQ"
    benchmark_prices = {
        ticker: TossInvestCurrentStockPriceResponse(
            ticker=ticker, current_price=500.0, current_time=datetime(2026, 8, 11, 10, 0)
        )
    }
    buying_power = TossInvestBuyingPowerResponse(cash_buying_power=1000.0)
    stocks = _make_stocks_response()

    benchmarks, positions, portfolio = create_portfolio_by_api_response(benchmark_prices, buying_power, stocks)

    assert benchmarks[0].ticker == ticker
    assert benchmarks[0].current_price == 500.0

    assert len(positions) == 1
    position = positions[0]
    assert position.ticker == "AAPL"
    assert position.cost_basis == 1553.0
    assert position.market_value == 1785.0
    assert position.profit_amount == 232.0
    assert position.profit_rate == 0.1494

    assert portfolio.cash_balance == 1000.0
    assert portfolio.positions_cost_basis == 6500.0
    assert portfolio.positions_market_value == 7200.0
    assert portfolio.total_value == 1000.0 + 7050.0
    assert portfolio.total_value_basis == 1000.0 + 6500.0
    assert portfolio.profit_amount == 700.0
    assert portfolio.profit_amount_excluding_fees == 550.0


def test_create_transactions_by_api_responses_maps_buy_and_sell():
    orders = [_make_order("order-buy", "BUY"), _make_order("order-sell", "SELL")]

    transactions = create_transactions_by_api_responses(orders)

    assert [t.type for t in transactions] == [TransactionType.BUY, TransactionType.SELL]
    assert transactions[0].order_id == "order-buy"
    assert transactions[0].ticker == "AAPL"
    assert transactions[0].order_quantity == 10
    assert transactions[0].filled_amount == 1785.0
    assert transactions[0].avg_price == 178.5