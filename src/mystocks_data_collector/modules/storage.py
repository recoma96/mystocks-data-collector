import json
from typing import Any

import boto3
from botocore.exceptions import ClientError
from types_boto3_s3.client import S3Client

from mystocks_data_collector.config import Config
from mystocks_data_collector.modules.utils import now_korea


class S3Storage:
    _s3: S3Client

    def __init__(self):
        super().__init__()
        self._s3 = boto3.client("s3", region_name=Config.AWS_REGION_NAME)

    def put_object(self, key: str, body: str) -> None:
        self._s3.put_object(Bucket=Config.s3_bucket(), Key=key, Body=body.encode("utf-8"))

    def put_bytes(self, key: str, body: bytes) -> None:
        self._s3.put_object(Bucket=Config.s3_bucket(), Key=key, Body=body)

    def get_object(self, key: str) -> bytes | None:
        try:
            response = self._s3.get_object(Bucket=Config.s3_bucket(), Key=key)
        except self._s3.exceptions.NoSuchKey:
            return None

        return response["Body"].read()

    def exists(self, key: str) -> bool:
        try:
            self._s3.head_object(Bucket=Config.s3_bucket(), Key=key)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

        return True

    def write_snapshot(self, topic: str, body: Any) -> None:
        # PATH: {topic}/{YYYY}/{MM}/{DD}/snapshot-{HH}-{mm}-{ss}-{millisecond}.json
        now = now_korea()
        key = (
            f"raw/{topic}/{now:%Y}/{now:%m}/{now:%d}/"
            f"snapshot-{now:%H}-{now:%M}-{now:%S}-{now.microsecond // 1000:03d}.json"
        )

        self.put_object(key, json.dumps(body, ensure_ascii=False, default=str, indent=2))