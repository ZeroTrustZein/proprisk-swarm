"""Event bus subsystem for asynchronous multi-agent coordination."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict

from proprisk_swarm.protocols import EventBusProtocol
from proprisk_swarm.types.events import EventPriority, EventType, SwarmEvent


class EventBus(EventBusProtocol):
    """In-memory topic-based event bus with filtering and audit history."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = defaultdict(list)
        self._history: List[SwarmEvent] = []

    def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Register handler for specific event type or '*' for all events."""
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Unregister previously registered handler."""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Publish event payload to subscribers matching event_type and wildcard '*'."""
        deal_id = payload.get("deal_id", "global")
        source_role = payload.get("source_role", "system")
        event = SwarmEvent(
            event_type=event_type,
            deal_id=deal_id,
            source_role=source_role,
            payload=payload,
            priority=payload.get("priority", EventPriority.NORMAL),
        )
        self._history.append(event)

        # Dispatch to specific subscribers
        handlers = list(self._subscribers.get(event_type, []))
        # Dispatch to wildcard subscribers
        handlers.extend(self._subscribers.get("*", []))

        for handler in handlers:
            handler(payload)

    def publish_event(self, event: SwarmEvent) -> None:
        """Publish SwarmEvent object directly."""
        self._history.append(event)
        evt_type = str(event.event_type)
        payload = event.model_dump()

        handlers = list(self._subscribers.get(evt_type, []))
        handlers.extend(self._subscribers.get("*", []))

        for handler in handlers:
            handler(payload)

    def get_history(
        self, deal_id: Optional[str] = None, event_type: Optional[str] = None
    ) -> List[SwarmEvent]:
        """Query event audit trail filtered by deal_id and/or event_type."""
        results = self._history
        if deal_id is not None:
            results = [e for e in results if e.deal_id == deal_id]
        if event_type is not None:
            results = [e for e in results if str(e.event_type) == event_type]
        return results

    def clear(self) -> None:
        """Clear all subscribers and history."""
        self._subscribers.clear()
        self._history.clear()
