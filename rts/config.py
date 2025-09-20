"""Configuration objects for match and server runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class MatchConfig:
    """Static configuration describing how a match is created.

    Attributes
    ----------
    min_players:
        Minimum number of human players required for the session to
        start.  The matchmaking service keeps players in the lobby until
        this threshold is reached.
    max_players:
        Maximum number of human players supported in the arena.  The
        matchmaking service never allocates more players than this
        number to a single match.
    ai_mob_count:
        Tuple describing the inclusive range of AI mobs to spawn once
        the session is initialised.  The count is randomised for each
        match to keep the PvE pressure unpredictable.
    match_duration_seconds:
        Duration of the match once players drop into the arena.  The
        authoritative server is responsible for ending the match once
        this timer reaches zero.
    extraction_window_seconds:
        How long the extraction phase lasts once the first extraction is
        triggered.  Players that fail to evacuate before the window
        closes are considered lost even if they are still alive.
    hazard_count:
        Number of dynamic hazards to spawn.  Hazards rotate positions to
        encourage map movement and create emergent objectives.
    tick_rate:
        Number of authoritative server updates per second.
    """

    min_players: int = 20
    max_players: int = 40
    ai_mob_count: Tuple[int, int] = (100, 300)
    match_duration_seconds: int = 15 * 60
    extraction_window_seconds: int = 90
    hazard_count: int = 5
    tick_rate: int = 10

    def validate(self) -> None:
        if self.min_players <= 0 or self.max_players <= 0:
            raise ValueError("Player counts must be positive")
        if self.min_players > self.max_players:
            raise ValueError("min_players cannot exceed max_players")
        if self.ai_mob_count[0] <= 0 or self.ai_mob_count[1] < self.ai_mob_count[0]:
            raise ValueError("Invalid AI mob range")
        if self.match_duration_seconds <= 0:
            raise ValueError("Match duration must be positive")
        if self.tick_rate <= 0:
            raise ValueError("Tick rate must be positive")
