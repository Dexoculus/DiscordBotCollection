import os
import discord
from discord.ext import commands
from openai import AsyncOpenAI

from Token import GPT_tokon, discord_token

# Initialize OpenAI async client
client = AsyncOpenAI(api_key=GPT_tokon)

# Set up Discord bot intents
intents = discord.Intents.default()
intents.message_content = True

# Create bot object (prefix: '!')
bot = commands.Bot(command_prefix='!', intents=intents)

# Dictionary to store chat history for each user
chat_history = {}

@bot.event
async def on_ready():
    print(f'Bot successfully logged in: {bot.user}')

@bot.command(name='reset')
async def reset_conversation(ctx):
    """Reset conversation history with the user"""
    user_id = ctx.author.id
    if user_id in chat_history:
        del chat_history[user_id]
    await ctx.send("Conversation history has been reset.")

@bot.listen('on_message')
async def chat_with_gpt(message):
    # Ignore messages sent by the bot itself
    if message.author == bot.user:
        return

    # Ignore messages not starting with the prefix
    if not message.content.startswith('!'):
        return

    user_id = message.author.id

    # Manage chat history for each user
    if user_id not in chat_history:
        chat_history[user_id] = []

    # Add the current user message to the history
    user_message = message.content
    chat_history[user_id].append({"role": "user", "content": user_message})

    try:
        # Call OpenAI ChatCompletion
        completion = await client.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=chat_history[user_id]
        )

        reply = completion.choices[0].message.content

        # Add assistant's reply to the history
        chat_history[user_id].append({"role": "assistant", "content": reply})

        # Send the assistant's reply to the Discord channel
        await message.channel.send(reply)

    except Exception as e:
        await message.channel.send("ERROR: Please try again later.")
        print(f"ERROR: {e}")

if __name__ == "__main__":
    bot.run(discord_token)
