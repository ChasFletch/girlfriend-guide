"""
Roster scraper — fetches the current roster and player headshot URLs
from an MLS team's website.
"""
import base64
import httpx
from bs4 import BeautifulSoup
from pathlib import Path
import json


async def fetch_roster(team_config: dict) -> list[dict]:
    """
    Scrape the team's roster page for player names, numbers, positions,
    and headshot image URLs.

    Returns a list of player dicts:
    [
        {
            "name": "Héctor Herrera",
            "jersey_number": 16,
            "position": "Midfielder",
            "headshot_url": "https://..."
        },
        ...
    ]
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            team_config["mls_roster_url"],
            headers={"User-Agent": "GirlfriendGuide/1.0"},
            follow_redirects=True,
        )
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    players = []

    # MLS team sites typically use structured roster cards.
    # This selector targets common MLS roster page patterns.
    # May need adjustment per-team if markup differs.
    for card in soup.select(".roster-player, [class*='PlayerCard'], [class*='player-card']"):
        name_el = card.select_one(
            "[class*='player-name'], [class*='PlayerName'], .player-card__name, h3, h4"
        )
        number_el = card.select_one(
            "[class*='player-number'], [class*='PlayerNumber'], .player-card__number"
        )
        position_el = card.select_one(
            "[class*='player-position'], [class*='PlayerPosition'], .player-card__position"
        )
        img_el = card.select_one("img")

        if not name_el:
            continue

        player = {
            "name": name_el.get_text(strip=True),
            "jersey_number": _parse_number(number_el.get_text(strip=True)) if number_el else None,
            "position": position_el.get_text(strip=True) if position_el else "Unknown",
            "headshot_url": _resolve_img_url(img_el, team_config["mls_roster_url"]) if img_el else None,
        }
        players.append(player)

    return players


async def download_headshots(players: list[dict], output_dir: Path) -> list[dict]:
    """
    Download headshot images for each player into output_dir.
    Updates each player dict with a local 'headshot_path' field.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient() as client:
        for player in players:
            if not player.get("headshot_url"):
                player["headshot_path"] = None
                continue

            filename = _slugify(player["name"]) + ".jpg"
            filepath = output_dir / filename

            try:
                resp = await client.get(player["headshot_url"], follow_redirects=True)
                resp.raise_for_status()
                filepath.write_bytes(resp.content)
                player["headshot_path"] = str(filepath)
                player["headshot_b64"] = base64.b64encode(resp.content).decode("utf-8")
            except httpx.HTTPError:
                player["headshot_path"] = None
                player["headshot_b64"] = None

    return players


def load_roster_override(override_path: Path) -> list[dict] | None:
    """
    Load a manually curated roster JSON file.
    Use this when scraping fails or for corrections.
    """
    if override_path.exists():
        return json.loads(override_path.read_text())
    return None


def _parse_number(text: str) -> int | None:
    digits = "".join(c for c in text if c.isdigit())
    return int(digits) if digits else None


def _resolve_img_url(img_el, base_url: str) -> str | None:
    src = img_el.get("data-src") or img_el.get("src")
    if not src:
        return None
    if src.startswith("http"):
        return src
    if src.startswith("//"):
        return "https:" + src
    if src.startswith("/"):
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{src}"
    return src


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace(".", "").replace("é", "e").replace("ú", "u")
