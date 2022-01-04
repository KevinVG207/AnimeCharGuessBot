#!/usr/bin/python3

import collections
import datetime
import random
import discord
import logging
import bot_token
import asyncio
import database_tools as db
import name_tools as nt

DROP_CHANCE = 0.1
EMBED_COLOR = discord.Color.red()
DROP_TIMEOUT = 5 * 60.0  # 3600.0
PROFILE_TIMEOUT = 30.0
PROFILE_PAGE_SIZE = 25
PREFIX = "w."
TRADE_TIMEOUT = 60

logger = logging.getLogger('discord')
logger.setLevel(logging.WARNING)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
logger.addHandler(handler)

client = discord.Client()
client.intents.members = True

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
    db.enableAllTrades()
    print(f"Bot has logged in as {client.user}")
    for g in client.guilds:
        print(g.name, g.id)


@client.event
async def on_guild_remove(guild):
    db.removeGuild(guild.id)


@client.event
async def on_message(message):
    """
    TODO: Rarities.
    TODO: Gacha rolls.
    TODO: Trading.
    TODO: Add lots of characters!
    TODO: Pagination for w.show with more than 25 characters.
    TODO: Character detail page (add ID to w.show) with name(s), image(s) (maybe using pagination),
          amount claimed, unique users.
    TODO: Add update functions for character and images in database.
    MAYBE: w.skip to skip drop *based* on the amount of online members.
    """
    if message.author == client.user:
        return

    # I wonder if this causes issues elsewhere. The whole bot becomes case insensitive.
    message.content = message.content.lower()

    if message.content == f"{PREFIX}ping":
        return await message.channel.send("Pong! :ping_pong:")

    if message.content == f"{PREFIX}help" or message.content.startswith(f"{PREFIX}help "):
        args = getMessageArgs("help", message)

        if not args:
            # Simple help
            help_commands = {
                "help": f"Show this help message. Use {PREFIX}help [command] to get help for a specific command.",
                "ping": "Pong.",
                "waifus": "View your collected waifus.",
                "list": f"Alias of {PREFIX}waifus.",
                "search": "Find a show.",
                "show": "View characters of a show.",
                "assign": "Assign bot to a channel. The bot will drop waifus here. Most commands only work in the assigned channel. (Only for members with the Manage Channels permission.)",
                "trade": "Start a trade offer with another user."
            }
            help_lines = []
            for command, text in help_commands.items():
                help_lines.append(f"**{command}**: {text}")
            return await message.channel.send(embed=makeEmbed("Bot Help", "\n".join(help_lines)))
        else:
            # Help for specific command.
            embed_title = "No extra help available."
            embed_description = "This command has no additional help available."
            specific_command = args[0]
            if specific_command == "waifus" or specific_command == "list":
                embed_title = f"Help for {PREFIX}waifus"
                embed_description = f"View your collected waifus inventory.\nUsage: ``{PREFIX}waifus [user ping or ID] -u [user ping or ID] -r [rarity number] -p [page number] -n [part of name (MUST BE FINAL ARGUMENT cuz I'm lazy)]``"
            elif specific_command == "inspect":
                embed_title = f"Help for {PREFIX}inspect"
                embed_description = f"Inspect a waifu in more detail.\nUsage: ``{PREFIX}inspect [inventory number] -u [user ping or ID]``"
            elif specific_command == "search":
                embed_title = f"Help for {PREFIX}search"
                embed_description = f"Look for shows that the bot has characters of.\nUsage: ``{PREFIX}search [anime/manga name]``"
            elif specific_command == "show":
                embed_title = f"Help for {PREFIX}show"
                embed_description = f"Displays the characters of a show that the bot has.\nUsage: ``{PREFIX}show [show id]``"
            elif specific_command == "trade":
                embed_title = f"Help for {PREFIX}trade"
                embed_description = f"Start a trade offer or modify/confirm an existing trade offer.\nUsages:\n``{PREFIX}trade [user]``\n``{PREFIX}trade add [inventory number]``\n``{PREFIX}trade remove [inventory number]``\n``{PREFIX}trade confirm``\n``{PREFIX}trade cancel``"
            return await message.channel.send(embed=makeEmbed(embed_title, embed_description))

    # Assign bot to channel.
    if message.content == f"{PREFIX}assign":
        if message.channel.permissions_for(message.author).administrator:
            db.assignChannelToGuild(message.channel.id, message.guild.id)
            embed = makeEmbed("Channel Assigned!",
                              f"""I've been assigned to channel ``#{message.channel.name}``""")
            return await message.channel.send(embed=embed)

    # These should only happen in the assigned channel
    if message.channel.id == db.getAssignedChannelID(message.guild.id):
        if message.content == f"{PREFIX}waifus" or message.content.startswith(f"{PREFIX}waifus ") or \
                message.content == f"{PREFIX}list" or message.content.startswith(f"{PREFIX}list "):
            if message.content.startswith(f"{PREFIX}waifus"):
                args = getMessageArgs("waifus", message)
            else:
                args = getMessageArgs("list", message)

            user_id = message.author.id
            user_name = message.author.display_name
            cur_page = 0
            rarity = -1
            name_query = None

            # Arguments
            if args:
                while len(args) > 0:
                    cur_arg = args.pop(0)
                    if cur_arg.startswith("-p"):
                        page_arg = args.pop(0)
                        if page_arg.isnumeric():
                            cur_page = int(page_arg) - 1
                    elif cur_arg.startswith("-r"):
                        rarity = args.pop(0)
                        if rarity.isnumeric():
                            rarity = int(rarity)
                        else:
                            return await message.channel.send(embed=makeEmbed("Waifus Lookup Failed",
                                                                              "Rarity not a number."))
                    elif cur_arg.startswith("-n"):
                        name_args = args
                        args = []
                        name_query = " ".join(name_args)
                    elif not cur_arg.startswith("-") or cur_arg == "-u":
                        if cur_arg.startswith("-"):
                            user_arg = args.pop(0)
                        else:
                            user_arg = cur_arg
                        if user_arg.startswith("<@!"):
                            # It's a ping
                            user_id = pingToID(user_arg)
                        else:
                            # Assume it's an ID
                            user_id = user_arg
                        try:
                            # User in current Guild
                            requested_member = await message.guild.fetch_member(user_id)
                            user_id = requested_member.id
                            user_name = requested_member.display_name
                        except (discord.errors.NotFound, discord.errors.HTTPException):
                            # User not in current Guild
                            return await message.channel.send(embed=makeEmbed("Waifus Lookup Failed",
                                                                              "Requested user is not in this server."))
            return await showNormalWaifusPage(message, user_id, user_name, cur_page, rarity, name_query)

        elif message.content == f"{PREFIX}inspect" or message.content.startswith(f"{PREFIX}inspect "):
            args = getMessageArgs("inspect", message)
            user_id = message.author.id
            user_name = message.author.display_name
            inventory_index = 0
            # Arguments
            if not args:
                return await message.channel.send(embed=makeEmbed("Command failed.",
                                                                  f"Usage: ``{PREFIX}inspect [number] (optional: -u @ping/user_id)``"))
            else:
                inventory_arg = args.pop(0)
                if not inventory_arg.isnumeric():
                    return await message.channel.send(embed=makeEmbed("Command failed.",
                                                                      f"Usage: ``{PREFIX}inspect [number]``"))
                inventory_index = int(inventory_arg)
                while len(args) > 0:
                    cur_arg = args.pop(0)
                    if cur_arg == "-u":
                        user_arg = args.pop(0)

                        requested_member = await getUserInGuild(user_arg, message.guild)

                        if not requested_member:
                            # User not in current Guild
                            return await message.channel.send(embed=makeEmbed("Waifus Lookup Failed",
                                                                              "Requested user is not in this server."))
                        user_id = requested_member.id
                        user_name = requested_member.display_name

            return await showClaimedWaifuDetail(message, user_id, user_name, inventory_index)

        elif message.content == f"{PREFIX}search" or message.content.startswith(f"{PREFIX}search "):
            if not message.content.startswith(f"{PREFIX}search "):
                return await message.channel.send(embed=makeEmbed("Command failed.",
                                                                  f"Usage: ``{PREFIX}search [anime/manga name]``"))
            else:
                show_query = message.content.split(" ", 1)[1]
                if len(show_query) < 3:
                    return await message.channel.send(embed=makeEmbed("Query too short.",
                                                                      f"The search query must be 3 or more letters."))
                shows_list = db.getShowsLike(show_query)
                if not shows_list:
                    return await message.channel.send(embed=makeEmbed("Show Search", "No results."))
                else:
                    return await message.channel.send(embed=makeShowsListEmbed(shows_list))

        elif message.content == f"{PREFIX}show" or message.content.startswith(f"{PREFIX}show "):
            args = getMessageArgs("show", message)
            if not args:
                return await message.channel.send(embed=makeEmbed("Command failed.",
                                                                  f"Usage: ``{PREFIX}show [show id]``"))
            else:
                show_id = args[0]
                if not show_id.isnumeric():
                    return await message.channel.send(embed=makeEmbed("Command failed.",
                                                                      f"Usage: ``{PREFIX}show [show id]``"))
                else:
                    show_id = int(show_id)
                    if not db.showExists(show_id):
                        return await message.channel.send(embed=makeEmbed("Command failed.",
                                                                          f"Show ID not found."))
                    characters = db.getCharactersFromShow(show_id)
                    show_title_jp = db.getShowTitleJP(show_id)
                    if not characters:
                        return await message.channel.send(embed=makeEmbed(f"{show_title_jp}",
                                                                          f"No waifus found for this show."))
                    else:
                        return await message.channel.send(embed=makeShowWaifusEmbed(show_title_jp, characters))

        elif message.content == f"{PREFIX}trade" or message.content.startswith(f"{PREFIX}trade "):
            if db.canTrade(message.author.id):
                if not message.content.startswith(f"{PREFIX}trade "):
                    return await message.channel.send(
                        embed=makeEmbed("Command failed.", f"Usage: ``{PREFIX}trade [user]``"))
                user1 = message.author
                user1_confirm = False
                user1_offer = []
                user2 = await getUserInGuild(message.content.split(" ", 1)[1], message.guild)

                if not user2 or user1.id == user2.id:
                    return await message.channel.send(
                        embed=makeEmbed("Failed to start trade.", "User not found in server."))

                user2_confirm = False
                user2_offer = []
                cancel = False
                timeout = False

                db.disableTrade(user1.id)
                db.disableTrade(user2.id)

                def receiveTradeMessage(m):
                    if m.channel.id == message.channel.id:
                        if m.author.id == user1.id or m.author.id == user2.id:
                            return True
                    return False

                change = False
                user1_prev_confirm = -1
                user2_prev_confirm = -1

                while not cancel and not timeout:
                    # Determine what to do
                    if user1_prev_confirm != user1_confirm or \
                            user2_prev_confirm != user2_confirm or \
                            change:
                        # State changed!
                        if user1_confirm and user2_confirm:
                            # Both confirmed
                            break
                        else:
                            # Normal state change
                            await message.channel.send(
                                embed=makeTradeEmbed(user1, user2, user1_offer, user2_offer, user1_confirm, user2_confirm))
                    else:
                        # No state change
                        pass

                    if cancel:
                        break

                    user1_prev_confirm = user1_confirm
                    user2_prev_confirm = user2_confirm
                    change = False

                    # Wait for next message
                    try:
                        m = await client.wait_for("message", check=receiveTradeMessage,
                                                  timeout=TRADE_TIMEOUT if not bot_token.isDebug() else 30)
                        m.content = m.content.lower()
                        if m.content == f"{PREFIX}trade cancel":
                            cancel = True
                        elif m.content == f"{PREFIX}trade confirm":
                            if m.author.id == user1.id:
                                user1_confirm = True
                            else:
                                user2_confirm = True
                        elif m.content.startswith(f"{PREFIX}trade add"):
                            if not m.content.startswith(f"{PREFIX}trade add "):
                                await m.channel.send(embed=makeEmbed("Trade add failed.",
                                                                     f"Usage: ``{PREFIX}trade add [inventory number]``"))
                            else:
                                to_be_added = m.content.split(" ", 2)[2]
                                if not to_be_added.isnumeric():
                                    await m.channel.send(embed=makeEmbed("Trade add failed.",
                                                                         f"Usage: ``{PREFIX}trade add [inventory number]``"))
                                else:
                                    to_be_added = int(to_be_added)
                                    current_waifus = db.getWaifus(m.author.id, unpaginated=True)
                                    if to_be_added > len(current_waifus):
                                        await m.channel.send(embed=makeEmbed("Trade add failed.",
                                                                             f"Waifu not found in user's inventory."))
                                    else:
                                        if m.author.id == user1.id:
                                            new_waifu = current_waifus[to_be_added - 1]
                                            dupe = False
                                            for waifu in user1_offer:
                                                if waifu["waifus_id"] == new_waifu["waifus_id"]:
                                                    dupe = True
                                                    await m.channel.send(embed=makeEmbed("Trade add failed.", "Selected waifu already in offer."))
                                            if not dupe:
                                                user1_offer.append(new_waifu)
                                                change = True
                                        else:
                                            new_waifu = current_waifus[to_be_added - 1]
                                            dupe = False
                                            for waifu in user2_offer:
                                                if waifu["waifus_id"] == new_waifu["waifus_id"]:
                                                    dupe = True
                                                    await m.channel.send(embed=makeEmbed("Trade add failed.",
                                                                                         "Selected waifu already in offer."))
                                            if not dupe:
                                                user2_offer.append(new_waifu)
                                                change = True
                        elif m.content.startswith(f"{PREFIX}trade remove"):
                            if not m.content.startswith(f"{PREFIX}trade remove "):
                                await m.channel.send(embed=makeEmbed("Trade remove failed.",
                                                                     f"Usage: ``{PREFIX}trade remove [inventory number]``"))
                            else:
                                to_be_removed = m.content.split(" ", 2)[2]
                                if not to_be_removed.isnumeric():
                                    await m.channel.send(embed=makeEmbed("Trade remove failed.",
                                                                         f"Usage: ``{PREFIX}trade remove [inventory number]``"))
                                else:
                                    to_be_removed = int(to_be_removed)
                                    removed = False
                                    new_offer = []
                                    if m.author.id == user1.id:
                                        for waifu in user1_offer:
                                            if waifu["index"] == to_be_removed:
                                                removed = True
                                            else:
                                                new_offer.append(waifu)
                                        user1_offer = new_offer
                                    else:
                                        for waifu in user2_offer:
                                            if waifu["index"] == to_be_removed:
                                                removed = True
                                            else:
                                                new_offer.append(waifu)
                                        user2_offer = new_offer
                                    if not removed:
                                        await m.channel.send(embed=makeEmbed("Trade remove failed.", "Waifu not found in trade offer."))
                                    else:
                                        change = True
                    except asyncio.TimeoutError:
                        timeout = True
                        break

                db.enableTrade(user1.id)
                db.enableTrade(user2.id)

                if cancel:
                    return await message.channel.send(embed=makeEmbed("Trade Cancelled", "Trade has been cancelled."))
                elif timeout:
                    return await message.channel.send(embed=makeEmbed("Trade Cancelled", "Trade has timed out."))
                else:
                    if not db.trade(user1.id, user2.id, user1_offer, user2_offer):
                        return await message.channel.send(embed=makeEmbed("Trade Failed",
                                                                          "Something went wrong. The trade has been cancelled."))
                    return await message.channel.send(embed=makeEmbed("Trade Succeeded", "Trade has been confirmed!"))

    # Drops!
    if not message.content.startswith(f"{PREFIX}") and db.canDrop(message.guild.id):
        if random.random() < calcDropChance(message.guild.member_count):
            assigned_channel_id = db.getAssignedChannelID(message.guild.id)
            if assigned_channel_id:
                # Drop should happen!
                guild_id = message.guild.id
                db.disableDrops(guild_id)
                history = db.getHistory(guild_id)
                character_data = db.getDropData(history=history)
                if not history:
                    history = []
                history.append(character_data["char_id"])
                if len(history) > 100:
                    history.pop(0)
                db.updateHistory(guild_id, history)
                assigned_channel = client.get_channel(assigned_channel_id)
                embed = makeEmbed("Waifu Drop!",
                                  f"""A waifu dropped, guess their name!\nHint: ``{nt.generateInitials(character_data)}``""")
                embed.set_image(url=character_data["image_url"])
                await assigned_channel.send(embed=embed)

                def isCorrectGuess(m):
                    if m.channel.id == assigned_channel_id:
                        if verifyGuess(m.content.lower(), character_data):
                            return True
                        else:
                            return False
                    else:
                        return False

                try:
                    timeout = DROP_TIMEOUT if not bot_token.isDebug() else 30
                    guess = await client.wait_for("message", check=isCorrectGuess, timeout=timeout)
                except asyncio.TimeoutError:
                    db.enableDrops(guild_id)
                    embed = makeEmbed("Timed Out!",
                                      f"""**{character_data["en_name"]}** gave up waiting.\nBetter luck next time!""")
                    embed.set_image(url=character_data["image_url"])
                    return await assigned_channel.send(embed=embed)
                db.enableDrops(guild_id)
                db.addWaifu(guess.author.id, character_data["image_id"], character_data["rarity"])
                embed = makeEmbed("Waifu Claimed!",
                                  f"""**{guess.author.display_name}** is correct!\nYou've claimed **{character_data["en_name"]}**.\nRarity: {character_data["rarity"]}\n[MyAnimeList](https://myanimelist.net/character/{character_data["char_id"]})""")
                embed.set_image(url=character_data["image_url"])
                return await guess.reply(embed=embed)

    return


