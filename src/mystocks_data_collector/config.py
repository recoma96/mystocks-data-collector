import os


class Config:
    S3_BUCKET = os.getenv("S3_BUCKET")
    AWS_REGION_NAME = os.getenv("AWS_REGION_NAME", "ap-northeast-2")
