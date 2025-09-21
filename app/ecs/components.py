"""Component definitions used by the lightweight ECS implementation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.models import Vector2


@dataclass
class Position:
    """Stores the world-space position for an entity."""

    value: Vector2


@dataclass
class Movement:
    """Encapsulates movement capabilities of an entity."""

    speed: float


@dataclass
class Orders:
    """Represents the current high-level order assigned to an entity."""

    state: str = "idle"
    target_position: Optional[Vector2] = None
    target_entity_id: Optional[str] = None


@dataclass
class CombatStats:
    """Basic combat information for units capable of attacking."""

    damage: int
    attack_range: float
    cooldown: float
    current_cooldown: float = 0.0


@dataclass
class UnitLink:
    """Back-reference to the simulation's traditional unit identifier."""

    unit_id: str