def pingToID(ping_string):
    return int(ping_string[3:-1])


def calcDropChance(user_count):
    if bot_token.isDebug():
        return 1
    else:
        return min(0.1, (1 / (user_count / 10)))


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


async def showNormalWaifusPage(message, user_id, user_name, cur_page, rarity, name_query):
    embed, total_pages, cur_page = getWaifuPageEmbed(user_id, user_name, cur_page, rarity, name_query)
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
            embed, total_pages, cur_page = getWaifuPageEmbed(user_id, user_name, cur_page, rarity, name_query)
            if total_pages < 0:
                return await message.channel.send(embed=embed)
            await own_message.edit(embed=embed)
        await own_message.remove_reaction(reaction, user)
    return


def getWaifuPageEmbed(user_id, user_name, cur_page, rarity, name_query):
    page_data = db.getWaifus(user_id, rarity, name_query, PROFILE_PAGE_SIZE)
    if not page_data:
        return makeEmbed("404 Waifu Not Found",
                         f"""Selected user does not have any waifus that match the request...\nThey'd better claim some!"""), -1, -1
    if cur_page < 0:
        cur_page = 0
    elif cur_page - 1 >= len(page_data):
        cur_page = len(page_data) - 1
    page = page_data[cur_page]
    message_strings = []
    for waifu in page:
        message_strings.append(
            f"""{waifu["index"]}: **{waifu["en_name"]}** R:{waifu["rarity"]} #{waifu["image_index"]}""")
        # message_strings.append(f"""**{waifu["en_name"]}**: {waifu["amount"]}x""")
    final_string = "\n".join(message_strings)
    return makeEmbed(
        f"""{user_name}'s Waifus - Page {cur_page + 1}/{len(page_data)}""",
        final_string), len(page_data), cur_page


