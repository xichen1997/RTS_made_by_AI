"""Regression tests for the web-facing RTS engine."""
from __future__ import annotations

import math

import pytest

from webapp import config
from webapp.engine import GameEngine
from webapp.models import Command, Player, PlayerColor, UnitType


@pytest.fixture()
def engine() -> GameEngine:
    players = {
        "p1": Player(id="p1", name="Tester 1", color=PlayerColor.BLUE),
        "p2": Player(id="p2", name="Tester 2", color=PlayerColor.RED),
    }
    return GameEngine(seed=42, players=players)


def test_building_units_consumes_credits(engine: GameEngine) -> None:
    player = engine.state.players["p1"]
    starting = player.credits
    engine.queue_command(
        Command(player_id="p1", action="build", payload={"type": UnitType.INFANTRY.value}, issued_at=0.0)
    )
    engine._tick(1.0)
    assert player.credits == starting - config.UNIT_COST
    # Advance time to finish production.
    for _ in range(int(math.ceil(config.UNIT_BUILD_TIME)) + 1):
        engine._tick(1.0)
    assert any(unit.unit_type == UnitType.INFANTRY for unit in player.units.values())


def test_harvesters_generate_income(engine: GameEngine) -> None:
    player = engine.state.players["p1"]
    harvester = next(unit for unit in player.units.values() if unit.unit_type == UnitType.HARVESTER)
    original_credits = player.credits
    # Simulate a few harvest cycles.
    for _ in range(40):
        engine._tick(0.5)
    assert player.credits > original_credits
    assert harvester.carrying >= 0
