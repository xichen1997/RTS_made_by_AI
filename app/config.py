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

# Unit statistics keyed by unit type. These values roughly mirror their Red Alert 2
# inspirations to give each unit a battlefield role.
UNIT_STATS = {
    "ore_miner": {
        "max_hp": 420,
        "speed": 5.0,
        "attack_damage": 0,
        "attack_range": 0,
        "attack_cooldown": 1.0,
        "cost": 1400,
        "build_time": 18.0,
        "role": "harvester",
    },
    "conscript": {
        "max_hp": 65,
        "speed": 9.0,
        "attack_damage": 6,
        "attack_range": 7.0,
        "attack_cooldown": 0.9,
        "cost": 100,
        "build_time": 3.0,
        "role": "combat",
    },
    "gi": {
        "max_hp": 95,
        "speed": 8.0,
        "attack_damage": 12,
        "attack_range": 8.0,
        "attack_cooldown": 1.1,
        "cost": 200,
        "build_time": 5.0,
        "role": "combat",
    },
    "rocketeer": {
        "max_hp": 120,
        "speed": 12.0,
        "attack_damage": 18,
        "attack_range": 9.0,
        "attack_cooldown": 1.2,
        "cost": 800,
        "build_time": 12.0,
        "role": "combat",
    },
    "grizzly_tank": {
        "max_hp": 320,
        "speed": 8.0,
        "attack_damage": 28,
        "attack_range": 8.5,
        "attack_cooldown": 1.4,
        "cost": 700,
        "build_time": 10.0,
        "role": "combat",
    },
    "prism_tank": {
        "max_hp": 240,
        "speed": 7.0,
        "attack_damage": 45,
        "attack_range": 11.0,
        "attack_cooldown": 2.6,
        "cost": 1200,
        "build_time": 16.0,
        "role": "combat",
    },
    "mirage_tank": {
        "max_hp": 260,
        "speed": 9.0,
        "attack_damage": 38,
        "attack_range": 9.5,
        "attack_cooldown": 1.8,
        "cost": 1000,
        "build_time": 14.0,
        "role": "combat",
    },
    "kirov_airship": {
        "max_hp": 820,
        "speed": 4.0,
        "attack_damage": 120,
        "attack_range": 12.0,
        "attack_cooldown": 3.5,
        "cost": 2000,
        "build_time": 24.0,
        "role": "combat",
    },
}

# Building statistics keyed by building type.
BUILDING_STATS = {
    "construction_yard": {
        "max_hp": 3500,
        "buildable_units": ["conscript", "gi", "ore_miner"],
    },
    "power_plant": {
        "max_hp": 1600,
        "buildable_units": [],
    },
    "ore_refinery": {
        "max_hp": 2200,
        "buildable_units": ["ore_miner"],
    },
    "barracks": {
        "max_hp": 1800,
        "buildable_units": ["conscript", "gi", "rocketeer"],
    },
    "war_factory": {
        "max_hp": 2600,
        "buildable_units": [
            "grizzly_tank",
            "prism_tank",
            "mirage_tank",
            "ore_miner",
        ],
    },
    "airforce_command": {
        "max_hp": 2200,
        "buildable_units": ["rocketeer", "kirov_airship"],
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