def clamp(n, minn, maxn):
    return max(min(maxn, n), minn)


async def showClaimedWaifuDetail(message, user_id, user_name, inventory_index):
    total_waifus = int(db.getWaifuCount(user_id))
    if total_waifus == 0:
        return await message.channel.send(embed=makeEmbed("404 Waifu Not Found",
                                                          f"""Selected user does not have any waifus yet...\nThey'd better claim some!"""))
    skip = clamp(inventory_index, 1, total_waifus) - 1
    waifu_data = db.getWaifuOfUser(user_id, skip)
    if not waifu_data:
        return await message.channel.send(embed=makeEmbed("404 Waifu Not Found",
                                                          f"""Something went wrong with retrieving the requested waifu."""))
    description = f"""Character [{waifu_data["id"]}](https://myanimelist.net/character/{waifu_data["id"]})\n**{waifu_data["en_name"]}**\n"""
    if waifu_data["jp_name"]:
        description += f"""{waifu_data["jp_name"]}\n"""
    description += f"""Rarity: {waifu_data["rarity"]}\n"""
    description += f"""Image #{waifu_data["image_index"]}"""

    embed = makeEmbed("Waifu Detail", description)
    embed.set_image(url=waifu_data["image_url"])
    embed.set_footer(text=f"{user_name}'s Waifu #{inventory_index}")

    return await message.channel.send(embed=embed)


