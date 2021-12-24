import random

import discord
import logging
import bot_token
import asyncio
import database as db

DROP_CHANCE = 0.25

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
logger.addHandler(handler)

client = discord.Client()

random.seed()


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("$ping"):
        await message.channel.send("Pong!:ping_pong:")

    if not message.content.startswith("$") and db.canDrop(message.guild.id):
        if random.random() < DROP_CHANCE:
            # Drop happens!
            assigned_channel_id = db.getAssignedChannelID(message.guild.id)
            if assigned_channel_id:
                assigned_channel = client.get_channel(assigned_channel_id)
                await assigned_channel.send("This should be a drop!")

    if message.content.startswith("$assign"):
        db.assignChannelToGuild(message.channel.id, message.guild.id)
        await message.channel.send(f"I've been assigned to channel {message.channel.name}")

client.run(bot_token.getToken())
