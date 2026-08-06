import asyncio
from datetime import date
import logging

from mystocks_data_collector.modules.client.tossinvest_api.client import TossInvestAPI, TossInvestOrderStatus
from mystocks_data_collector.modules.client.tossinvest_api.responses import TossInvestStocksResponse
from mystocks_data_collector.modules.exc import APIResponseError



def handler(event, context):
    _set_before_handler()
    asyncio.run(main())


def _set_before_handler():
    _set_logger()


def _set_logger():
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


async def main():
    async with TossInvestAPI() as api:
        token_response = await api.get_oauth2_access_token()
        access_token = token_response.access_token

    async with TossInvestAPI(access_token) as api:
        try:
            response: TossInvestStocksResponse = await api.get_orders(
                from_date = date(year=2026, month=8, day=4),
                to_date = date(year=2026, month=8, day=5),
            )
        except APIResponseError as e:
            print(e.response_body)