def getMessageArgs(command, message):
    return message.content.replace(f"{PREFIX}{command}", "").strip().split()


def makeShowsListEmbed(shows_list):
    shows_strings = []
    for show in shows_list:
        shows_strings.append(
            f"""{show["id"]} | **{show["jp_title"]}** ({"Anime" if not show["is_manga"] else "Manga"})""")

    embed = makeEmbed("Show Search", "\n".join(shows_strings))
    return embed


def makeShowWaifusEmbed(show_title_jp, characters):
    characters_string = []
    for character in characters:
        characters_string.append(
            f"""**{character["en_name"]}** | {character["image_count"]} image{"s" if character["image_count"] > 1 else ""}""")
    embed = makeEmbed(f"{show_title_jp}", "\n".join(characters_string))
    return embed


async def getUserInGuild(requested_user, guild):
    """
    Gets user object from ping or user ID.
    Returns None if user not found in guild.
    :param requested_user: string - User ping or ID
    :param guild: Guild Object - The guild to search the user in.
    :return: User Object
    """
    if requested_user.startswith("<@!"):
        # It's a ping
        user_id = pingToID(requested_user)
    else:
        # Assume it's an ID
        user_id = requested_user
    try:
        # User in current Guild
        member_in_guild = await guild.fetch_member(user_id)
        return member_in_guild
    except (discord.errors.NotFound, discord.errors.HTTPException):
        # User not in current Guild
        return None


