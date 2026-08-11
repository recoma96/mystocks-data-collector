from typing import Dict, List, Tuple
from uuid import uuid4

from mystocks_data_collector.config import Config
from mystocks_data_collector.modules.client.tossinvest_api.orders_responses import TossInvestOrder
from mystocks_data_collector.modules.client.tossinvest_api.responses import (
    TossInvestBuyingPowerResponse,
    TossInvestCurrentStockPriceResponse,
    TossInvestStocksResponse
)
from mystocks_data_collector.modules.types import BenchmarkPosition, PortfolioSnapshot, Position, Transaction, TransactionType
from mystocks_data_collector.modules.utils import now_korea


def create_portfolio_by_api_response(
        res_benchmark_prices: Dict[str, TossInvestCurrentStockPriceResponse],
        res_buying_power: TossInvestBuyingPowerResponse,
        res_stocks: TossInvestStocksResponse,
) -> Tuple[List[BenchmarkPosition], List[Position], PortfolioSnapshot]:
    new_portfolio_id = str(uuid4())
    today = now_korea()

    benchmark_positions = [
        BenchmarkPosition(
            id=str(uuid4()),
            portfolio_id=new_portfolio_id,
            name=Config.peer_stocks()[ticker],
            ticker=ticker,
            current_price=item.current_price,
            log_date=today,
        )
        for ticker, item
        in res_benchmark_prices.items()
    ]

    positions = [
        Position(
            id=str(uuid4()),
            portfolio_id=new_portfolio_id,
            name=item.name,
            ticker=item.symbol,
            avg_purchase_price=item.average_purchase_price,
            current_price=item.last_price,
            quantity=item.quantity,
            cost_basis=item.market_value.purchase_amount,
            market_value=item.market_value.amount,
            market_value_excluding_fees=item.market_value.amount_after_cost,
            profit_amount=item.profit_loss.amount,
            profit_amount_excluding_fees=item.profit_loss.amount_after_cost,
            profit_rate=item.profit_loss.rate,
            profit_rate_excluding_fees=item.profit_loss.rate_after_cost,
            log_date=today,
        )
        for item in res_stocks.items
    ]

    portfolio_snapshot = PortfolioSnapshot(
        id=new_portfolio_id,
        total_value=res_buying_power.cash_buying_power + res_stocks.market_value.amount_after_cost.usd,
        total_value_basis=res_buying_power.cash_buying_power + res_stocks.total_purchase_amount.usd,
        cash_balance=res_buying_power.cash_buying_power,
        positions_cost_basis=res_stocks.total_purchase_amount.usd,
        positions_market_value=res_stocks.market_value.amount.usd,
        positions_market_value_excluding_fees=res_stocks.market_value.amount_after_cost.usd,
        profit_amount=res_stocks.profit_loss.amount.usd,
        profit_amount_excluding_fees=res_stocks.profit_loss.amount_after_cost.usd,
        log_date=today,
    )

    return benchmark_positions, positions, portfolio_snapshot


def create_transactions_by_api_responses(orders: List[TossInvestOrder]) -> List[Transaction]:
    transactions = [
        Transaction(
            id=str(uuid4()),
            order_id=item.order_id,
            ticker=item.symbol,
            type=TransactionType.BUY if item.side == "BUY" else TransactionType.SELL,
            order_amount=item.order_amount,
            order_quantity=item.quantity,
            filled_amount=item.execution.filled_amount,
            avg_price=item.execution.average_filled_price,
            filled_at=item.execution.filled_at,
            log_date=now_korea(),
        )
        for item in orders
    ]
    return transactions
