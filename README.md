# RTS Game Developer Documentations

Welcome to the RTS Game project! This document serves as a guide for developers looking to contribute to this simplified real-time strategy (RTS) game developed using Python and the Pygame library. The game features basic multiplayer functionality through a client-server network architecture.

## Table of Contents

- [Project Overview](#project-overview)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Development Guidelines](#development-guidelines)
- [Contributing](#contributing)
- [License](#license)

## Project Overview

The RTS Game is a real-time strategy game where players build and manage their own virtual civilizations. It offers a rich and immersive gaming experience, allowing players to explore, expand, exploit, and exterminate in a dynamic and ever-changing world.

## Getting Started

To get started with development, follow these steps:

1. Clone the repository: `git clone https://github.com/your-username/RTS_game.git`
2. Navigate to the project directory: `cd RTS_game`
3. Install dependencies: `pip install -r requirements.txt`
4. Start the web server: `python app.py`
5. Open the game in your browser: `http://127.0.0.1:5000`

The legacy Pygame prototype is still available through `python main.py`,
but the recommended way to experience the project is via the new web
client.

## Project Structure

The project is organized as follows:

- `__pycache__/`: Python cache files.
- `game.py`: Handles game logic, rendering, and state updates for the legacy desktop prototype.
- `app.py`: Flask application that serves the browser based prototype.
- `main.py`: Legacy Pygame entry point kept for reference.
- `map_generator.py`: Responsible for generating the game map and managing terrain.
- `web_map_generator.py`: Headless map generator used by the web server.
- `templates/` and `static/`: Assets powering the single page web client.
- `network/`: Contains networking code with `client.py` and `server.py` for multiplayer functionality.
- `README.md`: Project documentation.
- `test_all.py`: Script for running all tests.

## Development Guidelines

When developing for the RTS Game, please adhere to the following guidelines:

- **Code Style**: Follow PEP 8 style guide for Python code.
- **Commit Messages**: Use clear and descriptive commit messages.
- **Testing**: Write tests for new features and bug fixes when possible.
- **Documentation**: Update the README.md and inline documentation as needed.

## Contributing

We welcome contributions to the RTS Game project! If you'd like to contribute, please follow our contribution guidelines and submit a pull request. For more details, refer to the [Contributing](#contributing) section of the main README.md.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.
