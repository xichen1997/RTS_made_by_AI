"""Core package for the session-based RTS prototype.

This package exposes the high level services that a client would
integrate with to run a PvPvE arena match.  The focus is on providing a
server authoritative simulation loop that can be unit tested without
any graphical dependencies.
"""

from .config import MatchConfig
from .entities import PlayerProfile, Loadout
from .game_server import GameServer

__all__ = [
    "GameServer",
    "Loadout",
    "MatchConfig",
    "PlayerProfile",
]
