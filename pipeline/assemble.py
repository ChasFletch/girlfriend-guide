"""
Assembly module — uses Claude API to generate the final HTML guide
from verified research data, caricature images, and a template.
"""
import json
from pathlib import Path
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, ASSEMBLY_PROMPT

# Use async client since this function is awaited from generate.py
_async_client = None


def _get_client():
    global _async_client
    if _async_client is None:
        _async_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    return _async_client


async def assemble_guide(
    players: list[dict],
    team_config: dict,
    match_info: dict,
    template_path: Path,
    output_path: Path,
) -> Path:
    """
    Send all player data + caricatures to Claude to assemble the final guide.

    Args:
        players: list of player dicts with verified research and caricature data
        team_config: team configuration from config.py
        match_info: dict with 'opponent', 'date', 'theme' (e.g. "Rodeo Night")
        template_path: path to an existing guide HTML to use as style reference
        output_path: where to write the generated guide HTML

    Returns:
        Path to the generated HTML file
    """
    # Read the template for style reference
    template_html = ""
    if template_path.exists():
        template_html = template_path.read_text()
        # Truncate if too long — Claude just needs the structure, not all content
        if len(template_html) > 30000:
            template_html = template_html[:30000] + "\n<!-- ... truncated for brevity ... -->"

    # Prepare player data for Claude (strip binary data, keep essentials)
    players_for_prompt = _prepare_player_data(players)

    match_description = f"{match_info.get('theme', '')} vs {match_info['opponent']}".strip()

    prompt = ASSEMBLY_PROMPT.format(
        team_name=team_config["name"],
        match_description=match_description,
        match_date=match_info["date"],
        players_json=json.dumps(players_for_prompt, indent=2),
        template_html=template_html,
    )

    # Call Claude with streaming (required for large max_tokens / long requests)
    client = _get_client()
    full_text = ""
    async with client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=32000,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        async for text in stream.text_stream:
            full_text += text

    html_content = _extract_html(full_text)

    if not html_content or len(html_content.strip()) < 100:
        raise RuntimeError(
            f"Assembly failed: Claude returned empty or too-short HTML ({len(html_content)} chars). "
            "Refusing to overwrite existing guide."
        )

    # Replace image references with local paths (img/ directory)
    html_content = _rewrite_image_paths(html_content, players)

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content)

    return output_path


def _prepare_player_data(players: list[dict]) -> list[dict]:
    """Strip large binary fields, keep what Claude needs for writing."""
    cleaned = []
    for p in players:
        entry = {
            "name": p["name"],
            "jersey_number": p.get("jersey_number"),
            "position": p.get("position"),
            "has_caricature": p.get("caricature_path") is not None,
            "has_headshot": p.get("img_filename") is not None or p.get("headshot_path") is not None,
            "img_src": f"img/{p['img_filename']}" if p.get("img_filename") else None,
            "caricature_src": f"img/{_slugify(p['name'])}-caricature.png" if p.get("caricature_path") else None,
        }

        # Pass through social/relationship fields from roster override
        for key in ("player_instagram", "player_tiktok", "partner_name",
                     "partner_description", "partner_instagram", "partner_tiktok"):
            if p.get(key):
                entry[key] = p[key]

        # Add verified research (with confidence levels)
        if "verified" in p:
            entry["research"] = {
                k: v for k, v in p["verified"].items()
                if not k.startswith("_")
            }
        elif "research" in p:
            entry["research"] = {
                k: v for k, v in p["research"].items()
                if not k.startswith("_")
            }

        cleaned.append(entry)

    return cleaned


def _extract_html(text: str) -> str:
    """Extract HTML from Claude's response, stripping markdown fences if present."""
    if "```html" in text:
        start = text.index("```html") + 7
        end = text.rindex("```")
        return text[start:end].strip()
    if "<!DOCTYPE" in text:
        start = text.index("<!DOCTYPE")
        return text[start:].strip()
    if "<html" in text:
        start = text.index("<html")
        return text[start:].strip()
    return text


def _rewrite_image_paths(html: str, players: list[dict]) -> str:
    """
    Replace any external headshot URLs or placeholder references with
    local img/ paths. Claude should already use img_src from the data,
    but this catches any stragglers.
    """
    for player in players:
        img_filename = player.get("img_filename")
        headshot_url = player.get("headshot_url")

        # Replace external MLS URLs with local paths
        if img_filename and headshot_url and headshot_url in html:
            html = html.replace(headshot_url, f"img/{img_filename}")

        # Replace caricature placeholders with local paths
        slug = _slugify(player["name"])
        caricature_path = player.get("caricature_path")
        if caricature_path:
            local_caricature = f"img/{slug}-caricature.png"
            for pattern in [
                f'src="{slug}-caricature.png"',
                f"src='{slug}-caricature.png'",
                f'src="caricature-{slug}.png"',
                f"src='caricature-{slug}.png'",
                f'src="{slug}.png"',
            ]:
                if pattern in html:
                    html = html.replace(pattern, f'src="{local_caricature}"')

    return html


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace(".", "").replace("é", "e").replace("ú", "u")
