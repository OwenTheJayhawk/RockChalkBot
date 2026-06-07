#https://github.com/henrygd/ncaa-api
#https://www.reddit.com/r/CollegeBasketball/comments/1ario06/free_api_for_live_scores_stats_standings_and/
#https://discord.com/oauth2/authorize?client_id=1328131174098272276&permissions=39584569494528&integration_type=0&scope=bot


import datetime
import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord import FFmpegPCMAudio
import requests
import ffmpeg
import asyncio

# Runtime configuration values (prefer env vars/secrets file in production).
BOT_TOKEN = ""
CHANNEL_ID = 0

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.voice_states = True
intents.message_content = True  # Required for command parsing

bot = commands.Bot(command_prefix = "!", intents = discord.Intents.all())

checker = None
false = False
true = True

# Local sample payload used by helper functions and console checks.
# The bot mainly uses live API data at runtime.
game_data = {
      "game": {
        "gameID": "5809642",
        "away": {
          "score": "74",
          "names": {
            "char6": "KANSAS",
            "short": "Kansas",
            "seo": "kansas",
            "full": "University of Kansas"
          },
          "winner": true,
          "seed": "",
          "description": "(14-4)",
          "rank": "12",
          "conferences": [
            {
              "conferenceName": "Big 12",
              "conferenceSeo": "big-12"
            },
            {
              "conferenceName": "Top 25",
              "conferenceSeo": "top-25"
            }
          ]
        },
        "finalMessage": "FINAL",
        "bracketRound": "",
        "title": "TCU Kansas",
        "contestName": "",
        "url": "/game/6354955",
        "network": "",
        "home": {
          "score": "61",
          "names": {
            "char6": "TCU",
            "short": "TCU",
            "seo": "tcu",
            "full": "Texas Christian University"
          },
          "winner": false,
          "seed": "",
          "description": "(10-8)",
          "rank": "",
          "conferences": [
            {
              "conferenceName": "Big 12",
              "conferenceSeo": "big-12"
            }
          ]
        },
        "liveVideoEnabled": false,
        "startTime": "07:00PM ET",
        "startTimeEpoch": "1737590400",
        "bracketId": "",
        "gameState": "final",
        "startDate": "01-22-2025",
        "currentPeriod": "FINAL",
        "videoState": "",
        "bracketRegion": "",
        "contestClock": "0:00"
      }
    }

def fetch_game_data():
    """Fetches game data from API."""
    # Public NCAA scoreboard endpoint used for polling once per minute.
    # If the API host/path changes, update this URL to the active men's D1 scoreboard endpoint.
    url = "https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

def extract_kansas_game(data):
    """Extracts Kansas game from the input JSON."""
    # Fast path: look only at top-level games list and return first Kansas matchup.
    for game in data.get("games", []):
        if game["game"]["home"]["names"]["short"] == "Kansas" or game["game"]["away"]["names"]["short"] == "Kansas":
            return game["game"]
    return None

@bot.event
async def on_ready():
    # Runs once after login; sync slash commands and start background loop.
    print("HERE COME THE JAYHAWKS")
    synced = await bot.tree.sync()
    print(f"synced {len(synced)} commands")
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
      await channel.send("HERE COME THE JAYHAWKS")
    main.start()

@tasks.loop(minutes = 1)
async def main():
    # Poll live data and send a win announcement once per distinct final game state.
    global checker
    channel = bot.get_channel(CHANNEL_ID)
    data = fetch_game_data()
    game_data = search_for_kansas_in_game(data)


    if game_data:
        new_checker = hash(str(game_data))
        if is_final(game_data) and did_kansas_win(game_data) and checker != new_checker:
            await win_message(channel, game_data)
            # Prevent duplicate posts if the same final result is seen again.
            checker = new_checker


async def play_audio(channel: discord.TextChannel):
    """Connects to a voice channel, plays an audio file, then disconnects."""
    if not channel.guild:
        await channel.send("I couldn't find a valid server.")
        return
    
    # Find an available voice channel
    voice_channel = None
    for vc in channel.guild.voice_channels:
        if vc.members:  # Join a channel with active members if possible
            voice_channel = vc
            break
    if not voice_channel:
        await channel.send("No active voice channels found!")
        return

    try:
        # Reuse the first active voice channel found above.
        vc = await voice_channel.connect(timeout=None)

        # Set this to a valid local media file path accessible from the runtime machine.
        # For portability across systems, prefer constructing a path relative to this project.
        audio_source = discord.FFmpegPCMAudio(r'')
        
        if not vc.is_playing():
            # Play once, then wait until playback ends before disconnecting.
            vc.play(audio_source, after=lambda e: print(f"Playback finished: {e}"))

            while vc.is_playing():
                await asyncio.sleep(360)

        await vc.disconnect()
    except discord.ClientException as e:
        await channel.send(f"Error playing audio: {e}")



@bot.tree.command(name="forcewin", description="Force check if Kansas won and announce it if true.")
async def force_win(interaction: discord.Interaction):

    # Slash command for manual testing without waiting for live poll loop.

    await interaction.response.defer(ephemeral=True)

    channel = bot.get_channel(CHANNEL_ID)
    
    sample_data = fetch_sample_data()
    
    if is_final(sample_data) and did_kansas_win(sample_data):
        await win_message(channel, sample_data)
        await interaction.response.send_message("Win message sent!", ephemeral=True)
    else:
        await interaction.response.send_message("Conditions not met for win message.", ephemeral=True)
       




