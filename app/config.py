"""Configuration constants for the RTS web application."""

MAP_WIDTH = 96
MAP_HEIGHT = 64
TICK_RATE = 10  # ticks per second
STATE_BROADCAST_RATE = 10  # snapshots per second
MAX_PLAYERS_PER_ROOM = 4

# Economic tuning
STARTING_CREDITS = 1000
HARVEST_RATE_PER_SECOND = 20
HARVEST_NODE_CAPACITY = 5000

# Unit statistics keyed by unit type.
UNIT_STATS = {
    "harvester": {
        "max_hp": 120,
        "speed": 6.0,
        "attack_damage": 0,
        "attack_range": 0,
        "attack_cooldown": 1.0,
        "cost": 300,
        "build_time": 8.0,
    },
    "soldier": {
        "max_hp": 80,
        "speed": 10.0,
        "attack_damage": 8,
        "attack_range": 6.0,
        "attack_cooldown": 0.8,
        "cost": 150,
        "build_time": 4.0,
    },
    "tank": {
        "max_hp": 300,
        "speed": 7.0,
        "attack_damage": 25,
        "attack_range": 8.0,
        "attack_cooldown": 1.6,
        "cost": 650,
        "build_time": 12.0,
    },
}

# Building statistics keyed by building type.
BUILDING_STATS = {
    "hq": {
        "max_hp": 3000,
        "buildable_units": ["harvester", "soldier"],
    },
    "factory": {
        "max_hp": 2000,
        "buildable_units": ["soldier", "tank"],
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
