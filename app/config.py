"""Configuration constants for the RTS web application."""

MAP_WIDTH = 96
MAP_HEIGHT = 64
TICK_RATE = 10  # ticks per second
STATE_BROADCAST_RATE = 10  # snapshots per second
MAX_PLAYERS_PER_ROOM = 4

# Economic tuning
STARTING_CREDITS = 2500
HARVEST_RATE_PER_SECOND = 20
HARVEST_NODE_CAPACITY = 5000

# Unit statistics keyed by unit type.
UNIT_STATS = {
    "ore_miner": {
        "max_hp": 420,
        "speed": 5.2,
        "attack_damage": 0,
        "attack_range": 0,
        "attack_cooldown": 1.0,
        "cost": 1200,
        "build_time": 12.0,
        "role": "harvester",
    },
    "conscript": {
        "max_hp": 85,
        "speed": 9.0,
        "attack_damage": 7,
        "attack_range": 5.0,
        "attack_cooldown": 0.7,
        "cost": 100,
        "build_time": 3.5,
        "role": "combat",
    },
    "gi": {
        "max_hp": 110,
        "speed": 7.5,
        "attack_damage": 10,
        "attack_range": 6.5,
        "attack_cooldown": 0.85,
        "cost": 200,
        "build_time": 4.5,
        "role": "combat",
    },
    "grizzly_tank": {
        "max_hp": 420,
        "speed": 8.0,
        "attack_damage": 24,
        "attack_range": 7.0,
        "attack_cooldown": 1.3,
        "cost": 700,
        "build_time": 9.0,
        "role": "combat",
    },
    "prism_tank": {
        "max_hp": 320,
        "speed": 6.5,
        "attack_damage": 45,
        "attack_range": 12.0,
        "attack_cooldown": 3.5,
        "cost": 1200,
        "build_time": 16.0,
        "role": "combat",
    },
    "mirage_tank": {
        "max_hp": 360,
        "speed": 7.0,
        "attack_damage": 32,
        "attack_range": 9.0,
        "attack_cooldown": 2.2,
        "cost": 1000,
        "build_time": 14.0,
        "role": "combat",
    },
}

# Building statistics keyed by building type.
BUILDING_STATS = {
    "construction_yard": {
        "max_hp": 3500,
        "buildable_units": ["ore_miner"],
    },
    "ore_refinery": {
        "max_hp": 2500,
        "buildable_units": ["ore_miner"],
    },
    "barracks": {
        "max_hp": 1800,
        "buildable_units": ["conscript", "gi"],
    },
    "war_factory": {
        "max_hp": 2600,
        "buildable_units": [
            "ore_miner",
            "grizzly_tank",
            "prism_tank",
            "mirage_tank",
        ],
    },
}

# Spawn positions arranged clockwise starting from bottom-left.
SPAWN_POSITIONS = [
    (10.0, 10.0),
    (MAP_WIDTH - 10.0, MAP_HEIGHT - 10.0),
    (10.0, MAP_HEIGHT - 10.0),
    (MAP_WIDTH - 10.0, 10.0),
]

RESOURCE_NODE_POSITIONS = [
    (MAP_WIDTH / 2, MAP_HEIGHT / 2),
    (MAP_WIDTH / 2 + 15, MAP_HEIGHT / 2 - 12),
    (MAP_WIDTH / 2 - 20, MAP_HEIGHT / 2 + 16),
    (MAP_WIDTH / 2 + 5, MAP_HEIGHT / 2 + 18),
]
