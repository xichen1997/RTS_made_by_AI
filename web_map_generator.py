"""Utility to generate terrain maps for the web client.

This module mirrors the high level ideas of the original Pygame based
map generator but avoids any dependency on pygame so it can safely run
in a headless web server context.  The generator exposes a small API
that is convenient both for the Flask endpoints and for unit tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence
import random

import noise

# Default map configuration.  The values can be customised by
# instantiating :class:`WebMapGenerator` with different parameters.
DEFAULT_MAP_WIDTH = 128
DEFAULT_MAP_HEIGHT = 128

# The colour palette is kept in hex so the JavaScript client can use it
# without additional conversion.
TERRAIN_COLOURS: Dict[str, str] = {
    "deep_water": "#00008b",
    "shallow_water": "#4169e1",
    "beach": "#eed6af",
    "grassland": "#228b22",
    "forest": "#006400",
    "hills": "#a0522d",
    "mountains": "#8b8989",
    "snow_peaks": "#fffafa",
}


@dataclass(frozen=True)
class Tile:
    """Light-weight representation of a tile in the generated map."""

    x: int
    y: int
    terrain: str


class WebMapGenerator:
    """Generate 2D terrain maps using Perlin noise.

    The generator is intentionally deterministic for a given seed so the
    front end can request a new map with predictable results.  The
    implementation borrows the biome thresholds from the original
    ``map_generator`` module while staying independent from pygame.
    """

    def __init__(
        self,
        width: int = DEFAULT_MAP_WIDTH,
        height: int = DEFAULT_MAP_HEIGHT,
        *,
        seed: int | None = None,
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be positive integers")

        self.width = width
        self.height = height
        self.seed = random.randint(0, 1000) if seed is None else seed
        self._tiles: List[List[Tile]] | None = None

    # ------------------------------------------------------------------
    # Map generation helpers
    # ------------------------------------------------------------------
    def _get_elevation(self, x: int, y: int) -> float:
        return noise.pnoise2(
            x / self.width,
            y / self.height,
            octaves=6,
            persistence=0.5,
            lacunarity=2.0,
            repeatx=1024,
            repeaty=1024,
            base=self.seed,
        )

    def _get_moisture(self, x: int, y: int) -> float:
        return noise.pnoise2(
            x / self.width,
            y / self.height,
            octaves=4,
            persistence=0.6,
            lacunarity=2.0,
            repeatx=1024,
            repeaty=1024,
            base=self.seed + 1,
        )

    @staticmethod
    def _classify_terrain(elevation: float, moisture: float) -> str:
        if elevation < -0.3:
            return "deep_water"
        if elevation < -0.1:
            return "shallow_water"
        if elevation < 0.0:
            return "beach"
        if elevation < 0.3:
            return "grassland" if moisture < 0 else "forest"
        if elevation < 0.6:
            return "hills"
        if elevation < 0.8:
            return "mountains"
        return "snow_peaks"

    def _ensure_map_generated(self) -> None:
        if self._tiles is not None:
            return

        tiles: List[List[Tile]] = []
        for y in range(self.height):
            row: List[Tile] = []
            for x in range(self.width):
                elevation = self._get_elevation(x, y)
                moisture = self._get_moisture(x, y)
                terrain = self._classify_terrain(elevation, moisture)
                row.append(Tile(x=x, y=y, terrain=terrain))
            tiles.append(row)
        self._tiles = tiles

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_tiles(self) -> Sequence[Sequence[Tile]]:
        """Return the generated tile grid.

        The map is generated lazily, ensuring that instantiation is
        inexpensive if the caller only needs metadata.  The returned
        structure is immutable from the caller's perspective, but the
        actual :class:`Tile` objects are shared to minimise allocations.
        """

        self._ensure_map_generated()
        assert self._tiles is not None
        return self._tiles

    def serialise(self) -> Dict[str, object]:
        """Return a JSON-serialisable representation of the map."""

        tiles = self.get_tiles()
        return {
            "width": self.width,
            "height": self.height,
            "seed": self.seed,
            "tiles": [[tile.terrain for tile in row] for row in tiles],
            "colours": TERRAIN_COLOURS,
        }

    def regenerate(self, *, seed: int | None = None) -> None:
        """Invalidate the cached map and build a new one.

        Parameters
        ----------
        seed:
            Optional seed to use for the next generation.  If ``None`` the
            generator picks a new random seed.
        """

        self.seed = random.randint(0, 1000) if seed is None else seed
        self._tiles = None


__all__ = ["Tile", "WebMapGenerator", "TERRAIN_COLOURS"]
