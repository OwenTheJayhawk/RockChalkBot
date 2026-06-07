"""Discord bot that posts Kansas men's basketball final scores.

Data source:
https://github.com/henrygd/ncaa-api

Quick setup:
1) Set BOT_TOKEN and CHANNEL_ID (env vars preferred).
2) Optionally set AUDIO_FILE_PATH for post-win audio playback.
3) Run the script and invite the bot with message + voice permissions.
"""

import asyncio
import logging
import os
from typing import Any

import discord
import requests
from discord.ext import commands, tasks

# ----------------------------
# Configuration
# ----------------------------
# Prefer environment variables in production or when sharing on GitHub.
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
AUDIO_FILE_PATH = os.getenv("AUDIO_FILE_PATH", "")
KANSAS_SHORT_NAME = "Kansas"
SCOREBOARD_URL = "https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1"
ANNOUNCEMENT_TEXT = ":Jayhawk: :Jayhawk: JAYHAWKS WIN :Jayhawk: :Jayhawk:"
STARTUP_TEXT = "HERE COME THE JAYHAWKS"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

JsonDict = dict[str, Any]

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# Prevent duplicate win posts when poll loop sees the same final game repeatedly.
last_announced_game_hash = None


def fetch_game_data() -> JsonDict | None:
    """Fetch scoreboard JSON from the public NCAA API."""
    try:
        response = requests.get(SCOREBOARD_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def extract_kansas_game(data: JsonDict | None) -> JsonDict | None:
    """Return the first game dict that includes Kansas, or None."""
    if not isinstance(data, dict):
        return None

    for wrapper in data.get("games", []):
        game = wrapper.get("game", {})
        home_short = game.get("home", {}).get("names", {}).get("short")
        away_short = game.get("away", {}).get("names", {}).get("short")

        if home_short == KANSAS_SHORT_NAME or away_short == KANSAS_SHORT_NAME:
            return game

    return None


def is_final(game: JsonDict) -> bool:
    """Return True when the game state is final."""
    return game.get("gameState") == "final"


def extract_scores(game: JsonDict) -> tuple[str, str, str]:
    """Return (kansas_score, opponent_score, opponent_name)."""
    away = game.get("away", {})
    home = game.get("home", {})
    away_short = away.get("names", {}).get("short")

    if away_short == KANSAS_SHORT_NAME:
        return away.get("score", "0"), home.get("score", "0"), home.get("names", {}).get("short", "Opponent")

    return home.get("score", "0"), away.get("score", "0"), away.get("names", {}).get("short", "Opponent")


def parse_score(value: Any) -> int:
    """Convert score text to int, defaulting to 0 for unexpected values."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def did_kansas_win(game: JsonDict) -> bool:
    """Return True if Kansas has a higher score than the opponent."""
    kansas_score, opponent_score, _ = extract_scores(game)
    return parse_score(kansas_score) > parse_score(opponent_score)


async def play_audio(channel: discord.TextChannel) -> None:
    """Connect to an active voice channel, play audio, and disconnect."""
    if not AUDIO_FILE_PATH:
        return

    if not channel.guild:
        await channel.send("I couldn't find a valid server.")
        return

    voice_channel = next((vc for vc in channel.guild.voice_channels if vc.members), None)
    if not voice_channel:
        await channel.send("No active voice channels found.")
        return

    try:
        voice_client = await voice_channel.connect(timeout=None)
        audio_source = discord.FFmpegPCMAudio(AUDIO_FILE_PATH)

        if not voice_client.is_playing():
            voice_client.play(audio_source)
            while voice_client.is_playing():
                await asyncio.sleep(1)

        await voice_client.disconnect()
    except discord.ClientException as exc:
        await channel.send(f"Error playing audio: {exc}")


async def win_message(channel: discord.TextChannel, game: JsonDict) -> None:
    """Send celebration/final score messages, then attempt audio playback."""
    kansas_score, opponent_score, opponent_name = extract_scores(game)
    await channel.send(ANNOUNCEMENT_TEXT)
    await channel.send(f"FINAL SCORE: KANSAS {kansas_score} - {opponent_name} {opponent_score}")
    await play_audio(channel)


def fetch_sample_data() -> JsonDict:
    """Return sample game data for slash-command testing."""
    return {
        "gameState": "final",
        "away": {"names": {"short": "Kansas"}, "score": "74"},
        "home": {"names": {"short": "TCU"}, "score": "61"},
    }


@bot.event
async def on_ready():
    """Sync slash commands and start polling after bot login."""
    logger.info(STARTUP_TEXT)
    synced = await bot.tree.sync()
    logger.info("synced %s commands", len(synced))

    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(STARTUP_TEXT)

    if not poll_scores.is_running():
        poll_scores.start()


@tasks.loop(minutes=1)
async def poll_scores() -> None:
    """Poll live data and announce a Kansas final win once per distinct game."""
    global last_announced_game_hash

    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        return

    data = fetch_game_data()
    game = extract_kansas_game(data)

    if game is None:
        return

    game_hash = hash(str(game))
    if is_final(game) and did_kansas_win(game) and last_announced_game_hash != game_hash:
        await win_message(channel, game)
        last_announced_game_hash = game_hash


@bot.tree.command(name="forcewin", description="Force check if Kansas won and announce it if true.")
async def force_win(interaction: discord.Interaction):
    """Manual test command so you do not need to wait for the poll loop."""
    await interaction.response.defer(ephemeral=True)

    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        await interaction.followup.send("Channel is not configured or not found.", ephemeral=True)
        return

    sample_game = fetch_sample_data()
    if is_final(sample_game) and did_kansas_win(sample_game):
        await win_message(channel, sample_game)
        await interaction.followup.send("Win message sent.", ephemeral=True)
        return

    await interaction.followup.send("Conditions not met for win message.", ephemeral=True)


def main() -> None:
    """Entry point for running the bot."""
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is empty. Set BOT_TOKEN before running the bot.")

    if CHANNEL_ID <= 0:
        logger.warning("CHANNEL_ID is not set to a valid value; startup messages may fail.")

    bot.run(BOT_TOKEN)


if __name__ == "__main__":
    main()
