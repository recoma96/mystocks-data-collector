from abc import ABCMeta

import boto3
from types_boto3_s3.client import S3Client
from types_boto3_s3.type_defs import ListObjectsV2OutputTypeDef

from mystocks_data_collector.config import Config


class Database(metaclass=ABCMeta):
    pass


class S3Database(Database):
    _s3: S3Client
    
    def __init__(self):
        super().__init__()
        self._s3 = boto3.client("s3", region_name=Config.AWS_REGION_NAME)

    def list_keys(self):
        # TODO S3 작동 여부를 위한 코드로 추후 삭제 예정
        response: ListObjectsV2OutputTypeDef = self._s3.list_objects_v2(Bucket=Config.S3_BUCKET)

        print(response)
