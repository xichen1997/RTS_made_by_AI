# PvPvE RTS Backend Prototype

This repository contains a Python prototype that models the backend
systems required for a session-based PvPvE arena inspired by classic
real-time strategy games.  The goal is to showcase how a horizontally
scalable, server-authoritative architecture can orchestrate 20–40 human
players, 100–300 AI combatants and dynamic map systems within 10–15
minute matches.

## High level loop

```
Lobby → Loadout → Arena (PvE + PvP) → Extraction/Death → Rewards
```

Players queue through the matchmaking service, configure their loadouts
and drop into an arena that features points of interest, dynamic hazards
and procedurally selected spawn locations.  Surviving the combat phase
grants loot and experience, while death causes the player to lose their
unsecured rewards.

## Repository structure

- `main.py` – Text-based driver that queues players, runs a match and
  prints the resulting rewards.
- `rts/` – Core backend modules:
  - `arena.py` – Generates maps, points of interest and environmental
    hazards.
  - `config.py` – Match configuration and validation helpers.
  - `entities.py` – Player, inventory and AI combatant data structures.
  - `game_server.py` – Authoritative server facade managing sessions.
  - `matchmaking.py` – Skill-based matchmaking queue.
  - `progression.py` – Progression, loot stashing and cosmetics economy
    services.
  - `session.py` – Server-side simulation of a PvPvE match.
- `tests/` – Automated coverage for matchmaking and session logic.

Legacy Pygame rendering and networking experiments have been retained in
case they are useful for future front-end work, but the focus of this
iteration is the backend simulation.

## Installation

The prototype targets Python 3.10 or newer. Create and activate a virtual
environment, then install the dependencies listed in
[`requirements.txt`](requirements.txt):

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The dependencies include tooling for tests and legacy rendering
experiments. They are lightweight and allow you to run the backend demo
as well as revisit the earlier Pygame prototypes if desired.

## Running the demo

With the environment prepared, execute the main entry point:

```
python main.py
```

The script enqueues 24 mock players, drives the server tick loop until
all matches resolve and prints the reward summary for each participant.

## Tests

The project uses `pytest` for validation.  Run the following command to
execute the suite:

```
pytest
```

## Extending the prototype

The code is intentionally modular so that services can be split into
separate micro-services or scaled horizontally.  Suggested next steps
include:

- Replacing the random combat resolution with deterministic, lockstep
  simulation.
- Persisting player progression to a database.
- Reintroducing a modern client (web or native) that connects to the
  authoritative server using websockets or gRPC.
