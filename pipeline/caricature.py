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


async def generate_caricature(player: dict, team_config: dict, output_dir: Path) -> dict:
    """
    Generate a caricature from a player's headshot photo.
    Updates the player dict with 'caricature_path' and 'caricature_b64'.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
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
    players: list[dict], team_config: dict, output_dir: Path
) -> list[dict]:
    """
    Generate caricatures for all players.
    Runs with limited concurrency to respect API rate limits.
    """
    semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests

    async def _throttled(player):
        async with semaphore:
            return await generate_caricature(player, team_config, output_dir)

    tasks = [_throttled(p) for p in players]
    return await asyncio.gather(*tasks)


def _slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace(".", "").replace("é", "e").replace("ú", "u")
