"""Arena generation utilities."""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class PointOfInterest:
    poi_id: uuid.UUID
    name: str
    position: Tuple[int, int]
    loot_multiplier: float


@dataclass
class Hazard:
    hazard_id: uuid.UUID
    name: str
    area: Tuple[int, int]
    damage_per_tick: int
    duration: int

    def relocate(self, map_size: Tuple[int, int]) -> None:
        self.area = (
            random.randint(0, map_size[0]),
            random.randint(0, map_size[1]),
        )
        self.duration = random.randint(30, 90)


@dataclass
class ArenaMap:
    width: int
    height: int
    points_of_interest: List[PointOfInterest]
    hazards: List[Hazard]
    spawn_points: List[Tuple[int, int]]

    @classmethod
    def generate(cls, hazard_count: int) -> "ArenaMap":
        width, height = 4000, 4000
        pois = [
            PointOfInterest(uuid.uuid4(), "Derelict Base", (800, 1000), 1.4),
            PointOfInterest(uuid.uuid4(), "Power Relay", (2000, 1800), 1.2),
            PointOfInterest(uuid.uuid4(), "Research Lab", (3200, 900), 1.6),
            PointOfInterest(uuid.uuid4(), "Supply Depot", (1500, 3200), 1.1),
        ]
        hazards = [
            Hazard(
                hazard_id=uuid.uuid4(),
                name=random.choice(["Ion Storm", "Tiber Toxicity", "Sand Surge"]),
                area=(random.randint(0, width), random.randint(0, height)),
                damage_per_tick=random.randint(5, 20),
                duration=random.randint(30, 90),
            )
            for _ in range(hazard_count)
        ]
        spawn_points = [
            (random.randint(0, width), random.randint(0, height))
            for _ in range(12)
        ]
        return cls(width, height, pois, hazards, spawn_points)

    def rotate_hazards(self) -> None:
        for hazard in self.hazards:
            hazard.relocate((self.width, self.height))

    def random_spawn(self) -> Tuple[int, int]:
        return random.choice(self.spawn_points)
