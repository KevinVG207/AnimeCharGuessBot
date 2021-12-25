import collections
import datetime
import random
import discord
import logging
import bot_token
import asyncio
import database as db
import name_tools as nt

DROP_CHANCE = 0.1  # Currently 1/25 messages average 0.04
EMBED_COLOR = discord.Color.red()
DROP_TIMEOUT = 900.0  # 3600.0
PROFILE_TIMEOUT = 30.0
PROFILE_PAGE_SIZE = 25
PREFIX = "w."

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
logger.addHandler(handler)

client = discord.Client()

random.seed()

NAV_LEFT_EMOJI = "⬅"
NAV_RIGHT_EMOJI = "➡"
NAV_EMOJI = {
    NAV_LEFT_EMOJI: -1,
    NAV_RIGHT_EMOJI: 1
}


@client.event
async def on_ready():
    db.enableAllDrops()
    print(f"Bot has logged in as {client.user}")
    print([g.name for g in client.guilds])


@client.event
async def on_guild_remove(guild):
    db.removeGuild(guild.id)


@client.event
async def on_message(message):
    """
    TODO: Rarities.
    TODO: Gacha rolls.
    TODO: Viewing individual claimed images.
    TODO: w.waifus -p 4 -> Automatically go to pages (or max/minimum page if index out of range.)
    TODO: Trading.
    TODO: Add lots of characters!
    """
    if message.author == client.user:
        return

    if message.content == f"{PREFIX}ping":
        return await message.channel.send("Pong! :ping_pong:")

    if message.content == f"{PREFIX}help":
        help_commands = {
            "help": "Show this help message.",
            "ping": "Pong.",
            "waifus": "View your collected waifus.",
            "assign": "Assign bot to a channel. The bot will drop waifus here. Most commands only work in the assigned channel. (Only for members with the Manage Channels permission.)"
        }
        help_lines = []
        for command, text in help_commands.items():
            help_lines.append(f"**{PREFIX}{command}**: {text}")
        return await message.channel.send(embed=makeEmbed("Bot Help", "\n".join(help_lines)))

    # Assign bot to channel.
    if message.content == f"{PREFIX}assign":
        if message.channel.permissions_for(message.author).manage_channels:
            db.assignChannelToGuild(message.channel.id, message.guild.id)
            embed = makeEmbed("Channel Assigned!",
                              f"""I've been assigned to channel ``#{message.channel.name}``""")
            return await message.channel.send(embed=embed)

    # These should only happen in the assigned channel
    if message.channel.id == db.getAssignedChannelID(message.guild.id):
        if message.content == f"{PREFIX}waifus" or message.content.startswith(f"{PREFIX}waifus "):
            args = message.content.replace(f"{PREFIX}waifus", "").strip().split()

            user_id = message.author.id
            user_name = message.author.display_name

            # Arguments
            if args:
                while len(args) > 0:
                    cur_arg = args.pop(0)
                    if not cur_arg.startswith("-") or cur_arg == "-u":
                        if cur_arg.startswith("-"):
                            user_arg = args.pop(0)
                        else:
                            user_arg = cur_arg
                        if user_arg.startswith("<@!"):
                            # It's a ping
                            user_id = int(user_arg[3:-1])
                        else:
                            # Assume it's an ID
                            user_id = user_arg
                        try:
                            # User in current Guild
                            requested_member = await message.guild.fetch_member(user_id)
                            user_name = requested_member.display_name
                        except (discord.errors.NotFound, discord.errors.HTTPException):
                            # User not in current Guild
                            return await message.channel.send(embed=makeEmbed("Waifus Lookup Failed",
                                                                              "Requested user is not in this server."))

            cur_page = 0
            embed, total_pages = getWaifuPageEmbed(user_id, user_name, cur_page)
            if total_pages < 0:
                return await message.channel.send(embed=embed)
            own_message = await message.channel.send(embed=embed)
            await own_message.add_reaction(NAV_LEFT_EMOJI)
            await own_message.add_reaction(NAV_RIGHT_EMOJI)

            def isValidNavigation(r, u):
                if u != client.user and r.message.id == own_message.id and u.id == message.author.id:
                    if r.emoji in NAV_EMOJI:
                        return True
                return False

            while True:
                try:
                    reaction, user = await client.wait_for("reaction_add", check=isValidNavigation, timeout=PROFILE_TIMEOUT)
                except asyncio.TimeoutError:
                    break
                # Reaction received, edit message.
                new_page = cur_page + NAV_EMOJI[reaction.emoji]
                if not new_page < 0 and not new_page + 1 > total_pages:
                    cur_page = new_page
                    embed, total_pages = getWaifuPageEmbed(user_id, user_name, cur_page)
                    if total_pages < 0:
                        return await message.channel.send(embed=embed)
                    await own_message.edit(embed=embed)
                await own_message.remove_reaction(reaction, user)
            return

    # Drops!
    if db.canDrop(message.guild.id):
        if random.random() < DROP_CHANCE:
            assigned_channel_id = db.getAssignedChannelID(message.guild.id)
            if assigned_channel_id:
                # Drop should happen!
                guild_id = message.guild.id
                db.disableDrops(guild_id)
                character_data = db.getDropData()
                assigned_channel = client.get_channel(assigned_channel_id)
                embed = makeEmbed("Waifu Drop!",
                                  f"""A waifu dropped, guess their name!\nHint: ``{nt.generateInitials(character_data)}``""")
                embed.set_image(url=character_data["image_url"])
                await assigned_channel.send(embed=embed)

                def isCorrectGuess(m):
                    if m.channel.id == assigned_channel_id:
                        if verifyGuess(m.content, character_data):
                            return True
                        else:
                            return False
                    else:
                        return False

                try:
                    guess = await client.wait_for("message", check=isCorrectGuess, timeout=DROP_TIMEOUT)
                except asyncio.TimeoutError:
                    db.enableDrops(guild_id)
                    embed = makeEmbed("Timed Out!",
                                      f"""**{character_data["en_name"]}** gave up waiting.\nBetter luck next time!""")
                    embed.set_image(url=character_data["image_url"])
                    return await assigned_channel.send(embed=embed)
                db.enableDrops(guild_id)
                db.saveWin(guess.author.id, character_data["image_id"])
                embed = makeEmbed("Waifu Claimed!",
                                  f"""**{guess.author.display_name}** is correct!\nYou've claimed **{character_data["en_name"]}**.\n[MyAnimeList](https://myanimelist.net/character/{character_data["char_id"]})""")
                embed.set_image(url=character_data["image_url"])
                return await assigned_channel.send(embed=embed)

    return