def search_for_kansas_in_game(data):
    """
    Search for the value "Kansas" associated with the key "short" in a nested dictionary or list.
    If found, return the dictionary with the key "game" containing the match.

    :param data: The nested dictionary or list to search.
    :return: The dictionary with key "game" containing "short": "Kansas", or None if not found.
    """
    if isinstance(data, dict):
        # Check if the current dictionary contains the "game" key
        if "game" in data:
            game_dict = data["game"]
            # Check if "short": "Kansas" exists in the "game" dictionary
            if isinstance(game_dict, dict) and search_for_short_kansas(game_dict):
                return data  # Return the outer dictionary containing "game"

        # Otherwise, recursively search in the current dictionary
        for value in data.values():
            result = search_for_kansas_in_game(value)
            if result:
                # Return first matching game structure encountered.
                return result

    elif isinstance(data, list):
        # If the data is a list, iterate through its items
        for item in data:
            result = search_for_kansas_in_game(item)
            if result:
                return result

    # Return None if "short": "Kansas" is not found
    return None

def search_for_short_kansas(data):
    """
    Helper function to check if "short": "Kansas" exists in a nested structure.

    :param data: The dictionary or list to search.
    :return: True if "short": "Kansas" is found, False otherwise.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "short" and value == "Kansas":
                return True
            # Depth-first search through nested dict/list content.
            if search_for_short_kansas(value):
                return True
    elif isinstance(data, list):
        for item in data:
            if search_for_short_kansas(item):
                return True
    return False

# Example data (Replace this with your full nested data structure)


# Search for "short": "Kansas" within the "game" dictionaries
result = search_for_kansas_in_game(game_data)

# Output the result
if result:
    print("Found 'short': 'Kansas' in 'game' dictionary:")
    print(result)
else:
    print("No match found.")


def is_final(game):
    # Checks if a game is final (currently references global sample data).
    return game_data.get("game", {}).get("gameState") == "final"

#Final = is_final(game_data)
#print(Final)

FINAL_KANSAS_SCORE = 0
FINAL_OPPONENT_SCORE = 0
OPPONENT_NAME = None


def print_final_scores(data):
    """
    Prints the final scores of games where "gameState" is "final", along with team names.

    :param data: The nested dictionary or list containing game data.
    """
    if isinstance(data, dict):
        # Check if the current dictionary contains the "game" key
        if "game" in data:
            game = data["game"]
            if is_final(game_data):
                away_team = game.get("away", {}).get("names", {}).get("short", "Unknown Team")
                away_score = game.get("away", {}).get("score", "N/A")
                home_team = game.get("home", {}).get("names", {}).get("short", "Unknown Team")
                home_score = game.get("home", {}).get("score", "N/A")
                print(f"{home_team} ({home_score}) - {away_team} ({away_score})")

                # Track Kansas/opponent final values for optional reporting.
                if home_team == 'Kansas':
                    FINAL_KANSAS_SCORE = home_score
                    FINAL_OPPONENT_SCORE = away_score
                    OPPONENT_NAME = away_team
                else:
                    FINAL_KANSAS_SCORE = away_score
                    FINAL_OPPONENT_SCORE = home_score
                    OPPONENT_NAME = home_team

        # Recursively search other keys
        for value in data.values():
            print_final_scores(value)

    elif isinstance(data, list):
        # If the data is a list, iterate through its items
        for item in data:
            print_final_scores(item)


print("FINAL SCORE:")
print_final_scores(game_data)

def extract_scores(game):

    # Normalize output as (kansas_score, opponent_score, opponent_name)
    # regardless of home/away side.

  if game["game"]["away"]["names"]["short"] == "Kansas":
      return game["game"]["away"]["score"], game["game"]["home"]["score"], game["game"]["home"]["names"]["short"]
  else:
      return game["game"]["home"]["score"], game["game"]["away"]["score"], game["game"]["away"]["names"]["short"]

def did_kansas_win(game):
    # Uses normalized scores from extract_scores to determine winner.
  kansas_score, opponent_score, _ = extract_scores(game_data)
  return int(kansas_score) > int(opponent_score)




game_result = did_kansas_win(game_data)
print(game_result)


async def win_message(channel, game):
    # Post text celebration first, then trigger voice playback.
    kansas_score, opponent_score, opponent_name = extract_scores(game_data)
    await channel.send(":Jayhawk: :Jayhawk: JAYHAWKS WIN :Jayhawk: :Jayhawk:")
    await channel.send(f"FINAL SCORE: KANSAS {kansas_score} - {opponent_name} {opponent_score}")

    
    await play_audio(channel)

    





def fetch_sample_data():
    """Returns sample game data for testing."""
    return {
        "game": {
            "gameState": "final",
            "away": {"names": {"short": "Kansas"}, "score": "74"},
            "home": {"names": {"short": "TCU"}, "score": "61"}
        }
    }








bot.run(BOT_TOKEN)