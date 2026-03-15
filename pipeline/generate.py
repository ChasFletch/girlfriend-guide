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
from pathlib import Path

# Add pipeline dir to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import TEAMS
from roster import fetch_roster, download_headshots, load_roster_override
from research import research_all, verify_all, apply_corrections
from caricature import generate_all_caricatures
from assemble import assemble_guide
from opponents import scout_opponent


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
    research_cache_path = team_dir / "research-cache.json"
    print(f"\n🔍 Step 3/6: Researching players via Perplexity...")
    if fresh:
        print(f"   🔄 Fresh mode — ignoring cache")
    players = await research_all(players, team_config["name"], research_cache_path, fresh)
    print(f"   ✅ Research complete for {len(players)} players")

    print(f"\n🔎 Verifying claims (second pass)...")
    players = await verify_all(players, research_cache_path, fresh)
    print(f"   ✅ Verification complete")

    # Apply community corrections
    corrections_path = team_dir / "corrections.json"
    players = apply_corrections(players, str(corrections_path))
    if corrections_path.exists():
        print(f"   📝 Applied community corrections from {corrections_path}")

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

    # --- Step 5: Assemble Guide ---
    print(f"\n📝 Step 5/6: Assembling guide via Claude...")
    template_path = team_dir / "template.html"
    output_path = team_dir / "index.html"

    await assemble_guide(
        players=players,
        team_config=team_config,
        match_info=match_info,
        template_path=template_path,
        output_path=output_path,
    )
    print(f"   ✅ Guide written to {output_path}")

    # --- Step 6: Scout Opponent ---
    print(f"\n🕵️ Step 6: Scouting 3 players from {opponent}...")
    try:
        scouted = await scout_opponent(opponent, base_dir)
        if scouted:
            print(f"   ✅ Scouted {len(scouted)} opponent players")
    except Exception as e:
        print(f"   ⚠️  Opponent scouting failed (non-fatal): {e}")

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
