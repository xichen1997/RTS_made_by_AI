from __future__ import annotations

import uuid

from rts.config import MatchConfig
from rts.entities import Loadout, PlayerProfile
from rts.matchmaking import MatchmakingService


def test_matchmaking_forms_match_when_minimum_reached():
    config = MatchConfig(min_players=4, max_players=6)
    service = MatchmakingService(config)
    profiles = [
        PlayerProfile(account_id=uuid.uuid4(), display_name=f"Player-{i}")
        for i in range(4)
    ]
    loadout = Loadout("Assault", "Rifle", "Pistol", "Grenade")
    for profile in profiles:
        service.enqueue(profile, loadout)
    match = service.pop_match()
    assert match is not None
    assert len(match) == 4


def test_matchmaking_respects_max_player_cap():
    config = MatchConfig(min_players=2, max_players=3)
    service = MatchmakingService(config)
    profiles = [
        PlayerProfile(account_id=uuid.uuid4(), display_name=f"Player-{i}")
        for i in range(5)
    ]
    loadout = Loadout("Support", "Railgun", "Sidearm", "Turret")
    for profile in profiles:
        service.enqueue(profile, loadout)
    match = service.pop_match()
    assert match is not None
    assert len(match) == 3
    assert len(service) == 2
