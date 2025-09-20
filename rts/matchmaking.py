"""Matchmaking and lobby services."""

from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from .config import MatchConfig
from .entities import Loadout, PlayerProfile


@dataclass(order=True)
class _QueuedPlayer:
    sort_key: int
    ticket_id: int = field(compare=False)
    profile: PlayerProfile = field(compare=False)
    loadout: Loadout = field(compare=False)


class MatchmakingService:
    """Simple skill-based matchmaking queue.

    Players are stored in a heap prioritised by their skill rating and
    ticket age.  The queue keeps matchmaking fair while allowing the
    service to scale horizontally; multiple matchmaking workers can pull
    from the queue using a distributed lock system (not modelled here).
    """

    def __init__(self, config: MatchConfig):
        config.validate()
        self._config = config
        self._queue: List[_QueuedPlayer] = []
        self._ticket_counter = itertools.count()

    def enqueue(self, profile: PlayerProfile, loadout: Loadout) -> int:
        ticket_id = next(self._ticket_counter)
        entry = _QueuedPlayer(-profile.skill_rating, ticket_id, profile, loadout)
        heapq.heappush(self._queue, entry)
        return ticket_id

    def cancel(self, ticket_id: int) -> bool:
        for i, entry in enumerate(self._queue):
            if entry.ticket_id == ticket_id:
                self._queue.pop(i)
                heapq.heapify(self._queue)
                return True
        return False

    def pop_match(self) -> Optional[List[_QueuedPlayer]]:
        if len(self._queue) < self._config.min_players:
            return None
        slots = min(self._config.max_players, len(self._queue))
        return [heapq.heappop(self._queue) for _ in range(slots)]

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._queue)
