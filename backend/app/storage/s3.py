from __future__ import annotations

import asyncio
from typing import Any

from app.storage.base import ObjectNotFoundError, StorageError, validate_key

GCS_S3_ENDPOINT = "https://storage.googleapis.com"


class S3Storage:
    """AWS S3 or any S3-compatible store, including Google Cloud Storage's XML API.

    `boto3` is an optional dependency (`pip install ".[s3]"`), imported only when this
    backend is configured.
    """

    def __init__(
        self,
        *,
        bucket: str,
        access_key: str | None = None,
        secret_key: str | None = None,
        endpoint_url: str | None = None,
        region: str | None = None,
        client: Any = None,
    ) -> None:
        self.bucket = bucket
        if client is None:
            import boto3
            from botocore.config import Config

            client = boto3.client(
                "s3",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                endpoint_url=endpoint_url,
                region_name=region,
                config=Config(retries={"max_attempts": 3, "mode": "standard"}),
            )
        self._client = client

    async def put(self, key: str, data: bytes, *, content_type: str) -> None:
        await self._call(
            "put_object",
            Bucket=self.bucket,
            Key=validate_key(key),
            Body=data,
            ContentType=content_type,
        )

    async def get(self, key: str) -> bytes:
        response = await self._call("get_object", Bucket=self.bucket, Key=validate_key(key))
        return await asyncio.to_thread(response["Body"].read)

    async def delete(self, key: str) -> None:
        await self._call("delete_object", Bucket=self.bucket, Key=validate_key(key))

    async def _call(self, method: str, **kwargs: Any) -> Any:
        from botocore.exceptions import BotoCoreError, ClientError

        try:
            return await asyncio.to_thread(getattr(self._client, method), **kwargs)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in {"NoSuchKey", "404", "NotFound"}:
                raise ObjectNotFoundError(kwargs.get("Key", "")) from exc
            raise StorageError(f"{method} failed: {code}") from exc
        except BotoCoreError as exc:
            raise StorageError(f"{method} failed: {exc}") from exc
