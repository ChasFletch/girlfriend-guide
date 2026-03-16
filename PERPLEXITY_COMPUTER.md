# Perplexity Computer — Research Partner for Girlfriend Guide

## Who I Am

I'm **Perplexity Computer**, running inside Charles's Perplexity account. I have access to:
- The `ChasFletch/girlfriend-guide` GitHub repo (read + write via `gh` CLI)
- Live web browsing (I can visit actual Instagram, TikTok, and any public webpage)
- Multi-pass parallel web research (dozens of searches simultaneously)
- Scheduled recurring tasks (cron-style, runs on a weekly cadence)
- File creation and structured data output

I **cannot** run the Python pipeline, call the Perplexity Sonar API, call the Claude API, or trigger GitHub Actions. That's Claude's domain.

## Why This Document Exists

The Sonar API research pass (Steps 3-4 of the pipeline) is producing hallucinated social media handles and fabricated partner names at a high rate. Out of 23 players in the Houston research cache, **15 had fabricated data** that the verification pass correctly nulled — but this leaves the guide stripped of its most important content (social links, relationship tea, personality details).

Charles and I agreed that **I should handle all player research**, and Claude should continue handling **pipeline orchestration, HTML assembly, and deployment**. This document defines the interface between us.

## The Division of Labor

### Perplexity Computer Does:
1. **Weekly roster verification** — Pull the official MLS roster page, cross-reference with injury reports, flag any changes (trades, injuries, new signings)
2. **Deep player research** — Multi-pass search for every player: verified Instagram handles, TikTok accounts, relationship status, partner names, partner social handles, fun facts, personality content
3. **Weekly "hot content" scan** — Browse player and WAG Instagram/TikTok profiles to find the week's best posts, new announcements, fresh tea
4. **Opposition research** — For each upcoming home game, research 3 players from the opposing team (prioritizing players with active social media AND partners with active social media)
5. **Data output** — Write all findings to structured JSON files in the repo that the pipeline can consume directly

### Claude Does:
1. **Pipeline orchestration** — `generate.py` and all supporting modules
2. **HTML assembly** — Using the template + research data to generate the final guide
3. **Caricature generation** — Gemini/Perplexity image API for players without headshots
4. **GitHub Actions** — Automated Monday morning runs
5. **Corrections processing** — Applying community corrections from `corrections.json`
6. **Deployment** — Commit, push, Netlify auto-deploy

## Data Interface: How We Talk

### File: `{team}/research-data.json`

This is the new primary research file that Perplexity Computer writes and the pipeline reads. It replaces Sonar's research output entirely.

**Structure:**
```json
{
  "_metadata": {
    "generated_by": "perplexity_computer",
    "generated_at": "2026-03-16T15:30:00-05:00",
    "team": "houston-dynamo",
    "season": "2026"
  },
  "players": {
    "Mateusz Bogusz": {
      "full_name": "Mateusz Piotr Bogusz",
      "jersey_number": 19,
      "position": "Forward/Midfielder",
      "age": 24,
      "nationality": "Polish",
      "nationality_flag": "🇵🇱",
      "hometown": "Ruda Śląska, Poland",
      "player_instagram": "@x_bogus",
      "player_instagram_url": "https://www.instagram.com/x_bogus/",
      "player_tiktok": null,
      "player_tiktok_url": null,
      "relationship_status": "married",
      "partner_name": "Wiktoria Wychowska",
      "partner_description": "Wife, Pilates instructor, owns @no13.pilates. 24K IG followers. Based in Houston TX / Katowice, Poland.",
      "partner_instagram": "@wiktoria.wychowska",
      "partner_instagram_url": "https://www.instagram.com/wiktoria.wychowska/",
      "partner_tiktok": "@wiktoria.wychowska",
      "partner_tiktok_url": "https://www.tiktok.com/@wiktoria.wychowska",
      "kids": "Baby girl expected Feb 2026 — 'She's on her way' posted Jan 7. No public birth announcement as of mid-March.",
      "fun_facts": [
        "Signed as Designated Player from Cruz Azul (Mexico) in Jan 2026",
        "Former LAFC fan favorite — scored 18 goals in 2024",
        "Polish international",
        "Wiktoria runs a Pilates studio and has 24K IG followers"
      ],
      "tea": "Wiktoria posted 'She's on her way 💝' on Jan 7 with ultrasound photos — baby girl due Feb 2026. Her last post (Mar 3) was captioned '02.2026 💝' still showing a pregnant belly. Baby has likely arrived but they're keeping it private for now. She's a certified Pilates instructor who runs her own studio. The couple moved to Houston from Mexico after his transfer.",
      "one_liner_sports": "Houston's most expensive signing ever — the creative spark who makes goals happen.",
      "confidence": "high",
      "last_verified": "2026-03-14",
      "sources": [
        "https://www.instagram.com/x_bogus/",
        "https://www.instagram.com/wiktoria.wychowska/",
        "https://www.houstondynamofc.com/players/mateusz-bogusz/"
      ]
    }
  }
}
```

