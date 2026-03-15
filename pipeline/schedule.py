#!/usr/bin/env python3
"""
Fetch upcoming MLS schedule and identify the next home game.

Uses the public MLS schedule page — no API key needed.
Only returns home games to save tokens (away games aren't useful
for a guide aimed at people attending in person).
"""
import asyncio
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from config import TEAMS

# MLS schedule URL pattern
SCHEDULE_URL = "https://www.mlssoccer.com/schedule/scores#{slug}/all"

# Map MLS website slugs to our team slugs
MLS_SLUGS = {
    "houston-dynamo": "houston",
    "fc-dallas": "dallas",
    "austin-fc": "austin",
}

# Home venue keywords (case-insensitive substring match)
HOME_VENUES = {
    "houston-dynamo": ["shell energy stadium", "houston"],
    "fc-dallas": ["toyota stadium", "frisco"],
    "austin-fc": ["q2 stadium", "austin"],
}


async def fetch_schedule(team_slug: str) -> list[dict]:
    """
    Fetch the schedule for a team and return upcoming home games.

    Returns a list of dicts: {opponent, date, venue, is_home}
    """
    team_config = TEAMS.get(team_slug)
    if not team_config:
        print(f"Unknown team: {team_slug}")
        return []

    team_name = team_config["name"]
    mls_slug = MLS_SLUGS.get(team_slug, team_slug)

    # Try the MLS API endpoint for schedule data (JSON)
    api_url = f"https://sportapi.mlssoccer.com/api/matches?culture=en-us&dateFrom={date.today()}&dateTo={date.today() + timedelta(days=60)}&clubSlug={mls_slug}"

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        try:
            resp = await client.get(api_url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; GirlfriendGuide/1.0)",
                "Accept": "application/json",
            })
            if resp.status_code == 200:
                return _parse_api_response(resp.json(), team_slug, team_name)
        except Exception as e:
            print(f"   API fetch failed ({e}), trying HTML fallback...")

        # Fallback: scrape the schedule page
        page_url = f"https://www.houstondynamofc.com/schedule"
        try:
            resp = await client.get(page_url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; GirlfriendGuide/1.0)",
            })
            if resp.status_code == 200:
                return _parse_html_schedule(resp.text, team_slug, team_name)
        except Exception as e:
            print(f"   HTML fallback also failed: {e}")

    return []


def _parse_api_response(data: dict, team_slug: str, team_name: str) -> list[dict]:
    """Parse the MLS API JSON response into our match format."""
    matches = []
    home_venues = HOME_VENUES.get(team_slug, [])

    for match in data if isinstance(data, list) else data.get("matches", data.get("results", [])):
        try:
            # Extract fields — MLS API format varies, try common shapes
            home_club = (
                match.get("home", {}).get("fullName", "")
                or match.get("homeClub", {}).get("name", "")
            )
            away_club = (
                match.get("away", {}).get("fullName", "")
                or match.get("awayClub", {}).get("name", "")
            )
            venue = match.get("venue", {}).get("name", "") if isinstance(match.get("venue"), dict) else match.get("venue", "")
            match_date = match.get("matchDate", match.get("date", ""))[:10]

            # Determine if home game
            is_home = (
                team_name.lower() in home_club.lower()
                or any(v in venue.lower() for v in home_venues)
            )

            if is_home:
                opponent = away_club
            else:
                opponent = home_club

            if opponent and match_date:
                matches.append({
                    "opponent": opponent,
                    "date": match_date,
                    "venue": venue,
                    "is_home": is_home,
                })
        except (KeyError, TypeError):
            continue

    return matches


def _parse_html_schedule(html: str, team_slug: str, team_name: str) -> list[dict]:
    """Fallback: parse schedule from team website HTML."""
    soup = BeautifulSoup(html, "html.parser")
    matches = []
    home_venues = HOME_VENUES.get(team_slug, [])
    today = date.today()

    # Look for schedule match elements (common patterns on MLS team sites)
    for el in soup.select("[class*='match'], [class*='schedule'], [class*='game']"):
        text = el.get_text(" ", strip=True)

        # Try to find a date
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        if not date_match:
            continue

        match_date = date_match.group(1)
        if match_date < str(today):
            continue

        # Check for home indicator
        venue_text = text.lower()
        is_home = any(v in venue_text for v in home_venues) or "vs" in text

        # Try to extract opponent
        opponent = ""
        for pattern in [r"vs\.?\s+(.+?)(?:\d|$)", r"at\s+(.+?)(?:\d|$)"]:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                opponent = m.group(1).strip()
                break

        if opponent and match_date:
            matches.append({
                "opponent": opponent,
                "date": match_date,
                "venue": "",
                "is_home": is_home,
            })

    return matches


def get_next_home_game(team_slug: str, matches: list[dict]) -> dict | None:
    """Return the next upcoming home game, or None."""
    today = str(date.today())
    home_games = [m for m in matches if m["is_home"] and m["date"] >= today]
    home_games.sort(key=lambda m: m["date"])
    return home_games[0] if home_games else None


async def main():
    """CLI entry point: print next home game info as JSON for the workflow."""
    import argparse

    parser = argparse.ArgumentParser(description="Check next home game")
    parser.add_argument("--team", required=True, help="Team slug")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    print(f"Fetching schedule for {args.team}...")
    matches = await fetch_schedule(args.team)

    if not matches:
        print("No upcoming matches found.")
        # Output empty JSON for workflow consumption
        print("::set-output name=has_home_game::false")
        sys.exit(0)

    home_games = [m for m in matches if m["is_home"]]
    print(f"Found {len(matches)} upcoming matches, {len(home_games)} at home.")

    next_home = get_next_home_game(args.team, matches)
    if next_home:
        print(f"\nNext home game: vs {next_home['opponent']} on {next_home['date']}")
        if args.json:
            print(json.dumps(next_home))
        # Set GitHub Actions outputs
        print(f"::set-output name=has_home_game::true")
        print(f"::set-output name=opponent::{next_home['opponent']}")
        print(f"::set-output name=date::{next_home['date']}")
    else:
        print("No upcoming home games in the next 60 days.")
        print("::set-output name=has_home_game::false")


if __name__ == "__main__":
    asyncio.run(main())
