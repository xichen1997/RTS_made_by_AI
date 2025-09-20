"""Authoritative game session."""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple

from .arena import ArenaMap
from .config import MatchConfig
from .entities import AIMob, MobBehavior, PlayerState, PlayerStatus, random_inventory_item


class MatchPhase(Enum):
    LOBBY = "lobby"
    DEPLOYMENT = "deployment"
    COMBAT = "combat"
    EXTRACTION = "extraction"
    COMPLETE = "complete"


@dataclass
class CombatLogEntry:
    tick: int
    message: str


@dataclass
class GameSession:
    match_id: uuid.UUID
    config: MatchConfig
    arena: ArenaMap
    phase: MatchPhase = MatchPhase.LOBBY
    ticks_elapsed: int = 0
    players: Dict[uuid.UUID, PlayerState] = field(default_factory=dict)
    mobs: Dict[uuid.UUID, AIMob] = field(default_factory=dict)
    combat_log: List[CombatLogEntry] = field(default_factory=list)
    _extraction_timer: int = 0

    def add_player(self, player_state: PlayerState) -> None:
        if player_state.profile.account_id in self.players:
            raise ValueError("Player already in session")
        self.players[player_state.profile.account_id] = player_state
        player_state.status = PlayerStatus.DEPLOYING
        self._log(f"{player_state.profile.display_name} is preparing to deploy.")

    def start(self) -> None:
        if self.phase is not MatchPhase.LOBBY:
            raise RuntimeError("Session already started")
        if not self.players:
            raise RuntimeError("Cannot start an empty session")
        self.phase = MatchPhase.DEPLOYMENT
        self._spawn_mobs()
        self._log("Dropships en route. Prepare for deployment.")

    def _spawn_mobs(self) -> None:
        count = random.randint(*self.config.ai_mob_count)
        for _ in range(count):
            mob = AIMob(
                mob_id=uuid.uuid4(),
                species=random.choice(["Grunt", "Ravager", "Siege Drone"]),
                health=random.randint(50, 120),
                damage=random.randint(5, 20),
                position=(random.randint(0, self.arena.width), random.randint(0, self.arena.height)),
                behavior=random.choice(list(MobBehavior)),
            )
            self.mobs[mob.mob_id] = mob
        self._log(f"Spawned {len(self.mobs)} AI combatants.")

    def update(self) -> None:
        if self.phase is MatchPhase.COMPLETE:
            return
        self.ticks_elapsed += 1
        if self.phase is MatchPhase.DEPLOYMENT:
            self._handle_deployment()
        elif self.phase is MatchPhase.COMBAT:
            self._handle_combat()
        elif self.phase is MatchPhase.EXTRACTION:
            self._handle_extraction()

    def _handle_deployment(self) -> None:
        for player in self.players.values():
            player.status = PlayerStatus.ACTIVE
        self.phase = MatchPhase.COMBAT
        self._log("All strike teams deployed. Combat phase live.")

    def _handle_combat(self) -> None:
        if self.ticks_elapsed % (self.config.tick_rate * 30) == 0:
            self.arena.rotate_hazards()
            self._log("Hazards have shifted across the battlefield!")
        for mob in list(self.mobs.values()):
            mob.tick()
            if random.random() < 0.01:
                mob.apply_damage(999)
                self._log(f"{mob.species} neutralised during skirmish.")
                del self.mobs[mob.mob_id]
        for player in self.players.values():
            if player.status is not PlayerStatus.ACTIVE:
                continue
            if random.random() < 0.02 and player.inventory.can_loot():
                player.inventory.add(random_inventory_item())
            if random.random() < 0.01:
                player.status = PlayerStatus.DOWNED
                self._log(f"{player.profile.display_name} has been downed!")
            if player.status is PlayerStatus.DOWNED and random.random() < 0.5:
                player.mark_eliminated()
                self._log(f"{player.profile.display_name} has been eliminated.")
        if self._active_player_count() <= max(1, self.config.min_players // 4):
            self._begin_extraction()
        if self.ticks_elapsed >= self.config.match_duration_seconds * self.config.tick_rate:
            self._begin_extraction(force=True)

    def _handle_extraction(self) -> None:
        self._extraction_timer += 1
        for player in self.players.values():
            if player.status is PlayerStatus.ACTIVE and random.random() < 0.1:
                player.mark_extracted()
                self._log(f"{player.profile.display_name} has extracted with loot!")
            elif player.status is PlayerStatus.ACTIVE and self._extraction_timer > self.config.extraction_window_seconds * self.config.tick_rate:
                player.mark_eliminated()
                self._log(f"{player.profile.display_name} failed to extract in time.")
        if self._all_players_resolved():
            self.phase = MatchPhase.COMPLETE
            self._log("Match complete. Debrief in progress.")

    def _begin_extraction(self, force: bool = False) -> None:
        if self.phase is MatchPhase.EXTRACTION:
            return
        self.phase = MatchPhase.EXTRACTION
        self._extraction_timer = 0
        if force:
            self._log("Mission timer expired. Immediate extraction authorised!")
        else:
            self._log("Extraction window opened. Reach the dropships!")

    def _active_player_count(self) -> int:
        return sum(1 for player in self.players.values() if player.status is PlayerStatus.ACTIVE)

    def _all_players_resolved(self) -> bool:
        return all(
            player.status in {PlayerStatus.EXTRACTED, PlayerStatus.ELIMINATED}
            for player in self.players.values()
        )

    def _log(self, message: str) -> None:
        self.combat_log.append(CombatLogEntry(tick=self.ticks_elapsed, message=message))
