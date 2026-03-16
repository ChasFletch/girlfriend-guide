#!/usr/bin/env python3
"""
Girlfriend Guide Generator — main orchestrator.

Usage:
    python generate.py --team houston-dynamo --opponent "Portland Timbers" --date 2026-03-14 --theme "Rodeo Night"

Or triggered by GitHub Actions with the same arguments.
"""
import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add pipeline dir to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import TEAMS
from roster import fetch_roster, download_headshots, load_roster_override
from research import research_all, verify_all, apply_corrections
from caricature import generate_all_caricatures
from assemble import assemble_guide
from opponents import scout_opponent

RESEARCH_DATA_MAX_AGE_DAYS = 7


def _load_research_data(team_dir: Path) -> dict | None:
    """
    Load Perplexity Computer's research-data.json if it exists and is fresh.
    Returns the parsed data dict, or None if missing/stale.
    """
    path = team_dir / "research-data.json"
    if not path.exists():
        return None

    data = json.loads(path.read_text())
    generated_at = data.get("_metadata", {}).get("generated_at")
    if not generated_at:
        return None

    try:
        gen_time = datetime.fromisoformat(generated_at)
        age = datetime.now(timezone.utc) - gen_time.astimezone(timezone.utc)
        if age.days >= RESEARCH_DATA_MAX_AGE_DAYS:
            return None
    except (ValueError, TypeError):
        return None

    return data


def _merge_research_data(players: list[dict], research_data: dict) -> list[dict]:
    """
    Merge Perplexity Computer's research into player dicts.
    Sets both 'research' and 'verified' keys so the assembly step
    can consume them the same way it consumes Sonar output.
    """
    pc_players = research_data.get("players", {})

    for player in players:
        name = player["name"]
        if name not in pc_players:
            continue

        pc = pc_players[name]

        # Copy social/relationship fields directly onto the player dict
        # (same level as roster-override fields — roster-override wins on conflicts)
        for key in ("player_instagram", "player_tiktok", "partner_name",
                     "partner_description", "partner_instagram", "partner_tiktok",
                     "relationship_status", "kids"):
            if pc.get(key) and not player.get(key):
                player[key] = pc[key]

        # Build research dict in the format the assembly step expects
        research = {k: v for k, v in pc.items() if not k.startswith("_")}
        player["research"] = research

        # Mark as verified (Perplexity Computer browser-verified this data)
        player["verified"] = {
            k: {"value": v, "confidence": pc.get("confidence", "high"), "source": "perplexity_computer"}
            for k, v in research.items()
            if k not in ("sources", "confidence", "last_verified")
        }

    return players


def _load_hot_content(team_dir: Path) -> dict | None:
    """Load weekly-hot-content.json if it exists."""
    path = team_dir / "weekly-hot-content.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


