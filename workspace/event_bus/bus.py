from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Iterable

from workspace.event_bus.events import AgentEvent, StreamEventRecord, validate_stream_name
from workspace.event_bus.streams import ALL_STREAMS, StreamName

RedisClientFactory: type[Any] | None = None
ResponseError: type[Exception] = Exception
try:
    from redis import Redis as _ImportedRedis
    from redis.exceptions import ResponseError as _ImportedResponseError
except ImportError:  # pragma: no cover - import-safe fallback
    pass
else:
    RedisClientFactory = _ImportedRedis
    ResponseError = _ImportedResponseError


def _read_int_env(name: str, *, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    return int(raw_value)


def _read_optional_int_env(name: str) -> int | None:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return None
    return int(raw_value)


@dataclass
class RedisStreamBus:
    host: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: _read_int_env("REDIS_PORT", default=6379))
    db: int = field(default_factory=lambda: _read_int_env("REDIS_DB", default=0))
    password: str | None = field(default_factory=lambda: os.getenv("REDIS_PASSWORD"))
    stream_maxlen: int | None = field(default_factory=lambda: _read_optional_int_env("REDIS_STREAM_MAXLEN"))
    client: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.client = self.connect()

    def connect(self) -> Any:
        if RedisClientFactory is None:
            return None

        return RedisClientFactory(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            decode_responses=True,
        )

    def publish(self, stream: StreamName, event: AgentEvent | dict[str, Any]) -> str:
        client = self.require_client()
        stream_name = validate_stream_name(stream)
        message = event if isinstance(event, AgentEvent) else AgentEvent.from_dict(event)

        kwargs: dict[str, Any] = {
            "name": stream_name,
            "fields": message.to_stream_fields(),
            "id": "*",
        }
        if self.stream_maxlen:
            kwargs["maxlen"] = self.stream_maxlen
            kwargs["approximate"] = True

        return str(client.xadd(**kwargs))

    def read_streams(
        self,
        streams: dict[StreamName, str],
        *,
        count: int = 10,
        block_ms: int = 1_000,
    ) -> list[StreamEventRecord]:
        client = self.require_client()
        typed_streams = {validate_stream_name(stream): offset for stream, offset in streams.items()}
        return self._decode_read_result(client.xread(streams=typed_streams, count=count, block=block_ms))

    def ensure_consumer_group(
        self,
        stream: StreamName,
        group_name: str,
        *,
        start_id: str = "0",
        mkstream: bool = True,
    ) -> None:
        client = self.require_client()
        try:
            client.xgroup_create(
                name=validate_stream_name(stream),
                groupname=group_name,
                id=start_id,
                mkstream=mkstream,
            )
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    def ensure_consumer_groups(
        self,
        streams: Iterable[StreamName],
        group_name: str,
        *,
        start_id: str = "0",
        mkstream: bool = True,
    ) -> None:
        for stream in streams:
            self.ensure_consumer_group(stream, group_name, start_id=start_id, mkstream=mkstream)

    def read_group(
        self,
        group_name: str,
        consumer_name: str,
        streams: dict[StreamName, str],
        *,
        count: int = 10,
        block_ms: int = 1_000,
        noack: bool = False,
    ) -> list[StreamEventRecord]:
        client = self.require_client()
        typed_streams = {validate_stream_name(stream): offset for stream, offset in streams.items()}
        result = client.xreadgroup(
            groupname=group_name,
            consumername=consumer_name,
            streams=typed_streams,
            count=count,
            block=block_ms,
            noack=noack,
        )
        return self._decode_read_result(result)

    def acknowledge(self, stream: StreamName, group_name: str, event_id: str) -> int:
        client = self.require_client()
        return int(client.xack(validate_stream_name(stream), group_name, event_id))

    def ping(self) -> bool:
        client = self.require_client()
        return bool(client.ping())

    def require_client(self) -> Any:
        if self.client is None:
            raise RuntimeError(
                "redis-py is not available. Install the project dependencies to use Redis Streams."
            )
        return self.client

    def connection_info(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "db": self.db,
            "stream_maxlen": self.stream_maxlen,
            "supported_streams": list(ALL_STREAMS),
        }

    def _decode_read_result(self, result: Iterable[Any]) -> list[StreamEventRecord]:
        decoded: list[StreamEventRecord] = []
        for stream, messages in result:
            typed_stream = validate_stream_name(str(stream))
            for redis_id, fields in messages:
                event = AgentEvent.from_dict(fields)
                decoded.append(StreamEventRecord(stream=typed_stream, event_id=str(redis_id), event=event))
        return decoded
