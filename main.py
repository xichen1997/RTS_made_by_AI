"""Text based driver showcasing the PvPvE match flow."""

from __future__ import annotations

import random
import uuid
from typing import List

from rts import GameServer, Loadout, MatchConfig, PlayerProfile


def _generate_players(count: int) -> List[PlayerProfile]:
    profiles = []
    for idx in range(count):
        profile = PlayerProfile(
            account_id=uuid.uuid4(),
            display_name=f"Commander-{idx + 1}",
            skill_rating=random.randint(1000, 1800),
        )
        profiles.append(profile)
    return profiles


def _generate_loadout() -> Loadout:
    return Loadout(
        archetype=random.choice(["Assault", "Engineer", "Support", "Recon"]),
        primary_weapon=random.choice(["Railgun", "Plasma Rifle", "Gatling Laser"]),
        secondary_weapon=random.choice(["SMG", "Shotgun", "Pistol"]),
        utility=random.choice(["Deployable Shield", "Med Drone", "EMP Charge"]),
        tech_level=random.randint(1, 5),
    )


def run_demo(player_count: int = 24) -> None:
    config = MatchConfig(min_players=20, max_players=40, match_duration_seconds=10 * 60)
    server = GameServer(config)
    profiles = _generate_players(player_count)
    print("[Lobby] Queueing players for matchmaking...")
    for profile in profiles:
        server.enqueue_player(profile, _generate_loadout())
    print(f"[Matchmaking] {player_count} players queued. Spinning server ticks...")
    server.run_until_idle()
    print("[Rewards] Matches resolved. Granting progression and loot.")
    for profile in profiles:
        rewards = server.collect_rewards(profile.account_id)
        if not rewards:
            continue
        summary, stash = rewards
        print(
            f"- {profile.display_name}: +{summary.xp_gained} XP, "
            f"Loot secured={len(summary.loot_secured)}, Cosmetics={summary.cosmetics_unlocked}"
        )


if __name__ == "__main__":
    run_demo()
