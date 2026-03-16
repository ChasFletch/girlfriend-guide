"""
Research module — uses Perplexity Sonar API for player research
and a second verification pass. Supports caching to avoid redundant API calls.
"""
import json
import httpx
from datetime import datetime, timezone
from pathlib import Path
from config import (
    PERPLEXITY_API_KEY,
    PERPLEXITY_BASE_URL,
    PERPLEXITY_MODEL,
    RESEARCH_PROMPT,
    VERIFY_PROMPT,
)

CACHE_MAX_AGE_DAYS = 7


async def research_player(player: dict, team_name: str = "MLS") -> dict:
    """
    First pass: research a player's personal life, relationships, fun facts.
    Returns raw research JSON merged with the original player dict.
    """
    prompt = RESEARCH_PROMPT.format(
        team_name=team_name,
        player_name=player["name"],
        jersey_number=player.get("jersey_number", "?"),
        position=player.get("position", "Unknown"),
    )

    result = await _call_perplexity(prompt)

    # Parse the JSON from Perplexity's response
    research = _extract_json(result)
    if research:
        player["research"] = research
        player["research"]["_raw_response"] = result
    else:
        player["research"] = {"_raw_response": result, "_parse_error": True}

    return player


async def verify_player(player: dict) -> dict:
    """
    Second pass: verify the claims from the research pass.
    Adds confidence scores to each field.
    """
    research = player.get("research", {})
    if research.get("_parse_error"):
        player["verified"] = research
        return player

    # Build claims to verify (skip internal fields)
    claims = {
        k: v for k, v in research.items()
        if not k.startswith("_") and k != "sources" and v is not None
    }

    prompt = VERIFY_PROMPT.format(
        player_name=player["name"],
        claims_json=json.dumps(claims, indent=2),
    )

    result = await _call_perplexity(prompt)
    verification = _extract_json(result)

    if verification:
        player["verified"] = _merge_research_with_verification(research, verification)
    else:
        # If verification parse fails, use research as-is with medium confidence
        player["verified"] = _default_confidence(research)

    return player


def load_cache(cache_path: Path) -> dict:
    """Load the research cache from disk."""
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_cache(cache: dict, cache_path: Path):
    """Save the research cache to disk."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=2, default=str))


def _is_cache_fresh(entry: dict) -> bool:
    """Check if a cache entry is still within the max age."""
    cached_at = entry.get("_cached_at")
    if not cached_at:
        return False
    try:
        cached_time = datetime.fromisoformat(cached_at)
        age = datetime.now(timezone.utc) - cached_time
        return age.days < CACHE_MAX_AGE_DAYS
    except (ValueError, TypeError):
        return False


async def research_all(
    players: list[dict], team_name: str = "MLS", cache_path: Path | None = None, fresh: bool = False
) -> list[dict]:
    """Research all players, using cache when available."""
    import asyncio

    cache = {} if fresh else load_cache(cache_path) if cache_path else {}
    to_research = []
    cached_count = 0

    for p in players:
        name = p["name"]
        if not fresh and name in cache and _is_cache_fresh(cache[name]):
            p["research"] = cache[name]["research"]
            cached_count += 1
        else:
            to_research.append(p)

    if cached_count:
        print(f"   📦 Loaded {cached_count} players from research cache")

    if to_research:
        tasks = [research_player(p, team_name) for p in to_research]
        await asyncio.gather(*tasks)

    # Update cache with all research results
    if cache_path:
        for p in players:
            if "research" in p:
                cache[p["name"]] = {
                    "research": p["research"],
                    "_cached_at": datetime.now(timezone.utc).isoformat(),
                }
        save_cache(cache, cache_path)

    return players


async def verify_all(
    players: list[dict], cache_path: Path | None = None, fresh: bool = False
) -> list[dict]:
    """Verify all players, using cache when available."""
    import asyncio

    cache = {} if fresh else load_cache(cache_path) if cache_path else {}
    to_verify = []
    cached_count = 0

    for p in players:
        name = p["name"]
        if not fresh and name in cache and _is_cache_fresh(cache[name]) and "verified" in cache[name]:
            p["verified"] = cache[name]["verified"]
            cached_count += 1
        else:
            to_verify.append(p)

    if cached_count:
        print(f"   📦 Loaded {cached_count} players from verification cache")

    if to_verify:
        tasks = [verify_player(p) for p in to_verify]
        await asyncio.gather(*tasks)

    # Update cache with verification results
    if cache_path:
        for p in players:
            if "verified" in p:
                if p["name"] not in cache:
                    cache[p["name"]] = {}
                cache[p["name"]]["verified"] = p["verified"]
                cache[p["name"]]["_cached_at"] = datetime.now(timezone.utc).isoformat()
        save_cache(cache, cache_path)

    return players


def apply_corrections(players: list[dict], corrections_path: str) -> list[dict]:
    """
    Apply community corrections from a JSON file.
    Corrections override research data and are marked as high confidence.

    corrections.json format:
    {
        "Héctor Herrera": {
            "partner_instagram": "@corrected_handle",
            "partner_name": "Corrected Name"
        }
    }
    """
    from pathlib import Path
    path = Path(corrections_path)
    if not path.exists():
        return players

    corrections = json.loads(path.read_text())

    for player in players:
        name = player["name"]
        # Match on exact name OR partial name (e.g. "Ponce" matches "Ezequiel Ponce")
        matched_key = None
        if name in corrections:
            matched_key = name
        else:
            for corr_key in corrections:
                if corr_key.startswith("_"):
                    continue
                if corr_key in name or name in corr_key:
                    matched_key = corr_key
                    break

        if matched_key:
            for field, value in corrections[matched_key].items():
                if field.startswith("_"):
                    continue
                if "verified" in player:
                    player["verified"][field] = {
                        "value": value,
                        "confidence": "high",
                        "source": "community correction",
                    }
                if "research" in player:
                    player["research"][field] = value

    return players


def _merge_research_with_verification(research: dict, verification: dict) -> dict:
    """Merge original research with verification results."""
    verified_fields = verification.get("verified", {})
    merged = {}

    for key, value in research.items():
        if key.startswith("_"):
            continue
        if key in verified_fields:
            merged[key] = verified_fields[key]
        else:
            merged[key] = {"value": value, "confidence": "medium", "source": "unverified"}

    return merged


def _default_confidence(research: dict) -> dict:
    """Wrap all research fields in medium confidence."""
    return {
        k: {"value": v, "confidence": "medium", "source": "single-pass research"}
        for k, v in research.items()
        if not k.startswith("_")
    }


async def _call_perplexity(prompt: str) -> str:
    """Make a chat completion request to the Perplexity Sonar API."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PERPLEXITY_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": PERPLEXITY_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a sports research assistant. Return structured JSON when asked. Be thorough and cite your sources.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "return_images": True,
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()

    return data["choices"][0]["message"]["content"]


def _extract_json(text: str) -> dict | None:
    """Extract JSON from a text response that may contain markdown fences."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    import re
    match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding first [ to last ] (for JSON arrays)
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    # Try finding first { to last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    return None
