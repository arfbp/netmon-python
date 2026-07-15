"""Unit tests for websocket/event_forwarder.py."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock

from app.events.bus import EventBus
from app.websocket.connection_manager import ConnectionManager
from app.websocket.event_forwarder import (
    _event_payload,
    _event_type_name,
    register_event_forwarding,
)


@dataclass(frozen=True, slots=True)
class PingResultEvent:
    target: str
    latency_ms: float


@dataclass(frozen=True, slots=True)
class GatewayDownEvent:
    reason: str


class TestEventTypeName:
    def test_strips_event_suffix_and_converts_to_snake_case(self) -> None:
        assert (
            _event_type_name(PingResultEvent(target="1.1.1.1", latency_ms=1.0)) == "ping_result"
        )

    def test_multi_word_event_name(self) -> None:
        assert _event_type_name(GatewayDownEvent(reason="timeout")) == "gateway_down"

    def test_name_without_event_suffix_is_left_as_is(self) -> None:
        class Foo:
            pass

        assert _event_type_name(Foo()) == "foo"


class TestEventPayload:
    def test_dataclass_event_serializes_via_asdict(self) -> None:
        event = PingResultEvent(target="1.1.1.1", latency_ms=12.5)
        assert _event_payload(event) == {"target": "1.1.1.1", "latency_ms": 12.5}

    def test_non_dataclass_event_falls_back_to_vars(self) -> None:
        class PlainObject:
            def __init__(self) -> None:
                self.foo = "bar"

        assert _event_payload(PlainObject()) == {"foo": "bar"}


class TestRegisterEventForwarding:
    async def test_published_event_is_broadcast_to_connected_clients(self) -> None:
        bus = EventBus()
        manager = ConnectionManager()
        register_event_forwarding(bus, manager)

        ws = AsyncMock()
        await manager.connect(ws)

        await bus.publish(PingResultEvent(target="8.8.8.8", latency_ms=9.1))

        ws.send_json.assert_awaited_once()
        sent = ws.send_json.call_args.args[0]
        assert sent["type"] == "ping_result"
        assert sent["payload"] == {"target": "8.8.8.8", "latency_ms": 9.1}

    async def test_event_published_with_no_connected_clients_does_not_raise(self) -> None:
        bus = EventBus()
        manager = ConnectionManager()
        register_event_forwarding(bus, manager)

        await bus.publish(PingResultEvent(target="8.8.8.8", latency_ms=9.1))
