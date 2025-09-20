from __future__ import annotations

import uuid

from rts.arena import ArenaMap
from rts.config import MatchConfig
from rts.entities import Loadout, PlayerProfile, PlayerState
from rts.session import GameSession, MatchPhase


def _make_player(name: str) -> PlayerState:
    profile = PlayerProfile(account_id=uuid.uuid4(), display_name=name)
    loadout = Loadout("Assault", "Rifle", "Pistol", "Grenade")
    return PlayerState(profile=profile, loadout=loadout)


def test_session_runs_to_completion():
    config = MatchConfig(min_players=4, max_players=8, match_duration_seconds=1)
    arena = ArenaMap.generate(hazard_count=2)
    session = GameSession(match_id=uuid.uuid4(), config=config, arena=arena)
    for idx in range(4):
        session.add_player(_make_player(f"Player-{idx}"))
    session.start()
    for _ in range(2_000):
        session.update()
        if session.phase is MatchPhase.COMPLETE:
            break
    assert session.phase is MatchPhase.COMPLETE
    assert all(player.status.name in {"EXTRACTED", "ELIMINATED"} for player in session.players.values())


def test_session_logs_events():
    config = MatchConfig(min_players=2, max_players=4, match_duration_seconds=1)
    arena = ArenaMap.generate(hazard_count=1)
    session = GameSession(match_id=uuid.uuid4(), config=config, arena=arena)
    for idx in range(2):
        session.add_player(_make_player(f"Player-{idx}"))
    session.start()
    for _ in range(1_000):
        session.update()
        if session.phase is MatchPhase.COMPLETE:
            break
    assert session.combat_log
    assert any("extraction" in entry.message.lower() or "debrief" in entry.message.lower() for entry in session.combat_log)