def makeTradeEmbed(user1, user2, user1_offer, user2_offer, user1_confirm, user2_confirm):
    description = ""

    description += f"**{user1.display_name}**'s offer:\n"
    if not user1_offer:
        description += "``Empty``\n"
    else:
        for waifu in user1_offer:
            description += f"""{waifu["index"]} | {waifu["char_id"]} **{waifu["en_name"]}** R:{waifu["rarity"]} #{waifu["image_index"]}\n"""
    description += f"""{":white_check_mark: Confirmed" if user1_confirm else ":x: Unconfirmed"}\n"""

    description += f"\n**{user2.display_name}**'s offer:\n"
    if not user2_offer:
        description += "``Empty``\n"
    else:
        for waifu in user2_offer:
            description += f"""{waifu["index"]} | {waifu["char_id"]} **{waifu["en_name"]}** R:{waifu["rarity"]} #{waifu["image_index"]}\n"""
    description += f"""{":white_check_mark: Confirmed" if user2_confirm else ":x: Unconfirmed"}\n"""

    description += f"""\nAdd waifus using ``{PREFIX}trade add [inventory number]``\nConfirm trade using ``{PREFIX}trade confirm``"""

    embed = makeEmbed("Waifu Trade Offer", description)
    return embed


client.run(bot_token.getToken())
