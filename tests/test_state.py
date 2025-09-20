"""Regression tests for the ChronoFront game state."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rts_web.game.models import Action
from rts_web.game.state import GameState


def test_player_can_spawn_units() -> None:
    game = GameState()
    player = game.add_player("Test")
    assert player is not None
    action = Action(player_id=player.id, type="spawn_unit", payload={"unit_type": "grunt"})
    game.queue_action(action)
    events = game.tick_once()
    assert any(event["type"] == "unit_spawned" for event in events)
    assert game.players[player.id].credits < 600
    assert game.units


def test_units_move_toward_target() -> None:
    game = GameState()
    player = game.add_player("Mover")
    assert player is not None
    action = Action(player_id=player.id, type="spawn_unit", payload={"unit_type": "grunt"})
    game.queue_action(action)
    game.tick_once()
    unit_id = next(iter(game.units))
    move_action = Action(
        player_id=player.id,
        type="command_move",
        payload={"unit_ids": [unit_id], "target": {"x": 20, "y": 20}},
    )
    game.queue_action(move_action)
    game.tick_once()
    unit = game.units[unit_id]
    assert unit.target_position is not None
    assert unit.position != player.rally_point


def test_victory_when_one_player_remains() -> None:
    game = GameState()
    alpha = game.add_player("Alpha")
    beta = game.add_player("Beta")
    assert alpha and beta
    # Remove Beta's structures and mark them defeated.
    for structure_id, structure in list(game.structures.items()):
        if structure.owner_id == beta.id:
            structure.hp = 0
    events = game.tick_once()
    assert any(event.get("type") == "match_over" for event in events)
    assert game.match_over is True
    assert game.winner == alpha.id
