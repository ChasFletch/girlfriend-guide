#!/usr/bin/env python3
"""
Opponent scouting — research 3 key players from the opposing team each match.

Uses Perplexity to find players who have active social media AND whose
partners also have active social media. Builds a database over time so
future guides can include "ones to watch" without re-researching.
"""
import json
from pathlib import Path

from config import OPPONENT_SCOUT_PROMPT
from research import _call_perplexity, _extract_json, research_player, verify_player


def load_opponent_db(db_path: Path) -> dict:
    """Load the existing opponent database."""
    if db_path.exists():
        return json.loads(db_path.read_text())
    return {}


def save_opponent_db(db: dict, db_path: Path):
    """Save the opponent database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_text(json.dumps(db, indent=2, default=str))


async def scout_opponent(opponent_name: str, base_dir: Path) -> list[dict]:
    """
    Use Perplexity to find 3 opponent players with active social media
    (both player AND partner must have Instagram). Then do a full
    research + verify pass on each one.
    """
    import asyncio

    db_path = base_dir / "data" / "opponents.json"
    db = load_opponent_db(db_path)
    team_db = db.get(opponent_name, {})
    already_scouted = list(team_db.keys())

    # Build exclude clause so we don't re-research known players
    exclude_clause = ""
    if already_scouted:
        names = ", ".join(already_scouted)
        exclude_clause = f"EXCLUDE these players (already in our database): {names}"

    # Ask Perplexity to find 3 players with social media + partner social media
    prompt = OPPONENT_SCOUT_PROMPT.format(
        opponent_name=opponent_name,
        exclude_clause=exclude_clause,
    )

    print(f"   Asking Perplexity for {opponent_name} players with active social media...")
    result = await _call_perplexity(prompt)
    candidates = _extract_json(result)

    if not candidates:
        print(f"   ⚠️  Could not parse opponent scout results")
        return []

    # Handle case where result is a dict with a list inside
    if isinstance(candidates, dict):
        for key in ("players", "results", "data"):
            if key in candidates and isinstance(candidates[key], list):
                candidates = candidates[key]
                break
        else:
            candidates = [candidates]

    # Filter: prefer players with social links, but don't require them
    valid = []
    for c in candidates:
        if c.get("name") in already_scouted:
            continue
        valid.append(c)

    # Sort so players with the most social links come first
    valid.sort(
        key=lambda c: (
            bool(c.get("player_instagram")),
            bool(c.get("partner_instagram")),
        ),
        reverse=True,
    )

    if not valid:
        print(f"   ⚠️  No valid candidates found (need both player + partner Instagram)")
        return []

    print(f"   🔍 Scouting {len(valid)} players: {', '.join(c['name'] for c in valid)}")

    # Build player dicts and run full research + verify on each
    players = []
    for c in valid:
        player = {
            "name": c["name"],
            "jersey_number": c.get("jersey_number"),
            "position": c.get("position", "Unknown"),
            "player_instagram": c.get("player_instagram"),
            "partner_name": c.get("partner_name"),
            "partner_instagram": c.get("partner_instagram"),
        }
        players.append(player)

    # Research and verify in parallel
    research_tasks = [research_player(p, opponent_name) for p in players]
    await asyncio.gather(*research_tasks)

    verify_tasks = [verify_player(p) for p in players]
    await asyncio.gather(*verify_tasks)

    # Save to database
    for player in players:
        name = player.get("name", "")
        if name:
            # Store a clean version (no binary data)
            entry = {k: v for k, v in player.items() if k not in ("headshot_b64", "caricature_b64")}
            team_db[name] = entry

    db[opponent_name] = team_db
    save_opponent_db(db, db_path)

    print(f"   💾 Opponent database updated: {len(team_db)} total players for {opponent_name}")

    return players
