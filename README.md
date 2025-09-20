# Red Horizon Online

Red Horizon Online is a browser-based real-time strategy game inspired by
classic base building titles such as *Command & Conquer: Red Alert 2*. The
project ships with a FastAPI backend that simulates the battlefield on the
server and a lightweight HTML5 canvas client that renders the warzone inside
any modern web browser. Matches are room-based and support up to four human
commanders fighting across the same online lobby.

## Features

- **Authoritative server** – the FastAPI application keeps the canonical game
  state, processes unit orders and streams snapshots to connected clients over
  WebSockets.
- **Resource economy** – harvest ore fields to earn credits, queue production at
  your HQ or factory and grow your army.
- **Combined arms combat** – infantry, tanks and harvesters each have unique
  statistics and behaviours. Units automatically retaliate when enemy forces
  approach.
- **Cooperative networking** – host the server once and share the room ID with
  friends to play together directly from your browsers.

## Getting started

### Prerequisites

- Python 3.10 or newer

### Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Launching the server

```bash
uvicorn app.server:app --reload
```

The server listens on `http://127.0.0.1:8000/` by default. Open that address in
one or more browser tabs, choose a commander name and join the same room to
start a match.

### Controls

- **Left click** your units or buildings to select them. Hold <kbd>Shift</kbd>
  to add or remove additional units from the selection.
- **Right click** the map to move your army. Right click enemy units or
  structures to attack them.
- **Right click** resource fields with harvesters selected to send them mining.
- Use the buttons in the Production panel to queue new units while your
  headquarters or factory are selected.

## Running tests

The repository includes a focused test suite that validates the core economic
loop and combat logic. Execute it with:

```bash
pytest
```

## Project structure

```
app/          # FastAPI application and game simulation
web/          # Static HTML/CSS/JS front-end client
README.md     # This file
requirements.txt
```

## Contributing

Pull requests are welcome. Please ensure code is type annotated and documented,
run the supplied tests and linting tools before submitting changes.
