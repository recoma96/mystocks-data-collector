from datetime import date
from typing import Any, List, Dict

import pandas as pd
import io

from mystocks_data_collector.modules.storage import S3Storage


class DataUpdater:
    s3_storage: S3Storage

    S3_PREFIX = "data"

    def __init__(self, s3_storage: S3Storage):
        self.s3_storage = s3_storage

    def update_topic(self, topic: str, datas: List[Dict[str, Any]], t: date):
        if len(datas) < 1:
            return

        df = self.download(topic, t)

        if df is None:
            df = pd.DataFrame(datas)
        else:
            new_df = pd.DataFrame(datas)
            df = pd.concat([df, new_df], ignore_index=True)

        key = self._get_key(t, topic)
        self.s3_storage.put_bytes(key, self._pandas_to_bytes(df))

    def download(self, topic: str, t: date) -> pd.DataFrame | None:
        key = self._get_key(t, topic)

        byptedata =  self.s3_storage.get_object(key)

        if not byptedata:
            return None

        return self._bytes_to_pandas(byptedata)

    def _bytes_to_pandas(self, bytedata: bytes) -> pd.DataFrame:
        buffer = io.BytesIO(bytedata)
        df_loaded = pd.read_parquet(buffer, engine="pyarrow")
        return df_loaded

    def _pandas_to_bytes(self, df: pd.DataFrame) -> bytes:
        buffer = io.BytesIO()
        df.to_parquet(buffer, engine="pyarrow", index=False)
        return buffer.getvalue()

    def _get_key(self, t: date, topic: str) -> str:
        return f"{self.S3_PREFIX}/{topic}/date={t:%Y%m%d}/data.parquet"
