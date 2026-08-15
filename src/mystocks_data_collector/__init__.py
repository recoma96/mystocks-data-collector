def main() -> None:
    from dotenv import load_dotenv
    load_dotenv()

    import logging
    logging.basicConfig()

    from mystocks_data_collector.handler import handler
    handler({}, {})
