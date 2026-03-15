"""
Configuration for the Girlfriend Guide generation pipeline.
API keys loaded from environment variables (set in GitHub Secrets for CI).
"""
import os

# --- API Keys (from environment / GitHub Secrets) ---
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# --- API Endpoints ---
PERPLEXITY_BASE_URL = "https://api.perplexity.ai"
PERPLEXITY_MODEL = "sonar-pro"

GEMINI_MODEL = "gemini-2.5-flash-image"

CLAUDE_MODEL = "claude-sonnet-4-6"

# --- Team Configs ---
# Each team the pipeline can generate a guide for.
# Add new teams here as we expand.
TEAMS = {
    "houston-dynamo": {
        "name": "Houston Dynamo FC",
        "slug": "houston-dynamo",
        "mls_roster_url": "https://www.houstondynamofc.com/roster",
        "primary_color": "#F68B1F",
        "secondary_color": "#101820",
        "jersey_colors": "orange and white",
    },
    "fc-dallas": {
        "name": "FC Dallas",
        "slug": "fc-dallas",
        "mls_roster_url": "https://www.fcdallas.com/roster",
        "primary_color": "#BF0D3E",
        "secondary_color": "#002D72",
        "jersey_colors": "red and white",
    },
    "austin-fc": {
        "name": "Austin FC",
        "slug": "austin-fc",
        "mls_roster_url": "https://www.austinfc.com/roster",
        "primary_color": "#00B140",
        "secondary_color": "#000000",
        "jersey_colors": "verde (green) and black",
    },
}

# --- Prompt Templates ---

RESEARCH_PROMPT = """Research {team_name} soccer player {player_name} (#{jersey_number}, {position}).

THIS IS FOR A "GIRLFRIEND GUIDE" — a fun guide for partners/friends who got dragged to the game.
The #1 priority is SOCIAL MEDIA HANDLES and RELATIONSHIP INFO, not career stats.

RESEARCH PRIORITIES (in order of importance):
1. Instagram handle — search "{player_name} instagram", check the team's tagged photos, player bios
2. Relationship status & partner/spouse name — search "{player_name} wife", "{player_name} girlfriend"
3. Partner's Instagram handle — search the partner's name on Instagram once you find it
4. Partner's TikTok — if they have one
5. Fun personality details — hobbies, pets, style, viral moments, wholesome content
6. Brief background — age, hometown, nationality (1-2 sentences max of career info)

Find and return ALL of the following in JSON format:
{{
  "full_name": "...",
  "nickname": "...",
  "age": ...,
  "hometown": "city, state/country",
  "nationality": "...",
  "nationality_flag": "emoji flag e.g. 🇺🇸 🇦🇷 🇧🇷",
  "position": "...",
  "jersey_number": ...,
  "player_instagram": "@handle (REQUIRED — search hard for this)",
  "player_tiktok": "@handle or null",
  "relationship_status": "single / dating / married / engaged",
  "partner_name": "...",
  "partner_description": "brief — e.g. 'model, 12K followers' or 'dental hygienist from Texas'",
  "partner_instagram": "@handle",
  "partner_tiktok": "@handle or null",
  "kids": "e.g. 'Two kids: Leon and Rebeca' or null",
  "fun_facts": ["personality/lifestyle facts, NOT career stats"],
  "tea": "lighthearted gossip — how they met their partner, viral moments, funny interviews, wholesome family content, unexpected hobbies",
  "one_liner_sports": "ONE sentence max of what they do on the field",
  "sources": ["url1", "url2"]
}}

IMPORTANT SEARCH STRATEGIES for finding Instagram handles:
- Search "{player_name} instagram" directly
- Check the team's official Instagram tagged/following list
- Look at the player's profile on transfermarkt.com (often has social links)
- Search "{player_name} {team_name} wife instagram" or "girlfriend instagram"
- Check WAG fan accounts and team WAG group photos on Instagram

TONE RULES:
- Keep it POSITIVE and FUN. These players will likely see this guide.
- Focus on personality, relationships, lifestyle — NOT career statistics.
- "Tea" means fun storylines — how they met their partner, viral moments, funny interviews,
  wholesome family content, unexpected hobbies. NOT scandals or hardships.
- When in doubt, ask: "Would the player smile if they read this?" If not, leave it out.

Be thorough with social media research. Career stats are the LEAST important thing here.
If you can't verify something, set it to null rather than guessing."""

