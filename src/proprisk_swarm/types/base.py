"""Base model definitions and shared configuration for PropRisk Swarm types."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field


def generate_uuid() -> str:
    """Generate a standard UUID4 hex string."""
    return uuid.uuid4().hex


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class BaseEntity(BaseModel):
    """Base Pydantic entity with immutable identity and timestamp tracking."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    id: str = Field(default_factory=generate_uuid, description="Unique primary identifier")
    created_at: datetime = Field(
        default_factory=utc_now, description="Entity creation timestamp in UTC"
    )
    updated_at: datetime = Field(
        default_factory=utc_now, description="Entity last updated timestamp in UTC"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary extensible metadata"
    )

    def touch(self) -> None:
        """Update the updated_at timestamp to current UTC time."""
        self.updated_at = utc_now()
