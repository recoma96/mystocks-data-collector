from dotenv import load_dotenv
load_dotenv()

import logging

from mystocks_data_collector.handler import handler



def main() -> None:
    # 개발 테스트용
    logging.basicConfig()
    handler({}, {})
