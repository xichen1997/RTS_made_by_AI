"""Domain entities used by the RTS server simulation."""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class PlayerStatus(Enum):
    """Lifecycle state of a player inside a session."""

    LOBBY = "lobby"
    DEPLOYING = "deploying"
    ACTIVE = "active"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    DOWNED = "downed"
    ELIMINATED = "eliminated"


@dataclass
class Loadout:
    """Configuration chosen by the player in the loadout screen."""

    archetype: str
    primary_weapon: str
    secondary_weapon: str
    utility: str
    tech_level: int = 1


@dataclass
class PlayerProfile:
    """Account level information that persists between matches."""

    account_id: uuid.UUID
    display_name: str
    skill_rating: int = 1200


@dataclass
class InventoryItem:
    """Representation of an item that can be looted in the arena."""

    item_id: uuid.UUID
    name: str
    rarity: str
    value: int
    cosmetic: bool = False


@dataclass
class Inventory:
    """Tracks items carried by the player."""

    capacity: int = 10
    equipped: Dict[str, InventoryItem] = field(default_factory=dict)
    backpack: List[InventoryItem] = field(default_factory=list)

    def can_loot(self) -> bool:
        return len(self.backpack) < self.capacity

    def add(self, item: InventoryItem) -> None:
        if not self.can_loot():
            raise ValueError("Inventory is full")
        self.backpack.append(item)

    def clear_backpack(self) -> List[InventoryItem]:
        loot = list(self.backpack)
        self.backpack.clear()
        return loot


@dataclass
class PlayerState:
    profile: PlayerProfile
    loadout: Loadout
    status: PlayerStatus = PlayerStatus.LOBBY
    inventory: Inventory = field(default_factory=Inventory)
    xp: int = 0
    level: int = 1
    loot_secured: List[InventoryItem] = field(default_factory=list)

    def mark_extracted(self) -> None:
        self.status = PlayerStatus.EXTRACTED
        self.loot_secured.extend(self.inventory.clear_backpack())

    def mark_eliminated(self) -> None:
        self.status = PlayerStatus.ELIMINATED
        self.inventory.clear_backpack()


class MobBehavior(Enum):
    PATROL = "patrol"
    HUNT = "hunt"
    DEFEND = "defend"


@dataclass
class AIMob:
    """Simplified representation of an AI combatant."""

    mob_id: uuid.UUID
    species: str
    health: int
    damage: int
    position: tuple[int, int]
    behavior: MobBehavior = MobBehavior.PATROL

    def is_alive(self) -> bool:
        return self.health > 0

    def tick(self) -> None:
        if not self.is_alive():
            return
        roll = random.random()
        if self.behavior == MobBehavior.PATROL and roll < 0.1:
            self.behavior = MobBehavior.HUNT
        elif self.behavior == MobBehavior.HUNT and roll < 0.05:
            self.behavior = MobBehavior.DEFEND
        elif self.behavior == MobBehavior.DEFEND and roll < 0.1:
            self.behavior = MobBehavior.PATROL

    def apply_damage(self, amount: int) -> bool:
        self.health = max(0, self.health - amount)
        return self.health == 0


def random_inventory_item() -> InventoryItem:
    rarity = random.choices(
        population=["common", "rare", "epic", "legendary"],
        weights=[0.65, 0.25, 0.08, 0.02],
        k=1,
    )[0]
    base_value = {"common": 100, "rare": 250, "epic": 500, "legendary": 1000}[rarity]
    return InventoryItem(
        item_id=uuid.uuid4(),
        name=f"Loot-{rarity}-{random.randint(1000, 9999)}",
        rarity=rarity,
        value=base_value + random.randint(-50, 150),
        cosmetic=random.random() < 0.15,
    )
