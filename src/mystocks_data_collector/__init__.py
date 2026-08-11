def main() -> None:
    # 개발 테스트용. 패키지 import 시점이 아니라 여기서만 .env를 로드하고 실행함
    from dotenv import load_dotenv
    load_dotenv()

    import logging
    logging.basicConfig()

    from mystocks_data_collector.handler import handler
    handler({}, {})
