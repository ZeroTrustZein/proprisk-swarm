"""Base agent implementation conforming to AgentProtocol."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid

from proprisk_swarm.protocols import AgentProtocol
from proprisk_swarm.types.agents import AgentRole, AgentState


class BaseAgent(AgentProtocol):
    """Abstract base worker for diligence swarm agents."""

    def __init__(
        self,
        role: AgentRole,
        agent_id: Optional[str] = None,
        supported_tasks: Optional[List[str]] = None,
    ) -> None:
        self._role = role
        self._agent_id = agent_id or f"{role.value}-{uuid.uuid4().hex[:6]}"
        self._supported_tasks = supported_tasks or []
        self._state = AgentState.IDLE

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def role(self) -> AgentRole:
        return self._role

    @property
    def role_name(self) -> str:
        return self._role.value

    @property
    def state(self) -> AgentState:
        return self._state

    def can_handle(self, task_type: str) -> bool:
        """Check whether this agent supports the specified task type."""
        norm_task = task_type.lower().replace(".", "_").replace("-", "_")
        return norm_task in [t.lower().replace(".", "_").replace("-", "_") for t in self._supported_tasks]

    def execute_task(self, task_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute assigned diligence task."""
        self._state = AgentState.ACTIVE
        try:
            result = self._process(task_payload)
            self._state = AgentState.COMPLETED
            return result
        except Exception as exc:
            self._state = AgentState.ERROR
            return {
                "status": "error",
                "agent_id": self._agent_id,
                "role": self.role_name,
                "error": str(exc),
            }

    def _process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Subclasses override this with domain diligence logic."""
        raise NotImplementedError("Subclasses must implement _process.")
