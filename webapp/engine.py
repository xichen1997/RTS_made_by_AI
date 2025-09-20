"""Real time simulation engine for Nova Frontier.

The engine keeps the authoritative state of a match, runs a fixed tick loop and
processes player commands.  It is intentionally deterministic to simplify
synchronisation across WebSocket clients.
"""
from __future__ import annotations

import asyncio
import contextlib
import math
import random
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Iterable, List, Optional

from . import config
from .models import (
    Base,
    Command,
    GameState,
    MatchView,
    Player,
    PlayerColor,
    ResourceNode,
    Unit,
    UnitType,
    Vector2,
)


@dataclass(slots=True)
class CommandQueue:
    """Thread-safe queue used to stage player commands until the next tick."""

    _queue: Deque[Command] = field(default_factory=deque)

    def push(self, command: Command) -> None:
        self._queue.append(command)

    def drain(self) -> List[Command]:
        commands = list(self._queue)
        self._queue.clear()
        return commands


class GameEngine:
    """Simulation core responsible for executing one RTS match."""

    def __init__(self, seed: Optional[int] = None, players: Optional[Dict[str, Player]] = None) -> None:
        self.random = random.Random(seed)
        self.command_queue = CommandQueue()
        self.state = self._initial_state(players)
        self._tick_interval = 1.0 / config.TICK_RATE
        self._tick_task: Optional[asyncio.Task[None]] = None
        self._subscribers: List[asyncio.Queue[MatchView]] = []

    # ------------------------------------------------------------------
    # State initialization
    # ------------------------------------------------------------------
    def _initial_state(self, provided_players: Optional[Dict[str, Player]]) -> GameState:
        if provided_players is None:
            colors = list(PlayerColor)
            self.random.shuffle(colors)
            provided_players = {
                "p1": Player(id="p1", name="Player 1", color=colors[0]),
                "p2": Player(id="p2", name="Player 2", color=colors[1]),
            }
        players = {pid: player for pid, player in provided_players.items()}
        self._spawn_bases(players)
        resource_nodes = self._spawn_resources()
        return GameState(players=players, resource_nodes=resource_nodes)

    def _spawn_bases(self, players: Dict[str, Player]) -> None:
        placements = [(8, config.MAP_HEIGHT // 2), (config.MAP_WIDTH - 8, config.MAP_HEIGHT // 2)]
        for idx, (player, position) in enumerate(zip(players.values(), placements)):
            player.base = Base(id=idx + 1, owner_id=player.id, position=position)
            # Every player starts with one harvester.
            unit_id = self._generate_unit_id(player)
            player.units[unit_id] = Unit(
                id=unit_id,
                owner_id=player.id,
                unit_type=UnitType.HARVESTER,
                position=(position[0] + self.random.uniform(-2, 2), position[1] + self.random.uniform(-2, 2)),
                health=config.HARVESTER_MAX_HEALTH,
            )

    def _spawn_resources(self) -> Dict[int, ResourceNode]:
        nodes: Dict[int, ResourceNode] = {}
        margin = 10
        for idx in range(config.RESOURCE_NODE_COUNT):
            position = (
                self.random.randint(margin, config.MAP_WIDTH - margin),
                self.random.randint(margin, config.MAP_HEIGHT - margin),
            )
            nodes[idx] = ResourceNode(id=idx, position=position)
        return nodes

    # ------------------------------------------------------------------
    # Simulation loop
    # ------------------------------------------------------------------
    async def start(self) -> None:
        if self._tick_task is None:
            self._tick_task = asyncio.create_task(self._run_loop())

    async def wait_until_finished(self) -> None:
        if self._tick_task is not None:
            await self._tick_task

    async def stop(self) -> None:
        if self._tick_task:
            self._tick_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._tick_task
            self._tick_task = None

    async def _run_loop(self) -> None:
        last_tick = time.perf_counter()
        while self.state.winner is None:
            now = time.perf_counter()
            dt = now - last_tick
            if dt < self._tick_interval:
                await asyncio.sleep(self._tick_interval - dt)
                continue
            last_tick = now
            events = self._tick(dt)
            await self._notify_subscribers(events)

    def _tick(self, dt: float) -> List[Dict[str, object]]:
        self.state.time_elapsed += dt
        commands = self.command_queue.drain()
        events: List[Dict[str, object]] = []
        for command in commands:
            events.extend(self._execute_command(command))
        self._update_units(dt, events)
        self._update_bases(dt, events)
        self._determine_winner(events)
        return events

    async def _notify_subscribers(self, events: List[Dict[str, object]]) -> None:
        view = MatchView(state=self.state, events=events)
        for queue in list(self._subscribers):
            if queue.full():
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
            await queue.put(view)

    def subscribe(self) -> asyncio.Queue[MatchView]:
        """Create a queue that will receive every state update."""

        queue: asyncio.Queue[MatchView] = asyncio.Queue(maxsize=1)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[MatchView]) -> None:
        with contextlib.suppress(ValueError):
            self._subscribers.remove(queue)

    # ------------------------------------------------------------------
    # Command handling
    # ------------------------------------------------------------------
    def queue_command(self, command: Command) -> None:
        self.command_queue.push(command)

    def _execute_command(self, command: Command) -> List[Dict[str, object]]:
        handler_name = f"_handle_{command.action}"
        handler = getattr(self, handler_name, None)
        if handler is None:
            return [{"type": "error", "message": f"Unknown command {command.action}"}]
        return handler(command)

    def _handle_move(self, command: Command) -> List[Dict[str, object]]:
        unit_id = int(command.payload.get("unit"))
        position = command.payload.get("position")
        player = self.state.players.get(command.player_id)
        if not player or unit_id not in player.units or not position:
            return []
        player.units[unit_id].target_position = tuple(position)
        player.units[unit_id].target_unit = None
        return [{"type": "order", "unit": unit_id, "position": position}]

    def _handle_attack(self, command: Command) -> List[Dict[str, object]]:
        unit_id = int(command.payload.get("unit"))
        target_id = int(command.payload.get("target"))
        player = self.state.players.get(command.player_id)
        if not player or unit_id not in player.units:
            return []
        player.units[unit_id].target_unit = target_id
        return [{"type": "order", "unit": unit_id, "target": target_id}]

    def _handle_build(self, command: Command) -> List[Dict[str, object]]:
        unit_type = command.payload.get("type")
        player = self.state.players.get(command.player_id)
        if player is None:
            return []
        if unit_type == UnitType.INFANTRY.value and player.credits >= config.UNIT_COST:
            player.credits -= config.UNIT_COST
            unit_id = self._generate_unit_id(player)
            player.units[unit_id] = Unit(
                id=unit_id,
                owner_id=player.id,
                unit_type=UnitType.INFANTRY,
                position=self._spawn_near_base(player),
                health=config.UNIT_MAX_HEALTH,
                progress=-config.UNIT_BUILD_TIME,
            )
            return [{"type": "build", "unit": unit_id, "unit_type": UnitType.INFANTRY.value}]
        if unit_type == UnitType.HARVESTER.value and player.credits >= config.HARVESTER_COST:
            player.credits -= config.HARVESTER_COST
            unit_id = self._generate_unit_id(player)
            player.units[unit_id] = Unit(
                id=unit_id,
                owner_id=player.id,
                unit_type=UnitType.HARVESTER,
                position=self._spawn_near_base(player),
                health=config.HARVESTER_MAX_HEALTH,
                progress=-config.HARVESTER_BUILD_TIME,
            )
            return [{"type": "build", "unit": unit_id, "unit_type": UnitType.HARVESTER.value}]
        return []

    def _generate_unit_id(self, player: Player) -> int:
        return max(player.units.keys(), default=0) + 1

    def _spawn_near_base(self, player: Player) -> Vector2:
        if not player.base:
            return (config.MAP_WIDTH / 2, config.MAP_HEIGHT / 2)
        px, py = player.base.position
        return (px + self.random.uniform(-2, 2), py + self.random.uniform(-2, 2))

    # ------------------------------------------------------------------
    # Unit and base updates
    # ------------------------------------------------------------------
    def _update_units(self, dt: float, events: List[Dict[str, object]]) -> None:
        for player in self.state.players.values():
            for unit in list(player.units.values()):
                if unit.progress < 0:
                    unit.progress += dt
                    if unit.progress < 0:
                        continue
                if unit.unit_type == UnitType.HARVESTER:
                    self._update_harvester(unit, player, dt, events)
                else:
                    self._update_infantry(unit, player, dt, events)

    def _update_harvester(self, unit: Unit, player: Player, dt: float, events: List[Dict[str, object]]) -> None:
        if unit.target_position is None:
            node = self._find_closest_resource(unit.position)
            if node:
                unit.target_position = node.position
        self._move_towards(unit, dt, config.HARVESTER_SPEED)
        if unit.target_position and self._distance(unit.position, unit.target_position) < 0.5:
            node = self._resource_at(unit.target_position)
            if node and node.value_remaining > 0:
                gathered = node.take(config.HARVEST_RATE)
                unit.carrying += gathered
                unit.progress += dt
                if unit.progress >= config.HARVEST_TIME:
                    unit.progress = 0.0
                    unit.target_position = player.base.position if player.base else None
            elif player.base and self._distance(unit.position, player.base.position) < 1.5:
                if unit.carrying:
                    player.credits = min(config.CREDIT_CAP, player.credits + unit.carrying)
                    events.append({"type": "deposit", "player": player.id, "amount": unit.carrying})
                    unit.carrying = 0
                unit.target_position = None

    def _update_infantry(self, unit: Unit, player: Player, dt: float, events: List[Dict[str, object]]) -> None:
        target_unit = self._find_unit_by_id(unit.target_unit)
        if target_unit:
            unit.target_position = target_unit.position
        self._move_towards(unit, dt, config.UNIT_SPEED)
        attack_performed = False
        if target_unit and self._distance(unit.position, target_unit.position) <= config.UNIT_ATTACK_RANGE:
            if unit.cooldown <= 0:
                damage = config.UNIT_ATTACK_DAMAGE
                self._apply_damage(target_unit, damage, events, source=unit.id)
                unit.cooldown = config.UNIT_ATTACK_COOLDOWN
                attack_performed = True
        enemy_base = self._closest_enemy_base(player.id, unit.position)
        if enemy_base and self._distance(unit.position, enemy_base.position) <= config.UNIT_ATTACK_RANGE:
            if unit.cooldown <= 0 and not attack_performed:
                self._apply_base_damage(enemy_base, config.UNIT_ATTACK_DAMAGE, events, source=unit.id)
                unit.cooldown = config.UNIT_ATTACK_COOLDOWN
        unit.cooldown = max(0.0, unit.cooldown - dt)

    def _update_bases(self, dt: float, events: List[Dict[str, object]]) -> None:
        for player in self.state.players.values():
            base = player.base
            if not base:
                continue
            base.cooldown = max(0.0, base.cooldown - dt)
            enemy_units = [unit for other in self.state.players.values() if other.id != player.id for unit in other.units.values()]
            target = self._closest_enemy_unit(base.position, enemy_units)
            if target and self._distance(base.position, target.position) <= config.BASE_ATTACK_RANGE:
                if base.cooldown <= 0:
                    self._apply_damage(target, config.BASE_ATTACK_DAMAGE, events, source=base.id)
                    base.cooldown = config.BASE_ATTACK_COOLDOWN

    # ------------------------------------------------------------------
    # Helper routines
    # ------------------------------------------------------------------
    def _move_towards(self, unit: Unit, dt: float, speed: float) -> None:
        if unit.target_position is None:
            return
        ux, uy = unit.position
        tx, ty = unit.target_position
        dx, dy = tx - ux, ty - uy
        distance = math.hypot(dx, dy)
        if distance < 0.01:
            unit.position = (tx, ty)
            return
        step = min(distance, speed * dt)
        unit.position = (ux + dx / distance * step, uy + dy / distance * step)

    def _distance(self, a: Vector2, b: Vector2) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def _find_closest_resource(self, position: Vector2) -> Optional[ResourceNode]:
        return min(self.state.resource_nodes.values(), key=lambda node: self._distance(position, node.position), default=None)

    def _resource_at(self, position: Vector2) -> Optional[ResourceNode]:
        for node in self.state.resource_nodes.values():
            if self._distance(node.position, position) < 1.0:
                return node
        return None

    def _apply_damage(self, unit: Unit, damage: int, events: List[Dict[str, object]], source: int) -> None:
        unit.health -= damage
        events.append({"type": "damage", "target": unit.id, "amount": damage, "source": source})
        if unit.health <= 0:
            owner = self.state.players[unit.owner_id]
            del owner.units[unit.id]
            events.append({"type": "destroyed", "unit": unit.id})

    def _closest_enemy_unit(self, position: Vector2, units: Iterable[Unit]) -> Optional[Unit]:
        best: Optional[Unit] = None
        best_distance = float("inf")
        for unit in units:
            distance = self._distance(position, unit.position)
            if distance < best_distance:
                best = unit
                best_distance = distance
        return best

    def _closest_enemy_base(self, player_id: str, position: Vector2) -> Optional[Base]:
        best: Optional[Base] = None
        best_distance = float("inf")
        for other in self.state.players.values():
            if other.id == player_id or other.base is None:
                continue
            distance = self._distance(position, other.base.position)
            if distance < best_distance:
                best = other.base
                best_distance = distance
        return best

    def _apply_base_damage(self, base: Base, damage: int, events: List[Dict[str, object]], source: int) -> None:
        base.health -= damage
        events.append({"type": "base_damage", "target": base.owner_id, "amount": damage, "source": source})
        if base.health <= 0:
            owner = self.state.players[base.owner_id]
            owner.base = None
            events.append({"type": "base_destroyed", "player": owner.id})

    def _find_unit_by_id(self, unit_id: Optional[int]) -> Optional[Unit]:
        if unit_id is None:
            return None
        for player in self.state.players.values():
            if unit_id in player.units:
                return player.units[unit_id]
        return None

    def _determine_winner(self, events: List[Dict[str, object]]) -> None:
        alive_players = [player for player in self.state.players.values() if player.base and player.base.health > 0]
        if len(alive_players) == 1:
            self.state.winner = alive_players[0].id
            events.append({"type": "victory", "player": self.state.winner})


__all__ = ["GameEngine", "CommandQueue"]
