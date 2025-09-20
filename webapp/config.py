"""Configuration constants for the web RTS server.

All numeric values can be tuned to adjust the pacing of the match. The
settings have been chosen to roughly emulate the gathering rate and combat
speed of classic RTS titles while keeping the implementation simple.
"""

TICK_RATE = 10  # Simulation ticks per second.

MAP_WIDTH = 80
MAP_HEIGHT = 60
TILE_SIZE = 16  # Size of a tile in client side pixels.

STARTING_CREDITS = 500
CREDIT_CAP = 5000

RESOURCE_NODE_COUNT = 12
RESOURCE_NODE_VALUE = 2000
HARVEST_RATE = 20  # Credits per harvest action.
HARVEST_TIME = 3.0  # Seconds per harvest cycle.

UNIT_BUILD_TIME = 5.0  # Seconds to produce a combat unit.
UNIT_COST = 150
UNIT_SPEED = 5.0  # Tiles per second.
UNIT_ATTACK_RANGE = 4.0
UNIT_ATTACK_DAMAGE = 10
UNIT_ATTACK_COOLDOWN = 1.5
UNIT_MAX_HEALTH = 100

HARVESTER_COST = 250
HARVESTER_BUILD_TIME = 6.0
HARVESTER_SPEED = 4.0
HARVESTER_MAX_HEALTH = 120

BASE_MAX_HEALTH = 1000
BASE_ATTACK_RANGE = 8.0
BASE_ATTACK_DAMAGE = 25
BASE_ATTACK_COOLDOWN = 2.5

# Networking configuration.
MATCHMAKING_TIMEOUT = 30.0  # Seconds to wait for an opponent before bot fill.
MAX_PLAYERS_PER_MATCH = 2

# Client configuration hints.
GAME_NAME = "Nova Frontier"
LOBBY_WELCOME_MESSAGE = (
    "Welcome commander! Gather Tiberite shards, raise an army and crush the opposition."
)
