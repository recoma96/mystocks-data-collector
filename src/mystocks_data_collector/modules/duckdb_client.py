import os
from contextlib import contextmanager
from typing import Dict, Iterator, List

import duckdb

from mystocks_data_collector.config import Config


@contextmanager
def connect_s3_duckdb() -> Iterator[duckdb.DuckDBPyConnection]:
    """S3 parquet 조회를 위한 DuckDB 커넥션을 생성한다.
    """
    with duckdb.connect() as conn:
        conn.execute("INSTALL httpfs; LOAD httpfs;")
        conn.execute("INSTALL aws; LOAD aws;")
        # 실행 환경(로컬/Lambda)의 기본 타임존과 무관하게 log_date를 항상 KST 기준으로 해석하기 위함
        conn.execute("SET TimeZone='Asia/Seoul';")

        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        if access_key and secret_key:
            # 로컬 개발 환경 전용: .env에만 있는 값이라 실제 Lambda에서는 이 분기를 안 탐
            # (EC2 메타데이터가 없는 로컬에서는 load_aws_credentials()의 자동 탐색이 느려서 직접 지정)
            conn.execute(f"""
                SET s3_region='{Config.AWS_REGION_NAME}';
                SET s3_access_key_id='{access_key}';
                SET s3_secret_access_key='{secret_key}';
            """)
        else:
            # 실제 Lambda 등 배포 환경: IAM 실행 역할로 빠르게 자동 로드됨
            conn.execute("CALL load_aws_credentials();")
            conn.execute(f"SET s3_region='{Config.AWS_REGION_NAME}';")

        yield conn


def fetch_latest_portfolio_snapshot(conn: duckdb.DuckDBPyConnection, date_str: str) -> Dict | None:
    """date_str(YYYYmmdd) 기준 포트폴리오 스냅샷 중, 오전 5시 이후로 가장 이른 데이터를 조회한다.
    """
    portfolio_table = f"read_parquet('s3://{Config.s3_bucket()}/data/portfolio/date={date_str}/data.parquet')"
    result = conn.execute(
        "SELECT" \
        "   id, " \
        "   total_value as totalValue," \
        "   positions_cost_basis as positionsCostBasis, " \
        "   positions_market_value as positionsMarketValue," \
        "   cash_balance as cashBalance, " \
        "   profit_amount_excluding_fees as profitAmountExcludingFees " \
        f"FROM {portfolio_table} " \
        "WHERE strftime(log_date, '%H:%M:%S') >= '05:00:00' " \
        "ORDER BY log_date asc " \
        "LIMIT 1"
    )
    row = result.fetchone()
    return dict(zip((col[0] for col in result.description), row)) if row else None

def fetch_positions_snapshot(conn: duckdb.DuckDBPyConnection, portfolio_id: str, date_str: str) -> List[Dict]:
    """포트폴리오 ID에 해당하는 포지션 데이터 조회
    """
    position_table = f"read_parquet('s3://{Config.s3_bucket()}/data/positions/date={date_str}/data.parquet')"
    result = conn.execute(
        "SELECT " \
        "   ticker, " \
        "   name, " \
        "   quantity, " \
        "   cost_basis as costBasis, " \
        "   market_value_excluding_fees as marketValueExcludingFees, " \
        "   avg_purchase_price as avgPurchasePrice, " \
        "   profit_amount_excluding_fees as profitAmountExcludingFees, " \
        "   profit_rate_excluding_fees * 100 as profitRateExcludingFees " \
        f"FROM {position_table} " \
        "WHERE portfolio_id = ?",
        [portfolio_id]
    )
    columns = [col[0] for col in result.description]
    return [dict(zip(columns, row)) for row in result.fetchall()]


def fetch_latest_benchmark_price_snapshot(conn: duckdb.DuckDBPyConnection, portfolio_id: str, date_str: str) -> List[Dict]:
    """포트폴리오 ID에 해당하는 벤치마크 종목 데이터 조회
    """
    benchmark_table = f"read_parquet('s3://{Config.s3_bucket()}/data/benchmarks/date={date_str}/data.parquet')"
    tickers = list(Config.peer_stocks().keys())
    placeholders = ",".join(["?"] * len(tickers))
    result = conn.execute(
        "SELECT " \
        "   ticker, " \
        "   current_price " \
        f"FROM {benchmark_table} " \
        f"WHERE portfolio_id = '{portfolio_id}' AND ticker IN ({placeholders}) ",
        tickers
    )
    columns = [col[0] for col in result.description]
    return [dict(zip(columns, row)) for row in result.fetchall()]


def fetch_transactions_single_day_snapshot(conn: duckdb.DuckDBPyConnection, date_str: str) -> List[Dict]:
    # from_date, to_date는 같은 월 이어야 한다.
    transaction_table = f"read_parquet('s3://{Config.s3_bucket()}/data/transactions/date={date_str}/data.parquet')"
    result = conn.execute(
        "SELECT " \
        "   type, " \
        "   ticker, " \
        "   order_quantity as quantity, " \
        "   filled_amount as amount, " \
        "   filled_at as filledAt " \
        f"FROM {transaction_table}"
    )
    columns = [col[0] for col in result.description]
    return [dict(zip(columns, row)) for row in result.fetchall()]
