"""Tests for EventBus subsystem."""

from __future__ import annotations

from proprisk_swarm.events.bus import EventBus
from proprisk_swarm.protocols import EventBusProtocol
from proprisk_swarm.types.events import EventPriority, SwarmEvent


def test_event_bus_protocol_conformance():
    """Verify EventBus conforms to EventBusProtocol."""
    bus = EventBus()
    assert isinstance(bus, EventBusProtocol)


def test_event_bus_pub_sub():
    """Verify topic-based publish and subscribe."""
    bus = EventBus()
    received: list[dict] = []

    def handler(payload: dict) -> None:
        received.append(payload)

    bus.subscribe("deal.created", handler)
    bus.publish("deal.created", {"deal_id": "D-101", "name": "Sunset Plaza"})

    assert len(received) == 1
    assert received[0]["deal_id"] == "D-101"

    # Unsubscribe
    bus.unsubscribe("deal.created", handler)
    bus.publish("deal.created", {"deal_id": "D-102"})
    assert len(received) == 1


def test_event_bus_wildcard_subscription():
    """Verify '*' subscriber receives all events."""
    bus = EventBus()
    received_topics: list[str] = []

    bus.subscribe("*", lambda p: received_topics.append(p.get("deal_id", "")))
    bus.publish("topic.a", {"deal_id": "D-1"})
    bus.publish("topic.b", {"deal_id": "D-2"})

    assert received_topics == ["D-1", "D-2"]


def test_event_bus_publish_event_object():
    """Verify publishing SwarmEvent directly."""
    bus = EventBus()
    received: list[dict] = []

    bus.subscribe("audit.completed", lambda p: received.append(p))
    event = SwarmEvent(
        event_type="audit.completed",
        deal_id="D-200",
        source_role="auditor",
        payload={"score": 95},
        priority=EventPriority.HIGH,
    )
    bus.publish_event(event)

    assert len(received) == 1
    assert received[0]["deal_id"] == "D-200"


def test_event_bus_history_and_filter():
    """Verify audit history retrieval and filtering."""
    bus = EventBus()
    bus.publish("event.one", {"deal_id": "D-1"})
    bus.publish("event.two", {"deal_id": "D-1"})
    bus.publish("event.one", {"deal_id": "D-2"})

    assert len(bus.get_history()) == 3
    assert len(bus.get_history(deal_id="D-1")) == 2
    assert len(bus.get_history(event_type="event.one")) == 2
    assert len(bus.get_history(deal_id="D-2", event_type="event.one")) == 1

    bus.clear()
    assert len(bus.get_history()) == 0
