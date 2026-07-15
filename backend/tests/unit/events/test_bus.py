"""Unit tests for app.events.bus.EventBus. Zero I/O — pure in-process
dispatch logic. Relies on pyproject.toml's asyncio_mode = "auto", so no
explicit pytest.mark.asyncio is needed on async test functions.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.events.bus import EventBus


@dataclass(frozen=True, slots=True)
class SampleEvent:
    value: str


@dataclass(frozen=True, slots=True)
class OtherEvent:
    value: str


class TestSubscribeAndPublish:
    async def test_subscriber_receives_matching_event_type(self) -> None:
        bus = EventBus()
        received: list[SampleEvent] = []

        async def handler(event: SampleEvent) -> None:
            received.append(event)

        bus.subscribe(SampleEvent, handler)
        await bus.publish(SampleEvent(value="hello"))

        assert received == [SampleEvent(value="hello")]

    async def test_subscriber_does_not_receive_other_event_types(self) -> None:
        bus = EventBus()
        received: list[object] = []

        async def handler(event: SampleEvent) -> None:
            received.append(event)

        bus.subscribe(SampleEvent, handler)
        await bus.publish(OtherEvent(value="ignored"))

        assert received == []

    async def test_multiple_subscribers_all_receive_the_event(self) -> None:
        bus = EventBus()
        received_a: list[SampleEvent] = []
        received_b: list[SampleEvent] = []

        async def handler_a(event: SampleEvent) -> None:
            received_a.append(event)

        async def handler_b(event: SampleEvent) -> None:
            received_b.append(event)

        bus.subscribe(SampleEvent, handler_a)
        bus.subscribe(SampleEvent, handler_b)
        await bus.publish(SampleEvent(value="x"))

        assert len(received_a) == 1
        assert len(received_b) == 1

    async def test_publish_with_no_subscribers_does_not_raise(self) -> None:
        bus = EventBus()
        await bus.publish(SampleEvent(value="nobody listening"))


class TestSubscribeAll:
    async def test_wildcard_subscriber_receives_every_event_type(self) -> None:
        bus = EventBus()
        received: list[object] = []

        async def handler(event: object) -> None:
            received.append(event)

        bus.subscribe_all(handler)
        await bus.publish(SampleEvent(value="a"))
        await bus.publish(OtherEvent(value="b"))

        assert len(received) == 2

    async def test_wildcard_and_specific_subscribers_both_fire(self) -> None:
        bus = EventBus()
        wildcard_received: list[object] = []
        specific_received: list[SampleEvent] = []

        async def wildcard_handler(event: object) -> None:
            wildcard_received.append(event)

        async def specific_handler(event: SampleEvent) -> None:
            specific_received.append(event)

        bus.subscribe_all(wildcard_handler)
        bus.subscribe(SampleEvent, specific_handler)
        await bus.publish(SampleEvent(value="a"))

        assert len(wildcard_received) == 1
        assert len(specific_received) == 1


class TestUnsubscribe:
    async def test_unsubscribed_handler_no_longer_receives_events(self) -> None:
        bus = EventBus()
        received: list[SampleEvent] = []

        async def handler(event: SampleEvent) -> None:
            received.append(event)

        bus.subscribe(SampleEvent, handler)
        bus.unsubscribe(SampleEvent, handler)
        await bus.publish(SampleEvent(value="x"))

        assert received == []

    async def test_unsubscribe_of_unregistered_handler_does_not_raise(self) -> None:
        bus = EventBus()

        async def handler(event: SampleEvent) -> None:
            pass

        bus.unsubscribe(SampleEvent, handler)


class TestSubscriberFailureIsolation:
    async def test_one_failing_subscriber_does_not_prevent_others(self) -> None:
        bus = EventBus()
        received: list[SampleEvent] = []

        async def failing_handler(event: SampleEvent) -> None:
            raise RuntimeError("boom")

        async def good_handler(event: SampleEvent) -> None:
            received.append(event)

        bus.subscribe(SampleEvent, failing_handler)
        bus.subscribe(SampleEvent, good_handler)

        await bus.publish(SampleEvent(value="x"))  # must not raise

        assert len(received) == 1
