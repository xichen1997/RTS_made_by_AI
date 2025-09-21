"""Combat related ECS system."""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.ecs.components import CombatStats, Orders, UnitLink

if TYPE_CHECKING:  # pragma: no cover - imported for type checkers only
    from app.ecs.world import World
    from app.game import RTSGame


class CombatSystem:
    """Handles combat decision making for units each tick."""

    def __init__(self, game: "RTSGame") -> None:
        self._game = game

    def update(self, world: "World", dt: float) -> None:
        for _, (combat, orders, link) in world.get_components(CombatStats, Orders, UnitLink):
            unit = self._game.units.get(link.unit_id)
            if not unit or not unit.is_alive():
                continue
            if unit.attack_damage <= 0:
                continue

            target = None
            if orders.state == "attack" and orders.target_entity_id:
                target = self._game.units.get(orders.target_entity_id) or self._game.buildings.get(
                    orders.target_entity_id
                )
                if not target or not target.is_alive():
                    unit.reset_orders()
                    orders.state = unit.state
                    orders.target_entity_id = None
                    orders.target_position = None
                    continue
            else:
                target = self._game._find_closest_enemy(unit)
                if not target:
                    continue
                unit.state = "attack"
                unit.target_entity_id = target.id
                unit.target_position = target.position.copy()
                orders.state = unit.state
                orders.target_entity_id = unit.target_entity_id
                orders.target_position = unit.target_position.copy()

            self._game._attack_target(unit, target, dt)
            combat.current_cooldown = unit.current_cooldown
            if unit.state != orders.state or unit.target_entity_id != orders.target_entity_id:
                orders.state = unit.state
                orders.target_entity_id = unit.target_entity_id
                orders.target_position = unit.target_position.copy() if unit.target_position else None
