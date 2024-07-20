# RTS Game Developer Documentation

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
3. Install dependencies: `pip install pygame noise`
4. Start the game: `python main.py`

## Project Structure

The project is organized as follows:

- `__pycache__/`: Python cache files.
- `game.py`: Handles game logic, rendering, and state updates.
- `main.py`: The entry point of the game. Manages game initialization and the main game loop.
- `map_generator.py`: Responsible for generating the game map and managing terrain.
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