VERIFY_PROMPT = """Verify these claims about soccer player {player_name}:

{claims_json}

For each claim, search for confirming or contradicting evidence.
Return JSON:
{{
  "player_name": "...",
  "verified": {{
    "field_name": {{
      "value": "the verified value or null if unverifiable",
      "confidence": "high" | "medium" | "low",
      "source": "url or description"
    }}
  }}
}}

Flag anything that conflicts with the original claims."""

CARICATURE_PROMPT = """Transform this soccer player photo into a fun cartoon caricature.
Exaggerated features, bold outlines, vibrant colors, playful confident expression.
Keep the likeness clearly recognizable — this should look like THIS specific person.
They're wearing a {jersey_colors} soccer jersey with #{jersey_number} on it.
Clean white background. Sports card portrait style. Upper body only."""

ASSEMBLY_PROMPT = """You are building a "Girlfriend Guide" — a fun, sassy cheat-sheet to a soccer
team's roster for people who got dragged to the game by their partner. Think of it as explaining
the roster to your best friend who doesn't care about soccer but DOES care about the tea.

Given the verified player research data (JSON), generate a complete single-file HTML page that
matches the template's structure and CSS EXACTLY.

## CONTENT PRIORITIES (this is what the audience cares about, in order):

1. **Social media links** — Instagram for EVERY player that has one, Instagram AND TikTok for
   partners/WAGs. These go in a `<div class="card-links">` section at the bottom of each card.
   Use the exact CSS classes from the template: `ig-player`, `ig-partner`, `tiktok`.
   THIS IS THE MOST IMPORTANT THING. If a player or partner has an Instagram handle in the data,
   it MUST appear as a clickable link.

2. **Relationship info** — Who are they dating/married to? Put this in a `couple-callout` div
   with the 🎀 ribbon. Include partner's name, brief description, and kids if known.
   Format: `<div class="couple-callout"><div class="couple-label">🎀 His Person</div>...</div>`

3. **The tea** — Personality, lifestyle, how they met their partner, viral moments, funny stories,
   wholesome family content. This is the MAIN text of each card. Keep it short, punchy, and fun.
   Use emojis. Write like you're texting your group chat, not writing a sports article.

4. **Brief sports context** — ONE sentence max about what they do on the field. Just enough so
   someone can say "oh that's the fast one" or "he's the goal scorer." Do NOT write paragraphs
   about career statistics, transfer history, or match performance.

## CARD STRUCTURE (follow the template exactly):
- Player avatar with headshot image (use headshot_url from player data as img src)
- Name, position, number, age
- Flag emoji for nationality
- "the-tea" paragraph — SHORT, personality-focused, emoji-heavy
- "couple-callout" section if they have a partner
- "card-links" section with ALL available social links

## TONE:
- Fun, warm, a little sassy — like a group chat, NOT a sports broadcast
- Use emojis liberally (🎀 🔥 😭 👀 💕 🇺🇸 etc.)
- Short punchy sentences. "From Houston. Academy kid. Living the dream. 🏡➡️⚽"
- Keep it POSITIVE — players will see this and hopefully repost it
- Career stats are BORING for this audience. Personality and relationships are everything.

## WHAT NOT TO DO:
- Do NOT write multiple paragraphs about someone's career or transfer history
- Do NOT lead with sports achievements — lead with personality or relationship status
- Do NOT omit social links that exist in the player data
- Do NOT skip the couple-callout section for players who have partner info
- Do NOT write in a formal sports journalism voice

Team: {team_name}
Match: {match_description}
Date: {match_date}

Player data:
{players_json}

Template HTML for reference (match the structure, CSS, and social link patterns EXACTLY):
{template_html}
"""
