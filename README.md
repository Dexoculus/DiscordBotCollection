# Discord Bot Collection

## Overview
- ChatGPT Bot: A conversational bot powered by OpenAI's GPT-3.5-turbo, allowing engaging interactions with users.
- Music Bot: A bot for playing music from YouTube in Discord voice channels.

## Features
- ChatGPT Bot
    - AI-powered conversation using OpenAI's GPT-3.5-turbo.
    - Maintains chat history for personalized and contextual replies.
    - Commands:
        - `!reset`: Clears the chat history for the current user.
- Music Bot
    - Plays music from YouTube directly in voice channels.
    - Commands:
    - `!play [YouTube URL]`: Play or queue a song.
    - `!pause`: Pause the currently playing music.
    - `!resume`: Resume paused music.
    - `!skip`: Skip to the next song in the queue.
    - `!queue`: View the current music queue.
    - `!stop`: Stop playback and disconnect from the voice channel.
    - `!clear`: Clear the queue and playback history.
    - `!setchannel`: Restrict bot commands to the current text channel (Admin only).

## Requirements
- Python 3.8 or higher.

- Required libraries:
    - discord.py
    - openai
    - yt-dlp
    - async_timeout

- Discord bot tokens:
    - ChatGPT bot token.
    - Music bot token.

- OpenAI API key (for ChatGPT Bot).

## License
This project is licensed under the MIT License.