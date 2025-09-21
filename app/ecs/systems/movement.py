"""Movement related ECS system."""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.ecs.components import Movement, Orders, Position, UnitLink

if TYPE_CHECKING:  # pragma: no cover - imported for type checkers only
    from app.ecs.world import World
    from app.game import RTSGame


class MovementSystem:
    """Applies movement orders to units each simulation tick."""

    def __init__(self, game: "RTSGame") -> None:
        self._game = game

    def update(self, world: "World", dt: float) -> None:
        for _, (position, movement, orders, link) in world.get_components(
            Position, Movement, Orders, UnitLink
        ):
            unit = self._game.units.get(link.unit_id)
            if not unit or not unit.is_alive():
                continue
            if orders.state != "moving" or not orders.target_position:
                continue

            position.value.move_towards(orders.target_position, movement.speed * dt)
            # ``position.value`` is the same Vector2 instance referenced by the unit.
            if position.value.distance_to(orders.target_position) <= 0.5:
                unit.reset_orders()
                orders.state = unit.state
                orders.target_position = None
                orders.target_entity_id = None
