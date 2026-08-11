from datetime import date, datetime
from enum import  auto
from typing import Any, Dict, List

from mystocks_data_collector.modules.client import APIClient
from mystocks_data_collector.config import Config
from mystocks_data_collector.modules.client.enum import UpperCaseStrEnum
from mystocks_data_collector.modules.client.tossinvest_api.responses import (
    TossInvestBuyingPowerResponse,
    TossInvestCurrentStockPriceResponse,
    TossInvestOauth2AccessTokenResponse,
    TossInvestOrdersResponse,
    TossInvestStocksResponse,
)



class TossInvestOrderStatus(UpperCaseStrEnum):
    OPEN = auto()   # 주문진행중
    CLOSED = auto()  # 주문 완료


class TossInvestAPI(APIClient):
    BASE_URL = "https://openapi.tossinvest.com"

    def __init__(self, access_token: str | None = None):
        super().__init__(base_url=self.BASE_URL)
        if access_token:
            self.update_headers({"Authorization": f"Bearer {access_token}"})

    async def get_oauth2_access_token(self) -> TossInvestOauth2AccessTokenResponse:
        """토스 API를 사용하기 위한 엑세스 토큰 발급
        """
        # try를 하지 않은 이유 -> post에 발생하는 Exception 그대로 호출하기 위함
        raw_response = await self.post(
            "oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": Config.TOSSINVEST_CLIENT_ID,
                "client_secret": Config.TOSSINVEST_CLIENT_SECRET
            }
        )

        return TossInvestOauth2AccessTokenResponse(**raw_response)

    async def get_current_stock_price(self, ticker: str) -> TossInvestCurrentStockPriceResponse | None:
        """특정 종목의 현재가
        """
        raw_response = await self.get(
            "api/v1/prices",
            params={
                "symbols": ticker,
            }
        )

        # 토스 API에서는 해당 티커명과 연관된 모든 종목을 가져온다
        # 하지만 여기에선 무조건 일치하는 티커명만 찾는다
        stocks: List[Dict[str, Any]] = raw_response.get("result", [])

        for stock in stocks:
            if stock["symbol"] == ticker:
                return TossInvestCurrentStockPriceResponse(
                    ticker=ticker,
                    current_price=stock["lastPrice"],
                    current_time=datetime.fromisoformat(stock["timestamp"])
                )

        return None

    async def get_buying_power(self, account_number: int = 1) -> TossInvestBuyingPowerResponse:
        """매수 가능한 현금 조회
            주식 시장에서 현금을 buying power 라고 한다
        """
        self._put_account_number_into_header(account_number)

        raw_response = await self.get(
            "api/v1/buying-power",
            params={
                "currency": "USD", # 미국장만 확인
            }
        )

        return TossInvestBuyingPowerResponse(
            cash_buying_power=raw_response["result"]["cashBuyingPower"]
        )

    async def get_stocks(self, account_number: int = 1) -> TossInvestStocksResponse:
        """보유 종목 조회
        """
        self._put_account_number_into_header(account_number)

        raw_response = await self.get("api/v1/holdings")

        return TossInvestStocksResponse(**raw_response["result"])

    async def get_orders(
            self,
            from_date: date,
            to_date: date,
            account_number: int = 1,
            status: TossInvestOrderStatus = TossInvestOrderStatus.CLOSED,
            limit: int = 20,
            cursor: str | None = None,
    ) -> TossInvestOrdersResponse:
        self._put_account_number_into_header(account_number)

        params = {
            "status": status.value,
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d"),
            "limit": limit,
        }

        if cursor:
            params["cursor"] = cursor

        raw_response = await self.get("api/v1/orders", params=params)

        # 체결 완료된 주문건만 필터링
        raw_response["result"]["orders"] = list(
            filter(lambda e: e["status"] == "FILLED", raw_response["result"]["orders"]))

        return TossInvestOrdersResponse(**raw_response["result"])


    def _put_account_number_into_header(self, account_number: int):
        self.set_header("X-Tossinvest-Account", str(account_number))
