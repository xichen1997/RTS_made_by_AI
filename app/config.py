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

# Unit statistics keyed by unit type. Inspired by classic Red Alert 2 units.
UNIT_STATS = {
    "ore_miner": {
        "max_hp": 320,
        "speed": 5.2,
        "attack_damage": 0,
        "attack_range": 0,
        "attack_cooldown": 1.0,
        "cost": 800,
        "build_time": 12.0,
        "role": "harvester",
    },
    "conscript": {
        "max_hp": 90,
        "speed": 9.5,
        "attack_damage": 9,
        "attack_range": 6.0,
        "attack_cooldown": 0.8,
        "cost": 100,
        "build_time": 3.0,
    },
    "gi": {
        "max_hp": 140,
        "speed": 7.5,
        "attack_damage": 16,
        "attack_range": 7.0,
        "attack_cooldown": 1.0,
        "cost": 250,
        "build_time": 5.0,
    },
    "engineer": {
        "max_hp": 60,
        "speed": 8.5,
        "attack_damage": 0,
        "attack_range": 0,
        "attack_cooldown": 1.5,
        "cost": 500,
        "build_time": 6.0,
    },
    "rocketeer": {
        "max_hp": 110,
        "speed": 11.0,
        "attack_damage": 14,
        "attack_range": 8.5,
        "attack_cooldown": 0.9,
        "cost": 600,
        "build_time": 8.0,
    },
    "grizzly_tank": {
        "max_hp": 420,
        "speed": 6.5,
        "attack_damage": 32,
        "attack_range": 8.0,
        "attack_cooldown": 1.4,
        "cost": 700,
        "build_time": 10.0,
    },
    "prism_tank": {
        "max_hp": 360,
        "speed": 6.8,
        "attack_damage": 48,
        "attack_range": 11.0,
        "attack_cooldown": 2.0,
        "cost": 1200,
        "build_time": 16.0,
    },
    "ifv": {
        "max_hp": 280,
        "speed": 8.0,
        "attack_damage": 20,
        "attack_range": 9.0,
        "attack_cooldown": 1.2,
        "cost": 650,
        "build_time": 9.0,
    },
    "mirage_tank": {
        "max_hp": 380,
        "speed": 7.2,
        "attack_damage": 42,
        "attack_range": 10.0,
        "attack_cooldown": 1.8,
        "cost": 1000,
        "build_time": 14.0,
    },
}

# Building statistics keyed by building type.
BUILDING_STATS = {
    "construction_yard": {
        "max_hp": 4000,
        "buildable_units": ["engineer"],
    },
    "power_plant": {
        "max_hp": 1500,
        "buildable_units": [],
    },
    "ore_refinery": {
        "max_hp": 2200,
        "buildable_units": ["ore_miner"],
    },
    "barracks": {
        "max_hp": 1800,
        "buildable_units": ["conscript", "gi", "engineer", "rocketeer"],
    },
    "war_factory": {
        "max_hp": 2500,
        "buildable_units": ["grizzly_tank", "ifv", "mirage_tank", "prism_tank"],
    },
    "airforce_command": {
        "max_hp": 2100,
        "buildable_units": ["rocketeer"],
    },
    "prism_tower": {
        "max_hp": 1600,
        "buildable_units": [],
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
