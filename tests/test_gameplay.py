"""Unit tests covering the core RTS simulation loop."""
from app import config
from app.game import RTSGame
from app.models import Vector2


def run_updates(game: RTSGame, seconds: float, step: float = 0.5) -> None:
    iterations = int(seconds / step)
    for _ in range(iterations):
        game.update(step)


def test_player_join_spawns_base() -> None:
    game = RTSGame("room")
    player = game.add_player("p1", "Alpha")
    assert player.credits == config.STARTING_CREDITS
    assert player.units
    assert player.buildings
    assert all(unit.owner_id == "p1" for unit in player.units.values())


def test_production_queue_creates_units() -> None:
    game = RTSGame("room")
    player = game.add_player("p1", "Builder")
    training_structure = next(
        building
        for building in player.buildings.values()
        if "conscript" in building.buildable_units
    )
    game.enqueue_command(
        "p1",
        {
            "action": "build_unit",
            "building_id": training_structure.id,
            "unit_type": "conscript",
        },
    )
    run_updates(game, seconds=6.0)
    assert any(unit.kind == "conscript" for unit in player.units.values())
    assert player.credits < config.STARTING_CREDITS


def test_combat_units_destroy_targets() -> None:
    game = RTSGame("room")
    p1 = game.add_player("p1", "Alpha")
    p2 = game.add_player("p2", "Bravo")
    attacker = next(unit for unit in p1.units.values() if unit.attack_damage > 0)
    defender = next(unit for unit in p2.units.values() if unit.attack_damage > 0)
    attacker.position = Vector2(20, 20)
    defender.position = Vector2(21, 20)
    game.enqueue_command(
        "p1", {"action": "attack", "unit_ids": [attacker.id], "target_id": defender.id}
    )
    run_updates(game, seconds=10.0)
    assert defender.id not in game.units


def test_harvest_generates_credits() -> None:
    game = RTSGame("room")
    player = game.add_player("p1", "Miner")
    harvester = next(unit for unit in player.units.values() if unit.role == "harvester")
    resource = next(iter(game.resource_nodes.values()))
    harvester.position = Vector2(*resource.position.to_tuple())
    starting = player.credits
    game.enqueue_command(
        "p1",
        {"action": "harvest", "unit_ids": [harvester.id], "resource_id": resource.id},
    )
    run_updates(game, seconds=5.0)
    assert player.credits > starting