### File: `{team}/weekly-hot-content.json`

Written by Perplexity Computer before each home game. Contains the freshest social content for Claude to weave into that week's guide.

```json
{
  "_metadata": {
    "generated_at": "2026-03-20T09:00:00-05:00",
    "for_match": "houston-dynamo vs FC Dallas",
    "match_date": "2026-03-22"
  },
  "hot_posts": [
    {
      "player_or_partner": "Wiktoria Wychowska",
      "platform": "instagram",
      "handle": "@wiktoria.wychowska",
      "post_date": "2026-03-18",
      "description": "Posted first photo with newborn baby girl — 4,200 likes, 180 comments",
      "caption_excerpt": "Welcome to the world, little one 💝",
      "why_its_hot": "Baby announcement — the biggest personal news on the roster this week",
      "suggested_tea": "The Bogusz baby girl has arrived! Wiktoria finally shared the news this week and the comments section is flooded with Dynamo WAGs congratulating them."
    }
  ],
  "roster_changes": [
    {
      "type": "injury",
      "player": "Nelson Quiñones",
      "detail": "Lower body injury — not expected to play. Exclude from guide or mark as injured."
    }
  ]
}
```

### File: `data/opponents.json`

Shared database. Perplexity Computer adds new opponent players; Claude's pipeline reads them for the "Know the Enemy" section.

**The pipeline should check this file FIRST before calling Sonar for opponent research.** If a player already exists in the database with high-confidence data, skip the Sonar call.

## Proposed Weekly Workflow

### Monday (automated via Perplexity Computer recurring task)
1. Check upcoming home games for all 3 Texas teams this week
2. For each team with a home game:
   - Verify roster against official MLS page + injury reports
   - Scan all player/WAG profiles for hot content since last scan
   - Research 3 opponent players (check opponents.json first, skip known players)
   - Write `research-data.json` and `weekly-hot-content.json`
   - Commit to repo

### Monday-Wednesday (automated via GitHub Actions, Claude's pipeline)
1. Read `research-data.json` instead of calling Sonar
2. Read `weekly-hot-content.json` for fresh material
3. Assemble guide via Claude
4. Generate caricatures if needed
5. Commit and deploy to Netlify

### Match Day (manual, Charles posts to Facebook groups)
1. Share the link in Houston Dynamo FC Fans / Austin FC / FC Dallas groups
2. Monitor comments for corrections → add to `corrections.json`

## Changes Claude Should Make to the Pipeline

### 1. Read `research-data.json` as primary source (new)
In `generate.py`, after loading `roster-override.json`, check for `{team}/research-data.json`. If it exists and is fresh (< 7 days old), merge its player data into the roster and **skip the Sonar research + verify steps entirely**.

```python
# Pseudocode for the change
research_data_path = team_dir / "research-data.json"
if research_data_path.exists():
    research_data = json.loads(research_data_path.read_text())
    age_days = (now - parse(research_data["_metadata"]["generated_at"])).days
    if age_days < 7:
        # Merge research into players — skip Sonar
        for player in players:
            if player["name"] in research_data["players"]:
                player["research"] = research_data["players"][player["name"]]
                player["verified"] = player["research"]  # Already verified by PC
        skip_sonar = True
```

### 2. Read `weekly-hot-content.json` (new)
Pass hot content data to the assembly prompt so Claude can weave in fresh material:
```python
hot_content_path = team_dir / "weekly-hot-content.json"
if hot_content_path.exists():
    hot_content = json.loads(hot_content_path.read_text())
    # Add to assembly prompt context
```

### 3. Respect injury flags
If `weekly-hot-content.json` flags a player as injured/unavailable, either exclude them from the guide or add a visual indicator (the template already has a `.suspended` card class).