async def run(team_slug: str, opponent: str, match_date: str, theme: str = "", fresh: bool = False):
    """Run the full pipeline for a single team + match."""
    team_config = TEAMS.get(team_slug)
    if not team_config:
        print(f"❌ Unknown team: {team_slug}")
        print(f"   Available: {', '.join(TEAMS.keys())}")
        sys.exit(1)

    base_dir = Path(__file__).parent.parent
    team_dir = base_dir / team_slug
    build_dir = base_dir / ".build" / team_slug

    match_info = {
        "opponent": opponent,
        "date": match_date,
        "theme": theme,
    }

    # --- Step 1: Get Roster ---
    print(f"\n📋 Step 1/6: Fetching roster for {team_config['name']}...")

    override_path = team_dir / "roster-override.json"
    players = load_roster_override(override_path)

    if players:
        print(f"   ✅ Loaded {len(players)} players from roster override")
    else:
        players = await fetch_roster(team_config)
        print(f"   ✅ Scraped {len(players)} players from roster page")

    if not players:
        print("   ❌ No players found. Check the roster URL or add a roster-override.json")
        sys.exit(1)

    # --- Step 2: Download Headshots ---
    print(f"\n📸 Step 2/6: Downloading headshots...")
    headshot_dir = build_dir / "headshots"
    img_dir = team_dir / "img"
    players = await download_headshots(players, headshot_dir, img_dir)
    with_headshots = sum(1 for p in players if p.get("headshot_path"))
    print(f"   ✅ Downloaded {with_headshots}/{len(players)} headshots")

    # --- Step 3: Research + Verify ---
    # Check for Perplexity Computer's research-data.json first
    research_data = None if fresh else _load_research_data(team_dir)
    skip_sonar = False

    if research_data:
        pc_player_count = len(research_data.get("players", {}))
        gen_at = research_data["_metadata"]["generated_at"]
        print(f"\n🔍 Step 3/6: Loading research from Perplexity Computer ({pc_player_count} players, generated {gen_at})")
        players = _merge_research_data(players, research_data)
        skip_sonar = True
        print(f"   ✅ Merged Perplexity Computer research — skipping Sonar API")
    else:
        research_cache_path = team_dir / "research-cache.json"
        print(f"\n🔍 Step 3/6: Researching players via Perplexity Sonar (no fresh research-data.json found)...")
        if fresh:
            print(f"   🔄 Fresh mode — ignoring cache")
        players = await research_all(players, team_config["name"], research_cache_path, fresh)
        print(f"   ✅ Research complete for {len(players)} players")

        print(f"\n🔎 Verifying claims (second pass)...")
        players = await verify_all(players, research_cache_path, fresh)
        print(f"   ✅ Verification complete")

    # Apply community corrections (always runs, regardless of data source)
    corrections_path = team_dir / "corrections.json"
    players = apply_corrections(players, str(corrections_path))
    if corrections_path.exists():
        print(f"   📝 Applied community corrections from {corrections_path}")

    # Load hot content for assembly
    hot_content = _load_hot_content(team_dir)
    if hot_content:
        match_info["hot_content"] = hot_content
        hot_count = len(hot_content.get("hot_posts", []))
        print(f"   🔥 Loaded {hot_count} hot content items for this week")

    # --- Step 4: Generate Caricatures (only for players without headshots) ---
    players_needing_caricature = [p for p in players if not p.get("img_filename")]
    if players_needing_caricature:
        print(f"\n🎨 Step 4/6: Generating caricatures for {len(players_needing_caricature)} players without headshots...")
        caricature_dir = build_dir / "caricatures"
        players_needing_caricature = await generate_all_caricatures(
            players_needing_caricature, team_config, caricature_dir, img_dir, fresh
        )
        # Merge caricature data back into main players list
        caricature_map = {p["name"]: p for p in players_needing_caricature}
        for p in players:
            if p["name"] in caricature_map:
                p.update(caricature_map[p["name"]])
        with_caricatures = sum(1 for p in players if p.get("caricature_path"))
        print(f"   ✅ Generated {with_caricatures}/{len(players_needing_caricature)} caricatures")
    else:
        print(f"\n🎨 Step 4/6: All players have headshots — skipping caricatures")

    # --- Step 5: Scout Opponent ---
    print(f"\n🕵️ Step 5/6: Scouting 3 players from {opponent}...")
    opponent_players = []
    try:
        opponent_players = await scout_opponent(opponent, base_dir)
        if opponent_players:
            print(f"   ✅ Scouted {len(opponent_players)} opponent players")
        else:
            print(f"   ⚠️  No opponent players found")
    except Exception as e:
        print(f"   ⚠️  Opponent scouting failed (non-fatal): {e}")

    # --- Step 6: Assemble Guide ---
    print(f"\n📝 Step 6/6: Assembling guide via Claude...")
    template_path = team_dir / "template.html"
    output_path = team_dir / "index.html"

    await assemble_guide(
        players=players,
        team_config=team_config,
        match_info=match_info,
        template_path=template_path,
        output_path=output_path,
        opponent_players=opponent_players,
        hot_content=hot_content,
    )
    print(f"   ✅ Guide written to {output_path}")

    # --- Save build artifacts for debugging ---
    artifacts_path = build_dir / "pipeline-output.json"
    _save_artifacts(players, artifacts_path)
    print(f"\n💾 Build artifacts saved to {artifacts_path}")

    print(f"\n🎉 Done! Guide ready at: {output_path}")
    print(f"   Push to GitHub and Netlify will auto-deploy to girlfriendguide.gg")


def _save_artifacts(players: list[dict], path: Path):
    """Save pipeline output for debugging (without binary image data)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = []
    for p in players:
        entry = {k: v for k, v in p.items() if k not in ("caricature_b64", "headshot_b64")}
        cleaned.append(entry)
    path.write_text(json.dumps(cleaned, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(description="Generate a Girlfriend Guide")
    parser.add_argument("--team", required=True, help="Team slug (e.g. houston-dynamo)")
    parser.add_argument("--opponent", required=True, help="Opponent team name")
    parser.add_argument("--date", required=True, help="Match date (YYYY-MM-DD)")
    parser.add_argument("--theme", default="", help="Match theme (e.g. 'Rodeo Night')")
    parser.add_argument("--fresh", action="store_true", help="Skip cache and re-research all players")
    args = parser.parse_args()

    asyncio.run(run(args.team, args.opponent, args.date, args.theme, args.fresh))


if __name__ == "__main__":
    main()
