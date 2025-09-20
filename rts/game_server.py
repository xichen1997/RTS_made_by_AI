"""Authoritative server orchestrating multiple matches."""

from __future__ import annotations

import itertools
import random
import uuid
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from .arena import ArenaMap
from .config import MatchConfig
from .entities import Loadout, PlayerProfile, PlayerState, PlayerStatus
from .matchmaking import MatchmakingService
from .progression import InventoryService, ProgressionService
from .session import GameSession, MatchPhase


@dataclass
class PlayerRegistration:
    profile: PlayerProfile
    loadout: Loadout


class GameServer:
    """High level facade representing the backend cluster."""

    def __init__(self, config: Optional[MatchConfig] = None):
        self.config = config or MatchConfig()
        self.matchmaking = MatchmakingService(self.config)
        self.progression = ProgressionService()
        self.inventory = InventoryService()
        self.active_sessions: Dict[uuid.UUID, GameSession] = {}
        self._pending_rewards: Dict[uuid.UUID, Tuple] = {}

    def enqueue_player(self, profile: PlayerProfile, loadout: Loadout) -> int:
        return self.matchmaking.enqueue(profile, loadout)

    def tick(self) -> None:
        match_players = self.matchmaking.pop_match()
        if match_players:
            session = self._create_session(match_players)
            self.active_sessions[session.match_id] = session
            session.start()
        finished_sessions = []
        for session in self.active_sessions.values():
            session.update()
            if session.phase is MatchPhase.COMPLETE:
                finished_sessions.append(session.match_id)
        for match_id in finished_sessions:
            session = self.active_sessions.pop(match_id)
            self._resolve_session(session)

    def _create_session(self, match_players) -> GameSession:
        arena = ArenaMap.generate(self.config.hazard_count)
        session = GameSession(match_id=uuid.uuid4(), config=self.config, arena=arena)
        for entry in match_players:
            player_state = PlayerState(profile=entry.profile, loadout=entry.loadout)
            session.add_player(player_state)
        return session

    def _resolve_session(self, session: GameSession) -> None:
        for player in session.players.values():
            survived = player.status is PlayerStatus.EXTRACTED
            reward = self.progression.grant_match_rewards(player, survived, kills=random.randint(0, 5))
            stash = self.inventory.return_loot(player)
            self._pending_rewards[player.profile.account_id] = (reward, stash)

    def collect_rewards(self, account_id: uuid.UUID):
        return self._pending_rewards.pop(account_id, None)

    def run_until_idle(self, ticks: int = 10_000) -> None:
        for _ in range(ticks):
            self.tick()
            if not self.active_sessions and len(self.matchmaking) == 0:
                break
