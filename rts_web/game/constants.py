"""Constants and configuration values for the RTS game simulation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Vec2:
    """Immutable helper for expressing 2D positions."""

    x: float
    y: float


TICK_SECONDS: float = 0.25
MAP_WIDTH: int = 48
MAP_HEIGHT: int = 32
MAX_PLAYERS: int = 4
STARTING_CREDITS: int = 600
CREDITS_PER_TICK: int = 30
MAX_CREDITS: int = 4000
BASE_HP: int = 1500
BASE_ATTACK_RANGE: float = 4.0
BASE_ATTACK_DAMAGE: int = 40
BASE_ATTACK_COOLDOWN: float = 2.5

BASE_POSITIONS: tuple[Vec2, ...] = (
    Vec2(4.0, MAP_HEIGHT / 2.0),
    Vec2(MAP_WIDTH - 4.0, MAP_HEIGHT / 2.0),
    Vec2(MAP_WIDTH / 2.0, 4.0),
    Vec2(MAP_WIDTH / 2.0, MAP_HEIGHT - 4.0),
)

PLAYER_COLORS: tuple[str, ...] = ("#ff5e5b", "#6c5ce7", "#55efc4", "#ffeaa7")

UNIT_STATS: dict[str, dict[str, float]] = {
    "grunt": {
        "hp": 120,
        "speed": 3.2,  # tiles per second
        "damage": 18,
        "range": 2.5,
        "cooldown": 1.2,
        "cost": 120,
    },
    "rocketeer": {
        "hp": 90,
        "speed": 3.8,
        "damage": 26,
        "range": 3.5,
        "cooldown": 1.6,
        "cost": 180,
    },
    "tank": {
        "hp": 320,
        "speed": 2.4,
        "damage": 42,
        "range": 3.8,
        "cooldown": 2.2,
        "cost": 320,
    },
}

STRUCTURE_RADIUS: float = 2.2
UNIT_COLLISION_RADIUS: float = 0.6


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp *value* to the inclusive range [minimum, maximum]."""

    return max(minimum, min(value, maximum))
