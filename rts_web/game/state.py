"""Authoritative game state used by the RTS web experience."""

from __future__ import annotations

import math
import uuid
from collections import deque
from dataclasses import asdict
from typing import Deque, Dict, Iterable, List, Optional, Tuple

from .constants import (
    BASE_ATTACK_COOLDOWN,
    BASE_ATTACK_DAMAGE,
    BASE_ATTACK_RANGE,
    BASE_HP,
    BASE_POSITIONS,
    CREDITS_PER_TICK,
    MAP_HEIGHT,
    MAP_WIDTH,
    MAX_CREDITS,
    MAX_PLAYERS,
    PLAYER_COLORS,
    STARTING_CREDITS,
    TICK_SECONDS,
    UNIT_COLLISION_RADIUS,
    UNIT_STATS,
    Vec2,
    clamp,
)
from .models import Action, GameSnapshot, PlayerState, StructureState, UnitState


class GameState:
    """Server-authoritative state for a single RTS match."""

    def __init__(self) -> None:
        self.tick: int = 0
        self.players: Dict[str, PlayerState] = {}
        self.structures: Dict[str, StructureState] = {}
        self.units: Dict[str, UnitState] = {}
        self._actions: Deque[Action] = deque()
        self._color_cycle = iter(PLAYER_COLORS)
        self._spawn_cycle = iter(BASE_POSITIONS)
        self.match_over: bool = False
        self.winner: Optional[str] = None

    # ------------------------------------------------------------------
    # Player management
    # ------------------------------------------------------------------
    def add_player(self, name: str) -> Optional[PlayerState]:
        """Register a new commander in the match."""

        if len(self.players) >= min(MAX_PLAYERS, len(BASE_POSITIONS)):
            return None

        player_id = str(uuid.uuid4())
        color = next(self._color_cycle, PLAYER_COLORS[len(self.players) % len(PLAYER_COLORS)])
        spawn = next(self._spawn_cycle, BASE_POSITIONS[len(self.players) % len(BASE_POSITIONS)])
        player = PlayerState(
            id=player_id,
            name=name,
            color=color,
            credits=STARTING_CREDITS,
            income_per_tick=CREDITS_PER_TICK,
            rally_point=spawn,
        )
        self.players[player_id] = player
        base_id = str(uuid.uuid4())
        base = StructureState(id=base_id, owner_id=player_id, position=spawn, hp=float(BASE_HP))
        self.structures[base_id] = base
        return player

    def remove_player(self, player_id: str) -> None:
        """Remove a player from the match and clean up their entities."""

        player = self.players.get(player_id)
        if not player:
            return
        player.is_active = False
        player.defeat_tick = self.tick
        for unit_id in [u_id for u_id, u in self.units.items() if u.owner_id == player_id]:
            del self.units[unit_id]
        for structure_id in [s_id for s_id, s in self.structures.items() if s.owner_id == player_id]:
            del self.structures[structure_id]

    # ------------------------------------------------------------------
    # Action handling
    # ------------------------------------------------------------------
    def queue_action(self, action: Action) -> None:
        """Add a player request to the processing queue."""

        self._actions.append(action)

    def _consume_actions(self) -> Iterable[Action]:
        while self._actions:
            yield self._actions.popleft()

    # ------------------------------------------------------------------
    # Simulation loop
    # ------------------------------------------------------------------
    def tick_once(self) -> List[Dict[str, object]]:
        """Advance the simulation by a single tick."""

        if self.match_over:
            return []

        events: List[Dict[str, object]] = []
        self.tick += 1

        for action in self._consume_actions():
            handler = getattr(self, f"_handle_{action.type}", None)
            if handler:
                handler(action, events)

        self._apply_income()
        self._update_units(events)
        self._update_structures(events)
        self._check_victory(events)
        return events

    def _apply_income(self) -> None:
        for player in self.players.values():
            if not player.is_active:
                continue
            player.credits = min(MAX_CREDITS, player.credits + player.income_per_tick)

    def _update_units(self, events: List[Dict[str, object]]) -> None:
        delta = TICK_SECONDS
        removals: List[str] = []
        for unit in self.units.values():
            stats = UNIT_STATS[unit.unit_type]
            if unit.target_position:
                unit.position = self._step_toward(unit.position, unit.target_position, stats["speed"] * delta)
                if self._distance(unit.position, unit.target_position) <= 0.2:
                    unit.target_position = None
            if unit.attack_cooldown > 0.0:
                unit.attack_cooldown = max(0.0, unit.attack_cooldown - delta)

            target, is_structure = self._find_target(unit)
            if target and unit.attack_cooldown <= 0.0:
                self._deal_damage(unit, target, stats["damage"], events, is_structure)
                unit.attack_cooldown = stats["cooldown"]

            if unit.hp <= 0:
                removals.append(unit.id)
                events.append({"type": "unit_destroyed", "unit_id": unit.id})

        for unit_id in removals:
            self.units.pop(unit_id, None)

    def _update_structures(self, events: List[Dict[str, object]]) -> None:
        delta = TICK_SECONDS
        removals: List[str] = []
        for structure in self.structures.values():
            if structure.attack_cooldown > 0.0:
                structure.attack_cooldown = max(0.0, structure.attack_cooldown - delta)
            player = self.players.get(structure.owner_id)
            if not player or not player.is_active:
                continue
            target, _ = self._find_structure_target(structure)
            if target and structure.attack_cooldown <= 0.0:
                self._deal_damage_structure(structure, target, events)
                structure.attack_cooldown = BASE_ATTACK_COOLDOWN
            if structure.hp <= 0:
                removals.append(structure.id)
                events.append({"type": "structure_destroyed", "structure_id": structure.id})

        for structure_id in removals:
            structure = self.structures.pop(structure_id, None)
            if structure:
                owner = self.players.get(structure.owner_id)
                if owner:
                    owner.is_active = False
                    owner.defeat_tick = self.tick

    def _check_victory(self, events: List[Dict[str, object]]) -> None:
        active_players = [p for p in self.players.values() if p.is_active]
        if len(self.players) < 2:
            return
        if len(active_players) == 1 and not self.match_over:
            self.match_over = True
            self.winner = active_players[0].id
            events.append({"type": "match_over", "winner": self.winner})

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------
    def _handle_spawn_unit(self, action: Action, events: List[Dict[str, object]]) -> None:
        payload = action.payload
        unit_type = str(payload.get("unit_type", "")).lower()
        player = self.players.get(action.player_id)
        if unit_type not in UNIT_STATS or not player or not player.is_active:
            return
        cost = int(UNIT_STATS[unit_type]["cost"])
        if player.credits < cost:
            return
        player.credits -= cost
        spawn_position = self._spawn_position_for_player(player)
        unit = UnitState(
            id=str(uuid.uuid4()),
            owner_id=player.id,
            unit_type=unit_type,
            position=spawn_position,
            hp=float(UNIT_STATS[unit_type]["hp"]),
            target_position=player.rally_point,
        )
        self.units[unit.id] = unit
        events.append({"type": "unit_spawned", "unit": self._serialize_unit(unit)})

    def _handle_command_move(self, action: Action, events: List[Dict[str, object]]) -> None:
        payload = action.payload
        unit_ids = payload.get("unit_ids")
        target = payload.get("target")
        if not isinstance(unit_ids, list) or not isinstance(target, dict):
            return
        target_vec = self._validate_position(target)
        if not target_vec:
            return
        for unit_id in unit_ids:
            unit = self.units.get(unit_id)
            if unit and unit.owner_id == action.player_id:
                unit.target_position = target_vec
        events.append({"type": "command_ack", "unit_ids": unit_ids, "target": asdict(target_vec)})

    def _handle_set_rally(self, action: Action, events: List[Dict[str, object]]) -> None:
        payload = action.payload
        target = payload.get("target")
        player = self.players.get(action.player_id)
        if not isinstance(target, dict) or not player:
            return
        target_vec = self._validate_position(target)
        if not target_vec:
            return
        player.rally_point = target_vec
        events.append({"type": "rally_updated", "player_id": player.id, "target": asdict(target_vec)})

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def _spawn_position_for_player(self, player: PlayerState) -> Vec2:
        position = player.rally_point or self._find_structure_position(player.id)
        if position:
            return position
        return Vec2(MAP_WIDTH / 2.0, MAP_HEIGHT / 2.0)

    def _find_structure_position(self, owner_id: str) -> Optional[Vec2]:
        for structure in self.structures.values():
            if structure.owner_id == owner_id:
                return structure.position
        return None

    def _find_target(self, unit: UnitState) -> Tuple[Optional[UnitState | StructureState], bool]:
        closest: Optional[UnitState | StructureState] = None
        closest_distance = math.inf
        stats = UNIT_STATS[unit.unit_type]
        for enemy in self.units.values():
            if enemy.owner_id == unit.owner_id:
                continue
            distance = self._distance(unit.position, enemy.position)
            if distance < stats["range"] and distance < closest_distance:
                closest = enemy
                closest_distance = distance
        for structure in self.structures.values():
            if structure.owner_id == unit.owner_id:
                continue
            distance = self._distance(unit.position, structure.position)
            if distance < stats["range"] and distance < closest_distance:
                closest = structure
                closest_distance = distance
        return closest, isinstance(closest, StructureState)

    def _find_structure_target(self, structure: StructureState) -> Tuple[Optional[UnitState | StructureState], bool]:
        closest: Optional[UnitState | StructureState] = None
        closest_distance = math.inf
        for unit in self.units.values():
            if unit.owner_id == structure.owner_id:
                continue
            distance = self._distance(structure.position, unit.position)
            if distance < BASE_ATTACK_RANGE and distance < closest_distance:
                closest = unit
                closest_distance = distance
        for enemy_structure in self.structures.values():
            if enemy_structure.owner_id == structure.owner_id:
                continue
            distance = self._distance(structure.position, enemy_structure.position)
            if distance < BASE_ATTACK_RANGE and distance < closest_distance:
                closest = enemy_structure
                closest_distance = distance
        return closest, isinstance(closest, StructureState)

    def _deal_damage(
        self,
        unit: UnitState,
        target: UnitState | StructureState,
        damage: float,
        events: List[Dict[str, object]],
        target_is_structure: bool,
    ) -> None:
        target.hp -= damage
        events.append(
            {
                "type": "attack",
                "attacker": unit.id,
                "target": getattr(target, "id", None),
                "remaining_hp": target.hp,
                "structure": target_is_structure,
            }
        )

    def _deal_damage_structure(
        self,
        structure: StructureState,
        target: UnitState | StructureState,
        events: List[Dict[str, object]],
    ) -> None:
        target.hp -= BASE_ATTACK_DAMAGE
        events.append(
            {
                "type": "structure_attack",
                "attacker": structure.id,
                "target": getattr(target, "id", None),
                "remaining_hp": target.hp,
            }
        )

    def _step_toward(self, current: Vec2, target: Vec2, distance: float) -> Vec2:
        dx = target.x - current.x
        dy = target.y - current.y
        length = math.hypot(dx, dy)
        if length == 0:
            return current
        ratio = min(1.0, distance / length)
        new_x = clamp(current.x + dx * ratio, UNIT_COLLISION_RADIUS, MAP_WIDTH - UNIT_COLLISION_RADIUS)
        new_y = clamp(current.y + dy * ratio, UNIT_COLLISION_RADIUS, MAP_HEIGHT - UNIT_COLLISION_RADIUS)
        return Vec2(new_x, new_y)

    def _validate_position(self, payload: Dict[str, object]) -> Optional[Vec2]:
        try:
            x = float(payload["x"])
            y = float(payload["y"])
        except (KeyError, TypeError, ValueError):
            return None
        if 0 <= x <= MAP_WIDTH and 0 <= y <= MAP_HEIGHT:
            return Vec2(x, y)
        return None

    def _distance(self, a: Vec2, b: Vec2) -> float:
        return math.hypot(a.x - b.x, a.y - b.y)

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------
    def snapshot(self) -> GameSnapshot:
        snapshot = GameSnapshot(tick=self.tick, match_over=self.match_over, winner=self.winner)
        snapshot.players = [self._serialize_player(player) for player in self.players.values()]
        snapshot.structures = [self._serialize_structure(structure) for structure in self.structures.values()]
        snapshot.units = [self._serialize_unit(unit) for unit in self.units.values()]
        return snapshot

    def _serialize_player(self, player: PlayerState) -> Dict[str, object]:
        data = {
            "id": player.id,
            "name": player.name,
            "color": player.color,
            "credits": player.credits,
            "income_per_tick": player.income_per_tick,
            "is_active": player.is_active,
            "rally_point": asdict(player.rally_point) if player.rally_point else None,
            "defeat_tick": player.defeat_tick,
        }
        return data

    def _serialize_structure(self, structure: StructureState) -> Dict[str, object]:
        return {
            "id": structure.id,
            "owner_id": structure.owner_id,
            "position": asdict(structure.position),
            "hp": structure.hp,
        }

    def _serialize_unit(self, unit: UnitState) -> Dict[str, object]:
        return {
            "id": unit.id,
            "owner_id": unit.owner_id,
            "unit_type": unit.unit_type,
            "position": asdict(unit.position),
            "hp": unit.hp,
            "target_position": asdict(unit.target_position) if unit.target_position else None,
        }


__all__ = ["GameState"]
