# Rock Chalk Bot

Rock Chalk Bot is a Discord bot built to track Kansas basketball games and celebrate wins in a Discord server. It watches NCAA game data, detects when a Kansas game becomes final, and posts a win announcement with final scores. It can also join a voice channel and play a Jayhawks audio clip when Kansas wins.

## Features

- Polls the NCAA scoreboard for men’s Division I basketball game data.
- Searches the returned scoreboard payload for Kansas games.
- Detects when a Kansas game is final and checks whether Kansas won.
- Posts win messages and final scores to a configured Discord channel.
- Plays a Jayhawks fight-song audio file in an active voice channel after a win.
- Includes a `/forcewin` slash command to manually trigger a win check.

## How It Uses ncaa-api

This bot integrates with the public NCAA API by sending a GET request to the scoreboard endpoint for men’s basketball:

`https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1`

The bot then walks the JSON response to find the Kansas game, reads the game state, and compares the final scores. When the game is marked as `final` and Kansas has the higher score, it sends the win announcement to Discord.

The API itself is documented and maintained here:

- GitHub repo: https://github.com/henrygd/ncaa-api

## Bot Flow

1. The bot starts and syncs its slash commands.
2. Every minute, it fetches the latest scoreboard data from ncaa-api.
3. It searches the data for a game containing `Kansas`.
4. If the game is final and Kansas won, it posts the win message once.
5. It then joins a voice channel with active users and plays the audio file.

## Slash Commands

- `/forcewin` - Manually checks the sample game payload and sends the win message if the conditions are met.

## Requirements

- Python 3.10+.
- `discord.py`
- `requests`
- `ffmpeg` available on the system path.
- A Discord bot token and a target channel ID.

## Setup

1. Install the Python dependencies used by the script.
2. Update the bot token and channel ID in `ScoreFinder.py`.
3. Make sure the audio file path points to an accessible `.mp3` file.
4. Run the bot and invite it to your Discord server.

## Notes

- The current script is focused on Kansas basketball, but the ncaa-api endpoint can be swapped for other sports or divisions.
