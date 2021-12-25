import datetime
import random

import discord
import logging
import bot_token
import asyncio
import database as db

DROP_CHANCE = 0.04  # Currently 1/25 messages average
EMBED_COLOR = discord.Color.red()

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

    elif message.content.startswith("$ping"):
        await message.channel.send("Pong!:ping_pong:")

    elif message.content.startswith("$assign"):
        db.assignChannelToGuild(message.channel.id, message.guild.id)
        embed = makeEmbed("Channel Assigned!",
                          """I've been assigned to channel ``#{message.channel.name}``""")
        await message.channel.send(embed=embed)

    # These should only happen in the assigned channel
    elif message.channel.id == db.getAssignedChannelID(message.guild.id):
        if message.content.startswith("$waifus"):
            waifus = db.getWaifus(message.author.id)
            message_strings = []
            for waifu in waifus:
                message_strings.append(f"""**{waifu["en_name"]}**: {waifu["amount"]}x""")
            final_string = "\n".join(message_strings)
            embed = makeEmbed(f"""{message.author.display_name}'s Waifus""",
                              final_string)
            await message.channel.send(embed=embed)

    # Drops!
    elif db.canDrop(message.guild.id):
        if random.random() < DROP_CHANCE:
            assigned_channel_id = db.getAssignedChannelID(message.guild.id)
            if assigned_channel_id:
                # Drop should happen!
                guild_id = message.guild.id
                db.disableDrops(guild_id)
                character_data = db.getDropData()
                assigned_channel = client.get_channel(assigned_channel_id)
                embed = makeEmbed("Waifu Drop!",
                                  f"""A waifu dropped, guess their name!\nHint: ``{generateInitials(character_data)}``""")
                embed.set_image(url=character_data["image_url"])
                await assigned_channel.send(embed=embed)

                def isCorrectGuess(m):
                    if m.channel.id == assigned_channel_id:
                        print("correct channel")
                        if verifyGuess(m.clean_content, character_data):
                            print("Correct")
                            return True
                        else:
                            print("Wrong")
                            return False
                    else:
                        return False

                try:
                    guess = await client.wait_for("message", check=isCorrectGuess, timeout=10.0)
                except asyncio.TimeoutError:
                    db.enableDrops(guild_id)
                    embed = makeEmbed("Timed Out!",
                                      f"""**{character_data["en_name"]}** gave up waiting.\nBetter luck next time!""")
                    embed.set_image(url=character_data["image_url"])
                    return await assigned_channel.send(embed=embed)
                db.enableDrops(guild_id)
                db.saveWin(guess.author.id, character_data["image_id"])
                embed = makeEmbed("Correct!",
                                  f"""**{guess.author.display_name}** is correct!\nThat is **{character_data["en_name"]}**.""")
                embed.set_image(url=character_data["image_url"])
                await assigned_channel.send(embed=embed)


def generateInitials(character_data):
    char_name = character_data["en_name"]
    out_string = ""
    initials = [segment[0] for segment in char_name.split(" ")]
    for initial in initials:
        out_string += f"{initial}. "
    return out_string.rstrip()


def verifyGuess(guess_name, character_data):
    # Generate synonyms here?
    if guess_name.lower() == character_data["en_name"].lower():
        return True
    else:
        return False


def makeEmbed(title, desciption):
    return discord.Embed(type="rich",
                         title=title,
                         description=desciption,
                         color=EMBED_COLOR,
                         timestamp=datetime.datetime.utcnow())

client.run(bot_token.getToken())
