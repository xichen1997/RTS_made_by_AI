"""Server-authoritative RTS game simulation."""
from __future__ import annotations

import itertools
import math
import uuid
from collections import deque
from typing import Deque, Dict, Iterable, List, Optional, Tuple

from . import config
from .models import (
    Building,
    Entity,
    GameSnapshot,
    PlayerState,
    ProductionTask,
    ResourceNode,
    Unit,
    Vector2,
)


PLAYER_COLORS = ["#3cb44b", "#0082c8", "#f58231", "#911eb4"]


class GameFullError(RuntimeError):
    """Raised when a room has already reached the player limit."""


class RTSGame:
    """Encapsulates the state of a single RTS match."""

    def __init__(self, room_id: str):
        self.room_id = room_id
        self.players: Dict[str, PlayerState] = {}
        self.units: Dict[str, Unit] = {}
        self.buildings: Dict[str, Building] = {}
        self.resource_nodes: Dict[str, ResourceNode] = {}
        self.tick: int = 0
        self.time_accumulator: float = 0.0
        self.events: Deque[str] = deque(maxlen=50)
        self.command_queue: Deque[Tuple[str, Dict]] = deque()
        self._spawn_resources()

    # ------------------------------------------------------------------
    # Lifecycle management
    # ------------------------------------------------------------------
    def add_player(self, player_id: str, name: str) -> PlayerState:
        """Register a player and spawn their starting base."""
        if len(self.players) >= config.MAX_PLAYERS_PER_ROOM:
            raise GameFullError("room is full")

        color = PLAYER_COLORS[len(self.players) % len(PLAYER_COLORS)]
        spawn = config.SPAWN_POSITIONS[len(self.players)]
        player = PlayerState(
            player_id=player_id,
            name=name,
            credits=config.STARTING_CREDITS,
            color=color,
        )
        self.players[player_id] = player
        self._spawn_starting_base(player, spawn)
        self.add_event(f"{name} established a base.")
        return player

    def remove_player(self, player_id: str) -> None:
        player = self.players.pop(player_id, None)
        if not player:
            return
        for unit_id in list(player.units):
            self.units.pop(unit_id, None)
        for building_id in list(player.buildings):
            self.buildings.pop(building_id, None)
        self.add_event(f"{player.name} has left the battlefield.")

    # ------------------------------------------------------------------
    # Command processing
    # ------------------------------------------------------------------
    def enqueue_command(self, player_id: str, command: Dict) -> None:
        """Add a command to be processed on the next tick."""
        self.command_queue.append((player_id, command))

    @staticmethod
    def _format_name(identifier: str) -> str:
        return identifier.replace("_", " ").title()

    def _process_commands(self) -> None:
        while self.command_queue:
            player_id, command = self.command_queue.popleft()
            player = self.players.get(player_id)
            if not player:
                continue
            action = command.get("action")
            if action == "move":
                self._handle_move(player, command)
            elif action == "attack":
                self._handle_attack(player, command)
            elif action == "harvest":
                self._handle_harvest(player, command)
            elif action == "build_unit":
                self._handle_build_unit(player, command)

    def _handle_move(self, player: PlayerState, command: Dict) -> None:
        destination = Vector2(**command["position"])
        for unit_id in command.get("unit_ids", []):
            unit = player.units.get(unit_id)
            if not unit or not unit.is_alive():
                continue
            unit.target_position = destination.copy()
            unit.target_entity_id = None
            unit.state = "moving"

    def _handle_attack(self, player: PlayerState, command: Dict) -> None:
        target_id = command.get("target_id")
        if target_id is None:
            return
        target = self.units.get(target_id) or self.buildings.get(target_id)
        if not target:
            return
        for unit_id in command.get("unit_ids", []):
            unit = player.units.get(unit_id)
            if not unit or not unit.is_alive():
                continue
            unit.target_entity_id = target_id
            unit.target_position = target.position.copy()
            unit.state = "attack"

    def _handle_harvest(self, player: PlayerState, command: Dict) -> None:
        node_id = command.get("resource_id")
        node = self.resource_nodes.get(node_id)
        if not node:
            return
        destination = node.position.copy()
        for unit_id in command.get("unit_ids", []):
            unit = player.units.get(unit_id)
            if not unit or not unit.is_alive() or unit.role != "harvester":
                continue
            unit.state = "harvest"
            unit.target_entity_id = node_id
            unit.target_position = destination

    def _handle_build_unit(self, player: PlayerState, command: Dict) -> None:
        building_id = command.get("building_id")
        unit_type = command.get("unit_type")
        building = player.buildings.get(building_id)
        if not building:
            return
        stats = config.UNIT_STATS.get(unit_type)
        if not stats:
            return
        if unit_type not in building.buildable_units:
            return
        if player.credits < stats["cost"]:
            return
        player.credits -= stats["cost"]
        building.production_queue.append(
            ProductionTask(unit_type=unit_type, remaining=stats["build_time"])
        )
        self.add_event(
            f"{player.name} queued a {self._format_name(unit_type)} at {self._format_name(building.kind)}"
        )

    # ------------------------------------------------------------------
    # Update loop
    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self.time_accumulator += dt
        self._process_commands()
        self._update_buildings(dt)
        self._update_units(dt)
        self.tick += 1

    def _update_buildings(self, dt: float) -> None:
        for building in list(self.buildings.values()):
            if not building.production_queue:
                continue
            task = building.production_queue[0]
            task.remaining -= dt
            if task.remaining > 0:
                continue
            building.production_queue.pop(0)
            owner = self.players.get(building.owner_id)
            if not owner:
                continue
            unit = self._spawn_unit(owner, task.unit_type, near=building.position)
            owner.units[unit.id] = unit
            self.units[unit.id] = unit
            self.add_event(
                f"{owner.name} produced a {self._format_name(task.unit_type)} at {self._format_name(building.kind)}"
            )

    def _update_units(self, dt: float) -> None:
        for unit in list(self.units.values()):
            if not unit.is_alive():
                owner = self.players.get(unit.owner_id)
                if owner:
                    owner.units.pop(unit.id, None)
                self.units.pop(unit.id, None)
                self.add_event(f"{self._format_name(unit.kind)} destroyed")
                continue

            if unit.state == "moving" and unit.target_position:
                unit.position.move_towards(unit.target_position, unit.speed * dt)
                if unit.position.distance_to(unit.target_position) <= 0.5:
                    unit.reset_orders()
            elif unit.state == "attack" and unit.target_entity_id:
                target = self.units.get(unit.target_entity_id) or self.buildings.get(
                    unit.target_entity_id
                )
                if not target or not target.is_alive():
                    unit.reset_orders()
                    continue
                self._attack_target(unit, target, dt)
            elif unit.state == "harvest" and unit.target_entity_id:
                node = self.resource_nodes.get(unit.target_entity_id)
                if not node:
                    unit.reset_orders()
                    continue
                self._harvest_node(unit, node, dt)
            else:
                # Opportunistic targeting: engage closest enemy in range.
                self._seek_and_attack(unit, dt)

    def _harvest_node(self, unit: Unit, node: ResourceNode, dt: float) -> None:
        destination = node.position
        unit.position.move_towards(destination, unit.speed * dt)
        if unit.position.distance_to(destination) > 1.2:
            return
        gathered = node.harvest(config.HARVEST_RATE_PER_SECOND * dt)
        if gathered <= 0:
            unit.reset_orders()
            self.add_event("A resource field has been depleted.")
            return
        owner = self.players.get(unit.owner_id)
        if owner:
            owner.credits += int(gathered)

    def _attack_target(self, unit: Unit, target: Entity, dt: float) -> None:
        if unit.attack_damage <= 0:
            unit.reset_orders()
            return
        distance = unit.position.distance_to(target.position)
        if distance > unit.attack_range:
            # Advance towards the target
            unit.position.move_towards(target.position, unit.speed * dt)
            return
        if unit.current_cooldown > 0:
            unit.current_cooldown -= dt
            return
        target.take_damage(unit.attack_damage)
        unit.current_cooldown = unit.attack_cooldown
        if not target.is_alive():
            if isinstance(target, Unit):
                target_owner = self.players.get(target.owner_id)
                if target_owner:
                    target_owner.units.pop(target.id, None)
                self.units.pop(target.id, None)
            elif isinstance(target, Building):
                target_owner = self.players.get(target.owner_id)
                if target_owner:
                    target_owner.buildings.pop(target.id, None)
                self.buildings.pop(target.id, None)
                owner_name = target_owner.name if target_owner else "an unknown commander"
                self.add_event(
                    f"{self._format_name(target.kind)} belonging to {owner_name} destroyed!"
                )
            unit.reset_orders()

    def _seek_and_attack(self, unit: Unit, dt: float) -> None:
        if unit.attack_damage <= 0:
            return
        enemy = self._find_closest_enemy(unit)
        if not enemy:
            return
        unit.state = "attack"
        unit.target_entity_id = enemy.id
        unit.target_position = enemy.position.copy()
        self._attack_target(unit, enemy, dt)

    def _find_closest_enemy(self, unit: Unit) -> Optional[Entity]:
        candidates: Iterable[Entity] = itertools.chain(
            (u for u in self.units.values() if u.owner_id != unit.owner_id),
            (b for b in self.buildings.values() if b.owner_id != unit.owner_id),
        )
        closest: Optional[Entity] = None
        closest_dist = math.inf
        for entity in candidates:
            distance = unit.position.distance_to(entity.position)
            if distance < closest_dist:
                closest = entity
                closest_dist = distance
        if closest and closest_dist <= unit.attack_range + 5.0:
            return closest
        return None

    # ------------------------------------------------------------------
    # Snapshotting
    # ------------------------------------------------------------------
    def snapshot(self) -> GameSnapshot:
        units_data = [
            {
                "id": unit.id,
                "owner": unit.owner_id,
                "type": unit.kind,
                "position": unit.position.to_tuple(),
                "hp": unit.hp,
                "max_hp": unit.max_hp,
                "state": unit.state,
            }
            for unit in self.units.values()
        ]
        buildings_data = [
            {
                "id": building.id,
                "owner": building.owner_id,
                "type": building.kind,
                "position": building.position.to_tuple(),
                "hp": building.hp,
                "max_hp": building.max_hp,
                "queue": [task.unit_type for task in building.production_queue],
            }
            for building in self.buildings.values()
        ]
        players_data = {
            player_id: {
                "name": player.name,
                "credits": player.credits,
                "color": player.color,
            }
            for player_id, player in self.players.items()
        }
        resources_data = [
            {
                "id": node.id,
                "position": node.position.to_tuple(),
                "remaining": node.remaining,
            }
            for node in self.resource_nodes.values()
        ]
        snapshot = GameSnapshot(
            tick=self.tick,
            map_size=(config.MAP_WIDTH, config.MAP_HEIGHT),
            players=players_data,
            units=units_data,
            buildings=buildings_data,
            resources=resources_data,
            events=list(self.events),
        )
        self.events.clear()
        return snapshot

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _spawn_resources(self) -> None:
        for index, position in enumerate(config.RESOURCE_NODE_POSITIONS):
            node_id = f"resource_{index}"
            self.resource_nodes[node_id] = ResourceNode(
                id=node_id,
                position=Vector2(*position),
                remaining=config.HARVEST_NODE_CAPACITY,
            )

    def _spawn_starting_base(self, player: PlayerState, spawn: Tuple[float, float]) -> None:
        base_center = Vector2(spawn[0], spawn[1])
        layout = [
            ("construction_yard", base_center.copy()),
            ("power_plant", Vector2(base_center.x + 22, base_center.y - 18)),
            ("ore_refinery", Vector2(base_center.x - 28, base_center.y + 14)),
            ("barracks", Vector2(base_center.x + 24, base_center.y + 18)),
            ("war_factory", Vector2(base_center.x - 26, base_center.y - 16)),
            ("airforce_command", Vector2(base_center.x, base_center.y + 28)),
            ("prism_tower", Vector2(base_center.x + 30, base_center.y + 2)),
        ]

        buildings_by_kind: Dict[str, Building] = {}
        for kind, position in layout:
            building = self._spawn_building(player, kind, position)
            player.buildings[building.id] = building
            self.buildings[building.id] = building
            buildings_by_kind[kind] = building

        initial_units = [
            ("conscript", buildings_by_kind.get("barracks")),
            ("conscript", buildings_by_kind.get("barracks")),
            ("gi", buildings_by_kind.get("barracks")),
            ("grizzly_tank", buildings_by_kind.get("war_factory")),
            ("ifv", buildings_by_kind.get("war_factory")),
            ("ore_miner", buildings_by_kind.get("ore_refinery")),
        ]

        for unit_type, anchor in initial_units:
            anchor_position = anchor.position if anchor else base_center
            unit = self._spawn_unit(player, unit_type, near=anchor_position)
            player.units[unit.id] = unit
            self.units[unit.id] = unit

    def _spawn_building(
        self, player: PlayerState, kind: str, position: Vector2
    ) -> Building:
        stats = config.BUILDING_STATS[kind]
        building = Building(
            id=f"building_{uuid.uuid4().hex[:8]}",
            owner_id=player.player_id,
            kind=kind,
            position=position,
            max_hp=stats["max_hp"],
            hp=stats["max_hp"],
            buildable_units=list(stats["buildable_units"]),
        )
        return building

    def _spawn_unit(
        self, player: PlayerState, unit_type: str, near: Vector2
    ) -> Unit:
        stats = config.UNIT_STATS[unit_type]
        jitter = Vector2(near.x + 1.5 - (3.0 * (uuid.uuid4().int % 100) / 100.0), near.y)
        unit = Unit(
            id=f"unit_{uuid.uuid4().hex[:8]}",
            owner_id=player.player_id,
            kind=unit_type,
            position=jitter,
            max_hp=stats["max_hp"],
            hp=stats["max_hp"],
            speed=stats["speed"],
            attack_damage=stats["attack_damage"],
            attack_range=stats["attack_range"],
            attack_cooldown=stats["attack_cooldown"],
            role=stats.get("role", "combat"),
        )
        return unit

    def add_event(self, message: str) -> None:
        self.events.append(message)


__all__ = ["RTSGame", "GameFullError"]
