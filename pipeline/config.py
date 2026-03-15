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

Find and return ALL of the following in JSON format:
{{
  "full_name": "...",
  "nickname": "...",
  "age": ...,
  "hometown": "city, state/country",
  "college": "...",
  "nationality": "...",
  "position": "...",
  "jersey_number": ...,
  "relationship_status": "single / dating / married / engaged",
  "partner_name": "...",
  "partner_instagram": "@handle",
  "fun_facts": ["...", "..."],
  "tea": "any lighthearted gossip or interesting storylines",
  "sources": ["url1", "url2"]
}}

TONE RULES — follow these carefully:
- Keep it POSITIVE and FUN. These players will likely see this guide.
- Focus on what makes each player cool, interesting, or lovable.
- Relationship info should celebrate who they're with, not dwell on past breakups or divorces.
  If someone is divorced or went through a breakup, don't mention it unless it's genuinely
  breaking news (within the last 2 weeks). Old heartbreak is not "tea" — it's just sad.
- "Tea" means fun, lighthearted storylines — viral moments, funny interviews, wholesome
  family content, unexpected hobbies, fan-favorite celebrations. NOT scandals, legal trouble,
  or personal hardships unless the player has spoken about it publicly and positively.
- When in doubt, ask: "Would the player smile if they read this?" If not, leave it out.

Be thorough. Check Instagram, team pages, WAG accounts, local sports media.
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

ASSEMBLY_PROMPT = """You are building a Girlfriend Guide — a fun, sassy guide to a soccer team's
roster for people who got dragged to the game by their partner.

Given the following verified player research data (JSON), generate a complete single-file HTML page
in the exact style of the template provided. The guide should:

- Lead with the big-name players, then rising stars, then the rest
- Each player card includes: name, number, position, hometown, age, relationship status,
  partner info (with IG link if available), fun facts, and "the tea"
- Use qualifiers ("reportedly", "per team sources") for medium-confidence claims
- OMIT any low-confidence claims entirely
- Tone: fun, warm, informative — like explaining the roster to your best friend
- Keep it POSITIVE. Players will see this. Lead with what makes each person interesting,
  cool, or lovable. Celebrate current relationships — don't mention past breakups or
  divorces unless it's genuinely recent news. "Tea" should make someone smile, not cringe.
  Ask yourself: "Would this player repost this?" If not, rewrite it.
- Include player headshot images using the headshot_url from the player data (as <img> tags)
- Include caricature images where available (provided as base64 data URIs or file paths)
- Include Instagram links for players and their partners where available from the research data
- Include any TikTok or other social media links from the research data
- Social links should use the same styling as the template (with icons/badges)

Team: {team_name}
Match: {match_description}
Date: {match_date}

Player data:
{players_json}

Template HTML for reference (match the structure and CSS):
{template_html}
"""
