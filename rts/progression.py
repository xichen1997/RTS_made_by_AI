"""Progression, inventory persistence and cosmetic economy services."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List

from .entities import InventoryItem, PlayerState


@dataclass
class RewardSummary:
    """Summary returned to clients once the match resolves."""

    xp_gained: int
    loot_secured: List[InventoryItem]
    cosmetics_unlocked: List[str]


class ProgressionService:
    """Handles XP gain and levelling curves."""

    def __init__(self) -> None:
        self._xp_curve: Dict[int, int] = {level: int(100 * math.pow(level, 1.2)) for level in range(1, 200)}

    def grant_match_rewards(self, player: PlayerState, survived: bool, kills: int) -> RewardSummary:
        base_xp = 150 if survived else 75
        xp_gained = base_xp + kills * 25 + len(player.loot_secured) * 10
        player.xp += xp_gained
        self._level_check(player)
        cosmetics = []
        for item in list(player.loot_secured):
            if item.cosmetic:
                cosmetics.append(item.name)
        return RewardSummary(xp_gained=xp_gained, loot_secured=list(player.loot_secured), cosmetics_unlocked=cosmetics)

    def _level_check(self, player: PlayerState) -> None:
        while player.level + 1 in self._xp_curve and player.xp >= self._xp_curve[player.level + 1]:
            player.level += 1


class InventoryService:
    """Applies the post-match loot rules."""

    def stash_loot(self, player: PlayerState) -> None:
        player.inventory.backpack.clear()

    def return_loot(self, player: PlayerState) -> List[InventoryItem]:
        loot = list(player.loot_secured)
        player.loot_secured.clear()
        return loot
