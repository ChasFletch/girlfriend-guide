# Girlfriend Guide — Project Bible

## What This Is

A fun, sassy cheat-sheet to a soccer team's roster for people who are here for the vibe, not the score. Think of it as the roster explained by your best friend who happens to know all the tea.

**This is NOT a sports guide.** It's a social/lifestyle/relationship guide that happens to be about soccer players.

## Brand Positioning

**Brand mantra:** "Here for the vibe, not the score."

The name "Girlfriend" is the *voice* — group chat energy, your girls, insider gossip. It is NOT the audience definition. Our audience is a mindset, not a gender: anyone at the match for reasons beyond the scoreline. Partners, friends who came for the outing, casual fans who care about players as people, die-hard fans who want the gossip layer.

**Five brand commandments (informed by the Sky Sports Halo failure):**
1. No hierarchical framing — we are not "sports lite," we're a different product
2. No aesthetic segregation — pink is an accent color, not a theme
3. Athletes as celebrities — not male athletes repackaged for a female audience
4. Authentic voice only — the tone comes from real people, not a slang mood board
5. Never assume the audience isn't already watching

## The Soul of the Product

People reacted to the prototype because it felt like a group chat, not a sports broadcast. The content that made it viral was:

- **Instagram links for every player and their partner** — this is the #1 feature
- **Relationship tea** — who's dating who, how they met, cute couple content
- **The Inner Circle** — partner spotlights with names, descriptions, their own social links. Partners are featured as independent people (lead with who they ARE, relationship is context not identity)
- **Personality over stats** — hobbies, viral moments, funny stories
- **Short, punchy, emoji-heavy writing** — "From Houston. Academy kid. Living the dream. 🏡➡️⚽"

## Content Priorities (in order)

1. **Social media links** — Instagram for players AND partners. TikTok where available. If someone has a handle, it MUST be in the guide.
2. **Relationship info** — Partner name, how they met, kids, cute details
3. **The tea** — Personality, lifestyle, viral moments, wholesome stories
4. **Brief sports context** — ONE sentence max. "He's the goal scorer." "Fastest player on the team." That's it.

## Roster Rules

- **Only feature the starting goalkeeper.** Backup GKs aren't relevant to our audience until they start. Remove them from the roster override.

## What We Do NOT Want

- Paragraphs about career statistics or transfer history
- Sports journalism voice ("He captained EC Vitória in all 33 matches...")
- Missing social links when we have the data
- Missing partner sections when we have the data
- Formal, dry, stats-heavy player bios

## Tone Examples

**Good (from the prototype):**
> 🇺🇸 From Humble, TX. Homegrown player — came up through the Dynamo academy. Signed his first contract in December 2025. Local kid living the dream. 🏡➡️⚽

> 🇦🇷 The goal machine. Four continents before becoming Houston's most expensive signing ever. 💰

**Bad (from a failed generation):**
> He captained EC Vitória in all 33 matches during his 2025 loan, scoring a career-high 4 league goals including a game-winner. He was also part of Botafogo's history-making squad that won the Copa Libertadores for the first time in 2024.

## Architecture

The pipeline (`pipeline/`) runs via GitHub Actions:

1. **Roster** — Load from `roster-override.json` (preferred) or scrape MLS site
2. **Headshots** — Download player photos from MLS CDN, embed as base64
3. **Research** — Perplexity API to find social handles, relationship info, personality details
4. **Verify** — Second Perplexity pass to fact-check claims
5. **Caricatures** — Gemini generates cartoon versions ONLY for players without real headshots (fallback only)
6. **Assembly** — Claude generates the final HTML guide from research + template

### Key Files

- `{team}/roster-override.json` — Seed data: headshot URLs, Instagram handles, partner info. This is the source of truth for social links since Perplexity often can't find them.
- `{team}/template.html` — The original prototype. Claude uses this for structure/CSS/tone reference.
- `{team}/index.html` — The generated output. This is what gets deployed.
- `pipeline/config.py` — All prompts (research, verify, assembly) live here.
- `pipeline/assemble.py` — Sends data to Claude and post-processes the HTML.

### Common Failure Modes

- **No images**: Roster override missing `headshot_url` fields, or headshot download fails
- **No social links**: Roster override missing `player_instagram`/`partner_instagram`, AND Perplexity failed to find them
- **Wrong tone**: Assembly prompt not specific enough about girlfriend-guide voice vs sports journalism
- **Template truncation**: `assemble.py` truncates the template — if too aggressive, Claude loses the social link HTML patterns

## Adding a New Team

1. Create `{team-slug}/` directory
2. Add team config to `TEAMS` in `pipeline/config.py`
3. Create `roster-override.json` with player names, jersey numbers, positions, headshot URLs, and Instagram handles
4. Optionally create a `template.html` prototype for tone/style reference
5. Run the pipeline: `python pipeline/generate.py --team {team-slug} --opponent "Opponent Name" --date YYYY-MM-DD`

## Guiding Principle

If someone would screenshot it and send it to their group chat, we're doing it right. If it reads like ESPN, we've failed.
