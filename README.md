# ChronoFront – Web RTS Prototype

ChronoFront is a browser-based real-time strategy game inspired by
classic base building titles such as *Red Alert 2*. The experience is
served entirely from Python using FastAPI and synchronises state with
connected clients over WebSockets so that friends can join the same
match across the network.

## Features

- **Authoritative simulation** – the server drives the match, handling
  unit production, combat resolution and victory detection.
- **Fast WebSocket updates** – clients receive frequent state snapshots
  and send commands with low latency.
- **Built-in UI** – a responsive control panel for production,
  rally point management and match events.
- **Extensible code** – the game logic lives in well-documented Python
  modules that can be extended with new unit types or mechanics.

## Getting started

Create and activate a virtual environment, then install the
requirements:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Launch the web server:

```bash
python main.py
```

Open `http://localhost:8000/` in your browser. Each additional tab or
player on your network can connect to the same address to join the
match. Players select units with the left mouse button and issue move
orders with the right mouse button. Use the buttons in the Production
panel to queue new units.

## Development

- **Server code** lives under `rts_web/` with the simulation in
  `rts_web/game/`.
- **Static files** (`index.html`, `style.css`, `main.js`) are under
  `web/static/`.
- **Tests** are located in `tests/` and can be executed with `pytest`.

To iterate on the front-end, update the assets under `web/static` and
refresh the browser. The FastAPI application automatically serves the
latest files.

## Testing

Run the unit test suite with:

```bash
pytest
```

## Roadmap ideas

- Additional unit types with unique abilities.
- Fog of war and scouting mechanics.
- Dedicated matchmaking lobby and multiple concurrent matches.
- Persistent player profiles and statistics.
