"""Backend package for the Red Horizon Online RTS web application."""

from .game import GameFullError, RTSGame

__all__ = ["RTSGame", "GameFullError"]
