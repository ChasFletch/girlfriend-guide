#!/usr/bin/env python3
"""
Opponent scouting — research 3 key players from the opposing team each match.

Builds a database over time so future guides can include "ones to watch"
from the visiting squad without re-spending tokens on already-researched players.
"""
import json
from pathlib import Path

from roster import fetch_roster
from research import research_all


# How many new opponent players to research per match
SCOUT_COUNT = 3

# MLS team roster URLs (expand as needed)
OPPONENT_ROSTER_URLS = {
    # Western Conference
    "LA Galaxy": "https://www.lagalaxy.com/roster",
    "LAFC": "https://www.lafc.com/roster",
    "Portland Timbers": "https://www.timbers.com/roster",
    "Seattle Sounders FC": "https://www.soundersfc.com/roster",
    "Real Salt Lake": "https://www.rsl.com/roster",
    "Colorado Rapids": "https://www.coloradorapids.com/roster",
    "Minnesota United FC": "https://www.mnufc.com/roster",
    "Vancouver Whitecaps FC": "https://www.whitecapsfc.com/roster",
    "San Jose Earthquakes": "https://www.sjearthquakes.com/roster",
    "Sporting Kansas City": "https://www.sportingkc.com/roster",
    "St. Louis CITY SC": "https://www.stlcitysc.com/roster",
    "San Diego FC": "https://www.sandiegofc.com/roster",
    # Eastern Conference
    "Inter Miami CF": "https://www.intermiamicf.com/roster",
    "Columbus Crew": "https://www.columbuscrew.com/roster",
    "FC Cincinnati": "https://www.fccincinnati.com/roster",
    "Charlotte FC": "https://www.charlottefc.com/roster",
    "Nashville SC": "https://www.nashvillesc.com/roster",
    "New York Red Bulls": "https://www.newyorkredbulls.com/roster",
    "New York City FC": "https://www.newyorkcityfc.com/roster",
    "Philadelphia Union": "https://www.philadelphiaunion.com/roster",
    "Atlanta United FC": "https://www.atlutd.com/roster",
    "Orlando City SC": "https://www.orlandocitysc.com/roster",
    "Toronto FC": "https://www.torontofc.ca/roster",
    "CF Montréal": "https://www.cfmontreal.com/roster",
    "D.C. United": "https://www.dcunited.com/roster",
    "Chicago Fire FC": "https://www.chicagofirefc.com/roster",
    "New England Revolution": "https://www.revolutionsoccer.net/roster",
    # Texas teams (opponents to each other)
    "Houston Dynamo FC": "https://www.houstondynamofc.com/roster",
    "FC Dallas": "https://www.fcdallas.com/roster",
    "Austin FC": "https://www.austinfc.com/roster",
}


def load_opponent_db(db_path: Path) -> dict:
    """Load the existing opponent database."""
    if db_path.exists():
        return json.loads(db_path.read_text())
    return {}


def save_opponent_db(db: dict, db_path: Path):
    """Save the opponent database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_text(json.dumps(db, indent=2, default=str))


def pick_players_to_scout(roster: list[dict], already_scouted: list[str], count: int = SCOUT_COUNT) -> list[dict]:
    """
    Pick players to scout, prioritizing:
    1. Players we haven't researched yet
    2. Forwards and midfielders (more interesting for the audience)
    """
    # Filter out already-scouted players
    unscouted = [p for p in roster if p.get("name", "") not in already_scouted]

    if not unscouted:
        # Everyone's been scouted — skip
        return []

    # Sort: forwards first, then midfielders, then defenders, then goalkeepers
    position_priority = {"forward": 0, "midfielder": 1, "defender": 2, "goalkeeper": 3}

    def sort_key(p):
        pos = p.get("position", "").lower()
        for key, val in position_priority.items():
            if key in pos:
                return val
        return 4

    unscouted.sort(key=sort_key)

    return unscouted[:count]


async def scout_opponent(opponent_name: str, base_dir: Path) -> list[dict]:
    """
    Research 3 players from the opponent team.
    Saves results to the opponent database so we don't re-research them.
    """
    db_path = base_dir / "data" / "opponents.json"
    db = load_opponent_db(db_path)

    # Get the opponent's roster URL
    roster_url = OPPONENT_ROSTER_URLS.get(opponent_name)
    if not roster_url:
        # Try fuzzy match
        for name, url in OPPONENT_ROSTER_URLS.items():
            if opponent_name.lower() in name.lower() or name.lower() in opponent_name.lower():
                roster_url = url
                opponent_name = name
                break

    if not roster_url:
        print(f"   ⚠️  No roster URL for opponent: {opponent_name}")
        return []

    # Fetch opponent roster
    opponent_config = {
        "name": opponent_name,
        "mls_roster_url": roster_url,
    }

    print(f"   Fetching {opponent_name} roster...")
    try:
        roster = await fetch_roster(opponent_config)
    except Exception as e:
        print(f"   ⚠️  Could not fetch opponent roster: {e}")
        return []

    if not roster:
        print(f"   ⚠️  No players found for {opponent_name}")
        return []

    # Check what we already have
    team_db = db.get(opponent_name, {})
    already_scouted = list(team_db.keys())

    # Pick players to research
    to_scout = pick_players_to_scout(roster, already_scouted)
    if not to_scout:
        print(f"   ✅ All {opponent_name} players already in database ({len(already_scouted)} scouted)")
        return list(team_db.values())

    print(f"   🔍 Scouting {len(to_scout)} new players: {', '.join(p['name'] for p in to_scout)}")

    # Research them
    scouted = await research_all(to_scout)

    # Save to database
    for player in scouted:
        name = player.get("name", "")
        if name:
            team_db[name] = player

    db[opponent_name] = team_db
    save_opponent_db(db, db_path)

    print(f"   💾 Opponent database updated: {len(team_db)} total players for {opponent_name}")

    return scouted