def getWaifuPageEmbed(user_id, user_name, cur_page):
    waifus, page_data = db.getWaifus(user_id, cur_page, PROFILE_PAGE_SIZE)
    message_strings = []
    if not waifus:
        return makeEmbed("404 Waifu Not Found", f"""Selected user does not have any waifus yet...\nThey'd better claim some!"""), -1
    waifu_index = cur_page * PROFILE_PAGE_SIZE
    for waifu in waifus:
        waifu_index += 1
        message_strings.append(f"""{waifu_index}: **{waifu["en_name"]}** #{waifu["image_index"]}""")
        # message_strings.append(f"""**{waifu["en_name"]}**: {waifu["amount"]}x""")
    final_string = "\n".join(message_strings)
    return makeEmbed(
        f"""{user_name}'s Waifus - Page {page_data["cur_page"] + 1}/{page_data["total_pages"]}""",
        final_string), page_data["total_pages"]


def verifyGuess(guess_name, character_data):
    # Deal with random order of words.
    # Most of the time it will be two, but with more, a random order would still count.
    # This is a compromise. Most people won't try to guess with a random order
    # and if they do, they still had to insert the full name regardless.
    guess_segments = nt.nameToList(guess_name)
    possible_names = [nt.nameToList(character_data["en_name"])]
    if character_data["alt_name"]:
        possible_names.append(nt.nameToList(character_data["alt_name"]))
    for possible_name in possible_names:
        if collections.Counter(guess_segments) == collections.Counter(possible_name):
            return True
    return False


def makeEmbed(title, desciption):
    return discord.Embed(type="rich",
                         title=title,
                         description=desciption,
                         color=EMBED_COLOR,
                         timestamp=datetime.datetime.utcnow())


client.run(bot_token.getToken())