### 4. Keep Sonar as fallback
Don't delete the Sonar research code — it's a useful fallback if Perplexity Computer's data is missing or stale. Just don't use it as the primary source.

### 5. Stop hallucinating in opponent scouting
The current `opponents.py` asks Sonar for "3 players with Instagram AND partner Instagram." Sonar fabricates handles to satisfy this requirement. Change the prompt to say "it's OK to return players without social links" and let Perplexity Computer fill in the real handles later.

## Known Data Corrections Needed (as of 2026-03-16)

These should go into `roster-override.json` and/or `corrections.json`:

| Player | Field | Current (Wrong) | Correct | Source |
|--------|-------|-----------------|---------|--------|
| Jonathan Bond | player_instagram | (missing or wrong) | @jonathanbond23 | Verified via IG profile |
| Jonathan Bond | partner_name | (missing) | Isy Bella Bond | Verified via IG profile |
| Jonathan Bond | partner_instagram | (missing) | @isybellabond | Verified via IG profile |
| Erik Sviatchenko | partner_name | (was "Tina") | Anne Sviatchenko | His own IG posts confirm |
| Erik Sviatchenko | partner_instagram | (missing) | @annesviat | His own IG posts confirm |
| Héctor Herrera | relationship_status | partner | divorced (2025) | TUDN, Soy Fútbol confirmed |
| Héctor Herrera | partner_name | Shan Mayo | Ex-wife: Shantal Mayo | Public divorce 2025 |
| Héctor Herrera | player_tiktok | (missing) | @hherrera16 | Verified TikTok profile |
| Artur | partner_name | (was "Raíssa Reis") | Rachel Lima | Dynamo sustainability video, IG |
| Artur | partner_instagram | (was wrong) | @rachel.limaaa | Verified via IG profile |
| Duane Holmes | partner_name | (was "McKenna") | Brooke Holmes | Her IG bio: "Wife + Mama" |
| Duane Holmes | partner_instagram | (was wrong) | @brookesavannah2 | Verified via IG profile |
| Agustín Bouzat | partner_name | (was "Lucía Pérez") | Fiorella Curutchet | Multiple sources confirm |
| Agustín Bouzat | partner_instagram | (was wrong) | @fiorecurutchet | Verified via IG profile |
| Nelson Quiñones | partner_name | Fiorella Curutchet | Unknown (copy-paste error from Bouzat) | — |
| Nelson Quiñones | partner_instagram | @fiorecurutchet | Unknown | — |
| Ezequiel Ponce | partner_name | Martina Madeo | Needs verification — our research says Martina Ponce Soto-Aguilar (@maartinaponce), fan comment says current handle is wrong | Community feedback |
| Aliyu Ibrahim | partner_tiktok | @ibrahmaliyu | Should be player_tiktok (this is HIS TikTok, not a partner's) | Verified via TikTok profile |
| Mateusz Bogusz | player_instagram | (was wrong in cache) | @x_bogus | Verified via IG profile |
| Wiktoria Wychowska | partner_tiktok | (missing) | @wiktoria.wychowska | Verified TikTok profile |
| Preslee Clark (Ennali) | partner_tiktok | (missing in some places) | @presleeclarkartistry | Verified TikTok profile |

## Tone Reminder (for Claude's Assembly Prompt)

The project bible (CLAUDE.md) nails the tone, but here's the key insight from the Facebook reception: **the audience wants to feel like they're in on something**, not like they're reading a sports reference guide. The comments that lit up were:
- "Dude, my wife LOVED this"
- "this is iconic and informative!"
- "This is actually really good!"

The guide works when it feels like a group chat, not a database. Fresh weekly content (hot posts, baby announcements, couple milestones) is what keeps people coming back. Static bios get stale after one read.

## Questions for Claude

1. Should `research-data.json` completely replace `roster-override.json`, or should they coexist? My suggestion: coexist. Override is the "seed" data Charles manually curates. Research-data is the "enriched" version I generate weekly. Pipeline merges both, with override winning on conflicts.

2. The current corrections.json has "Ponce" as the key, not "Ezequiel Ponce" — is the pipeline matching on partial names or full names?

3. Is there a preference for how I commit to the repo? I can push directly to `main` or create PRs. Direct push is simpler for data files; PRs are better if Claude wants to review.

4. The repo description on GitHub says "matchday guides for sports fans" — should I update it to something like "matchday guides for people who got dragged to the game"?
