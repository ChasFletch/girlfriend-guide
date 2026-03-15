"""
Caricature generator — uses Google Gemini 2.5 Flash Image API
to transform player headshots into cartoon caricatures.
"""
import asyncio
import base64
from pathlib import Path
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL, CARICATURE_PROMPT


# Initialize Gemini client
_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


async def generate_caricature(player: dict, team_config: dict, output_dir: Path, fresh: bool = False) -> dict:
    """
    Generate a caricature from a player's headshot photo.
    Updates the player dict with 'caricature_path' and 'caricature_b64'.
    Reuses existing caricature if already generated (unless fresh=True).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check for cached caricature
    slug = _slugify(player["name"])
    cached_path = output_dir / f"{slug}-caricature.png"
    if not fresh and cached_path.exists() and cached_path.stat().st_size > 0:
        cached_bytes = cached_path.read_bytes()
        player["caricature_path"] = str(cached_path)
        player["caricature_b64"] = base64.b64encode(cached_bytes).decode("utf-8")
        return player

    headshot_path = player.get("headshot_path")

    if not headshot_path or not Path(headshot_path).exists():
        player["caricature_path"] = None
        player["caricature_b64"] = None
        return player

    # Read the headshot image
    image_bytes = Path(headshot_path).read_bytes()

    # Build the style prompt
    prompt = CARICATURE_PROMPT.format(
        jersey_colors=team_config.get("jersey_colors", "team colors"),
        jersey_number=player.get("jersey_number", ""),
    )

    try:
        # Call Gemini API with image input + text prompt
        # Run sync API call in thread pool to not block event loop
        response = await asyncio.to_thread(
            _generate_image, image_bytes, prompt
        )

        if response:
            # Save the caricature
            slug = _slugify(player["name"])
            out_path = output_dir / f"{slug}-caricature.png"
            out_path.write_bytes(response)

            player["caricature_path"] = str(out_path)
            player["caricature_b64"] = base64.b64encode(response).decode("utf-8")
        else:
            player["caricature_path"] = None
            player["caricature_b64"] = None

    except Exception as e:
        print(f"  ⚠ Caricature failed for {player['name']}: {e}")
        player["caricature_path"] = None
        player["caricature_b64"] = None

    return player


def _generate_image(image_bytes: bytes, prompt: str) -> bytes | None:
    """Synchronous Gemini API call for image generation."""
    client = _get_client()

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            prompt,
        ],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    # Extract image bytes from response
    if response.candidates:
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                return part.inline_data.data

    return None


async def generate_all_caricatures(
    players: list[dict], team_config: dict, output_dir: Path, fresh: bool = False
) -> list[dict]:
    """
    Generate caricatures for all players.
    Runs with limited concurrency to respect API rate limits.
    Reuses cached caricatures unless fresh=True.
    """
    semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests

    async def _throttled(player):
        async with semaphore:
            return await generate_caricature(player, team_config, output_dir, fresh)

    tasks = [_throttled(p) for p in players]
    results = await asyncio.gather(*tasks)

    cached = sum(1 for p in results if p.get("caricature_path") and not fresh)
    if cached and not fresh:
        print(f"   📦 Reused {cached} cached caricatures")

    return results


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace(".", "").replace("é", "e").replace("ú", "u")
