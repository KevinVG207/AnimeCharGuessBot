#!/usr/bin/python3

import collections
import datetime
import random
import time

import discord
import logging
import bot_token
import asyncio
import database_tools as db
import name_tools as nt
from numpy import random as numpyrand

CHARACTER_TIMEOUT = 30.0
CURRENCY = "credits"
DROP_CHANCE = 0.1
DROP_TIMEOUT = 10 * 60.0  # 3600.0
EMBED_COLOR = discord.Color.red()
GIFT_TIMEOUT = 15
PROFILE_TIMEOUT = 30.0
PROFILE_PAGE_SIZE = 25
PREFIX = "w." if not bot_token.isDebug() else bot_token.getPrefix()
REMOVAL_TIMEOUT = 15
TRADE_TIMEOUT = 60
UPGRADE_TIMEOUT = 15
HISTORY_SIZE = 500

logger = logging.getLogger('discord')
logger.setLevel(logging.WARNING)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
logger.addHandler(handler)

intents = discord.Intents().all()

client = discord.Client(intents=intents)

random.seed()

NAV_LEFT_EMOJI = "⬅"
NAV_RIGHT_EMOJI = "➡"
NAV_EMOJI = {
    NAV_LEFT_EMOJI: -1,
    NAV_RIGHT_EMOJI: 1
}

UPGRADE_FROM_COSTS = {
    0: 1,
    1: 5,
    2: 10,
    3: 20,
    4: None,
    5: None
}


@client.event
async def on_ready():
    db.enableAllDrops()
    db.enableAllTrades()
    db.enableAllRemoves()
    print(f"Bot has logged in as {client.user}")
    for g in client.guilds:
        print(g.name, g.id)


@client.event
async def on_guild_remove(guild):
    db.removeGuild(guild.id)


@client.event
async def on_message(message):
    """
    TODO: Favorite waifus with w.fav (can't be thrown away). And add a fav filter to w.list. (or w.favs)
    TODO: w.profile set [number] to set a waifu on your profile.
    TODO: Add -s [show_id] to w.waifus
    TODO: Add lots of characters!
    TODO: Pagination for w.show with more than 25 characters.
    TODO: Add update functions for character and images in database.
    MAYBE: w.skip to skip drop *based* on the amount of online members.
    """
    if message.author == client.user or message.author.bot:
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
                "help": f"Show this help message. Use ``{PREFIX}help [command]`` to get help for a specific command.",
                "ping": "Pong.",
                "waifus": "View your collected waifus.",
                "list": f"Alias of ``{PREFIX}waifus``.",
                "search": "Find a show.",
                "show": "View characters of a show.",
                "assign": "Assign bot to a channel. The bot will drop waifus here. Most commands only work in the assigned channel. (Only for members with the Manage Channels permission.)",
                "trade": "Start a trade offer with another user.",
                "waifu": "View one of your collected waifus in more detail.",
                "remove": "Let one or more of your waifus go.",
                "profile": "View your (or someone else's) profile.",
                "roll": f"Perform a gacha roll. (Default: 100 {CURRENCY})",
                "wager": f"Wager {CURRENCY} and have 50% chance to double it.",
                "fav": "Favorite a waifu.",
                "unfav": "Unfavorite a waifu.",
                "view": "View details of a character including stats.",
                "daily": f"Claim daily {CURRENCY}.",
                "give": f"Alias of ``{PREFIX}gift``.",
                "gift": f"Give a user {CURRENCY}.",
                "upgrade": f"Upgrade the star rating of a waifu using upgrade parts."
            }
            commands_sorted = sorted(help_commands.keys())
            help_lines = []
            for command in commands_sorted:
                help_lines.append(f"**{command}**: {help_commands[command]}")
            return await message.channel.send(embed=makeEmbed("Bot Help", "\n".join(help_lines)))
        else:
            # Help for specific command.
            embed_title = "No extra help available."
            embed_description = "This command has no additional help available."
            specific_command = args[0]
            if specific_command == "waifus" or specific_command == "list":
                embed_title = f"Help for {PREFIX}waifus"
                embed_description = f"View your collected waifus inventory.\nUsage: ``{PREFIX}waifus [user ping or ID] -u [user ping or ID] -r [rating] -p [page number] -n [part of name (MUST BE FINAL ARGUMENT cuz I'm lazy)]``"
            elif specific_command == "view":
                embed_title = f"Help for {PREFIX}waifu"
                embed_description = f"View a collected waifu in more detail.\nUsage: ``{PREFIX}view [inventory number] -u [user ping or ID]``"
            elif specific_command == "search":
                embed_title = f"Help for {PREFIX}search"
                embed_description = f"Look for shows that the bot has characters of.\nUsage: ``{PREFIX}search [anime/manga name]``"
            elif specific_command == "show":
                embed_title = f"Help for {PREFIX}show"
                embed_description = f"Displays the characters of a show that the bot has.\nUsage: ``{PREFIX}show [show id]``"
            elif specific_command == "trade":
                embed_title = f"Help for {PREFIX}trade"
                embed_description = f"Start a trade offer or modify/confirm an existing trade offer.\nUsages:\n``{PREFIX}trade [user]``\n``{PREFIX}trade add [inventory number]``\n``{PREFIX}trade remove [inventory number]``\n``{PREFIX}trade {CURRENCY} [amount] (use 0 to cancel)``\n``{PREFIX}trade confirm``\n``{PREFIX}trade cancel``"
            elif specific_command == "remove":
                embed_title = f"Help for {PREFIX}remove"
                embed_description = f"Let one of your waifus go. This will reward you {CURRENCY} depending on the rarity of the waifu.\n(1/4 of {CURRENCY} needed to roll that same rarity.)\nUsages:\n``{PREFIX}remove [inventory number]``\n``{PREFIX}remove -s [show id]``"
            elif specific_command == "profile":
                embed_title = f"Help for {PREFIX}profile"
                embed_description = f"Display your profile page. Mention a user to see theirs.\nUsage: ``{PREFIX}profile [user ping or ID]``"
            elif specific_command == "roll":
                embed_title = f"Help for {PREFIX}roll"
                embed_description = f"""Perform a gacha roll with optional infusion of {CURRENCY}.\n(Default: 100, maximum: 15000)\nPrices for guaranteed rarities:\n``★★☆☆☆: 300``\n``★★★☆☆: 1000``\n``★★★★☆: 5000``\n``★★★★★: 15000``\nUsage: ``{PREFIX}roll [{CURRENCY}]``"""
            elif specific_command == "wager":
                embed_title = f"Help for {PREFIX}wager"
                embed_description = f"Wager {CURRENCY} with a 50% chance of doubling them. (Or losing them :P)\nUsage: ``{PREFIX}wager [amount]``"
            elif specific_command == "fav":
                embed_title = f"Help for {PREFIX}fav"
                embed_description = f"Favorites a waifu from your inventory.\nUsage: ``{PREFIX}fav [inventory slot]``"
            elif specific_command == "unfav":
                embed_title = f"Help for {PREFIX}unfav"
                embed_description = f"Unfavorites a waifu from your inventory.\nUsage: ``{PREFIX}unfav [inventory slot]``"
            elif specific_command == "view":
                embed_title = f"Help for {PREFIX}view"
                embed_description = f"View a character's detail page.\nUsage: ``{PREFIX}view [character ID]``"
            elif specific_command == "daily":
                embed_title = f"Help for {PREFIX}daily"
                embed_description = f"Claim your daily {CURRENCY}.\nResets after <t:{generateNextMidnight()}:t>."
            elif specific_command == "give" or specific_command == "gift":
                embed_title = f"Help for {PREFIX}gift"
                embed_description = f"Gift some of your {CURRENCY} to someone else.\nUsage: ``{PREFIX}gift @user [amount]``"
            elif specific_command == "upgrade":
                embed_title = f"Help for {PREFIX}upgrade"
                embed_description = f"Upgrade a waifu's star rating using upgrade parts.\nUsage: ``{PREFIX}upgrade [inventory slot]``"
            return await message.channel.send(embed=makeEmbed(embed_title, embed_description))

    # Assign bot to channel.
    if message.content == f"{PREFIX}assign":
        if message.channel.permissions_for(message.author).administrator:
            db.assignChannelToGuild(message.channel.id, message.guild.id)
            embed = makeEmbed("Channel Assigned!",
                              f"""I've been assigned to channel ``#{message.channel.name}``""")
            return await message.channel.send(embed=embed)

    # These should only happen in the assigned channel
    if not message.guild or message.channel.id == db.getAssignedChannelID(message.guild.id):
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
            show_id = None

            # Arguments
            if args:
                while len(args) > 0:
                    cur_arg = args.pop(0)
                    if cur_arg.startswith("-p"):
                        if args:
                            page_arg = args.pop(0)
                            if page_arg.isnumeric():
                                cur_page = int(page_arg) - 1
                    elif cur_arg.startswith("-s"):
                        if args:
                            show_arg = args.pop(0)
                            if show_arg.isnumeric():
                                show_id = int(show_arg)
                    elif cur_arg.startswith("-r"):
                        if args:
                            rarity = args.pop(0)
                            if rarity.isnumeric():
                                rarity = int(rarity)
                                if rarity < 1:
                                    rarity = 1
                                if rarity > 6:
                                    rarity = 6
                                rarity -= 1
                            else:
                                return await message.channel.send(embed=makeEmbed("Waifus Lookup Failed",
                                                                                  "Rarity not a number."))
                    elif cur_arg.startswith("-n"):
                        name_args = args
                        args = []
                        name_query = " ".join(name_args)
                    elif not cur_arg.startswith("-") or cur_arg == "-u":
                        if cur_arg.startswith("-"):
                            if args:
                                user_arg = args.pop(0)
                            else:
                                return await message.channel.send(embed=makeEmbed("Waifus Lookup Failed",
                                                                                  "Did not mention a user."))
                        else:
                            user_arg = cur_arg
                        if user_arg.startswith("<@"):
                            # It's a ping
                            user_id = pingToID(user_arg)
                        else:
                            # Assume it's an ID
                            user_id = user_arg
                        try:
                            # User in current Guild
                            if not message.guild:
                                return await message.reply(
                                    embed=makeEmbed("User Lookup Failed", "You cannot look for users in DMs."))
                            requested_member = await message.guild.fetch_member(user_id)
                            user_id = requested_member.id
                            user_name = requested_member.display_name
                        except (discord.errors.NotFound, discord.errors.HTTPException):
                            # User not in current Guild
                            return await message.channel.send(embed=makeEmbed("Waifus Lookup Failed",
                                                                              "Requested user is not in this server."))
            return await showNormalWaifusPage(message, user_id, user_name, cur_page, rarity, name_query, show_id)

        elif message.content == f"{PREFIX}waifu" or message.content.startswith(f"{PREFIX}waifu "):
            args = getMessageArgs("waifu", message)
            user_id = message.author.id
            user_name = message.author.display_name
            # Arguments
            if not args:
                return await message.channel.send(embed=makeEmbed("Command failed.",
                                                                  f"Usage: ``{PREFIX}waifu [number] (optional: -u @ping/user_id)``"))
            else:
                inventory_arg = args.pop(0)
                if not inventory_arg.isnumeric():
                    return await message.channel.send(embed=makeEmbed("Command failed.",
                                                                      f"Usage: ``{PREFIX}waifu [number]``"))
                inventory_index = int(inventory_arg)
                while len(args) > 0:
                    cur_arg = args.pop(0)
                    if cur_arg == "-u":
                        if args:
                            user_arg = args.pop(0)
                        else:
                            return await message.channel.send(embed=makeEmbed("Command failed.",
                                                                              f"Usage: ``{PREFIX}waifu [number]``"))
                        if not message.guild:
                            return await message.reply(
                                embed=makeEmbed("User Lookup Failed", "You cannot look for users in DMs."))

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
                if not db.canRemove(message.author.id):
                    return await message.reply(
                        embed=makeEmbed("Command failed.", "Cannot initate trade while removing waifus."))
                if not message.content.startswith(f"{PREFIX}trade "):
                    return await message.reply(
                        embed=makeEmbed("Command failed.", f"Usage: ``{PREFIX}trade [user]``"))
                user1 = message.author
                user1_confirm = False
                user1_offer = []
                user1_currency = 0

                if not message.guild:
                    return await message.reply(
                        embed=makeEmbed("User Lookup Failed", "You cannot look for users in DMs."))

                user2 = await getUserInGuild(message.content.split(" ", 1)[1], message.guild)

                if not user2 or user1.id == user2.id:
                    return await message.channel.send(
                        embed=makeEmbed("Failed to start trade.", "User not found in server."))

                user2_confirm = False
                user2_offer = []
                user2_currency = 0
                cancel = False
                timeout = False

                if db.canTrade(user1.id) and db.canRemove(user1.id) and db.canTrade(user2.id) and db.canRemove(
                        user2.id):
                    db.disableTrade(user1.id)
                    db.disableTrade(user2.id)
                else:
                    return await message.channel.send(
                        makeEmbed("Something went wrong.", "Unable to perform action."))

                def receiveTradeMessage(incoming_message):
                    if incoming_message.channel.id == message.channel.id:
                        if incoming_message.author.id == user1.id or incoming_message.author.id == user2.id:
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
                                embed=makeTradeEmbed(user1, user2, user1_offer, user2_offer, user1_currency,
                                                     user2_currency, user1_confirm, user2_confirm))
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
                                await m.reply(embed=makeEmbed("Trade add failed.",
                                                              f"Usage: ``{PREFIX}trade add [inventory number]``"))
                            else:
                                to_be_added = m.content.split(" ", 2)[2]
                                if not to_be_added.isnumeric():
                                    await m.reply(embed=makeEmbed("Trade add failed.",
                                                                  f"Usage: ``{PREFIX}trade add [inventory number]``"))
                                else:
                                    to_be_added = int(to_be_added)
                                    current_waifus = db.getWaifus(m.author.id, unpaginated=True)
                                    if to_be_added > len(current_waifus):
                                        await m.reply(embed=makeEmbed("Trade add failed.",
                                                                      f"Waifu not found in user's inventory."))
                                    else:
                                        if m.author.id == user1.id:
                                            new_waifu = current_waifus[to_be_added - 1]
                                            dupe = False
                                            for waifu in user1_offer:
                                                if waifu["waifus_id"] == new_waifu["waifus_id"]:
                                                    dupe = True
                                                    await m.reply(embed=makeEmbed("Trade add failed.",
                                                                                  "Selected waifu already in offer."))
                                            if not dupe:
                                                user1_offer.append(new_waifu)
                                                change = True
                                        else:
                                            new_waifu = current_waifus[to_be_added - 1]
                                            dupe = False
                                            for waifu in user2_offer:
                                                if waifu["waifus_id"] == new_waifu["waifus_id"]:
                                                    dupe = True
                                                    await m.reply(embed=makeEmbed("Trade add failed.",
                                                                                  "Selected waifu already in offer."))
                                            if not dupe:
                                                user2_offer.append(new_waifu)
                                                change = True
                        elif m.content.startswith(f"{PREFIX}trade remove"):
                            if not m.content.startswith(f"{PREFIX}trade remove "):
                                await m.reply(embed=makeEmbed("Trade remove failed.",
                                                              f"Usage: ``{PREFIX}trade remove [inventory number]``"))
                            else:
                                to_be_removed = m.content.split(" ", 2)[2]
                                if not to_be_removed.isnumeric():
                                    await m.reply(embed=makeEmbed("Trade remove failed.",
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
                                        await m.reply(embed=makeEmbed("Trade remove failed.",
                                                                      "Waifu not found in trade offer."))
                                    else:
                                        change = True
                        elif m.content.startswith(f"{PREFIX}trade {CURRENCY}"):
                            if not m.content.startswith(f"{PREFIX}trade {CURRENCY} "):
                                await m.reply(embed=makeEmbed(f"Adding {CURRENCY} failed.",
                                                              f"Usage: ``{PREFIX}trade {CURRENCY} [amount]``"))
                            else:
                                amount = m.content.split(" ", 2)[2]
                                if not amount.isnumeric():
                                    await m.reply(embed=makeEmbed(f"Adding {CURRENCY} failed.",
                                                                  f"Usage: ``{PREFIX}trade {CURRENCY} [amount]``"))
                                else:
                                    amount = int(amount)
                                    if m.author.id == user1.id:
                                        tmp_user_id = user1.id
                                    else:
                                        tmp_user_id = user2.id
                                    if amount > db.getUserCurrency(tmp_user_id):
                                        await m.reply(embed=makeEmbed(f"Adding {CURRENCY} failed.",
                                                                      f"You do not have enough {CURRENCY}."))
                                    else:
                                        change = True
                                        if m.author.id == user1.id:
                                            user1_currency = amount
                                        else:
                                            user2_currency = amount

                    except asyncio.TimeoutError:
                        timeout = True
                        break

                db.enableTrade(user1.id)
                db.enableTrade(user2.id)

                if cancel:
                    return await message.channel.send(
                        embed=makeEmbed("Trade Cancelled", "Trade has been cancelled."))
                elif timeout:
                    return await message.channel.send(embed=makeEmbed("Trade Cancelled", "Trade has timed out."))
                else:
                    if not db.trade(user1.id, user2.id, user1_offer, user2_offer, user1_currency, user2_currency):
                        return await message.channel.send(embed=makeEmbed("Trade Failed",
                                                                          "Something went wrong. The trade has been cancelled."))
                    return await message.channel.send(
                        embed=makeEmbed("Trade Succeeded", "Trade has been confirmed!"))

        elif message.content == f"{PREFIX}remove" or message.content.startswith(f"{PREFIX}remove ") or \
                message.content == f"{PREFIX}yeet" or message.content.startswith(f"{PREFIX}yeet "):
            args = getMessageArgs("remove", message) if message.content.startswith(f"{PREFIX}remove") \
                else getMessageArgs("yeet", message)
            if not args:
                return await message.reply(embed=makeEmbed("Command failed.",
                                                           f"Usages:\n``{PREFIX}remove [inventory number]``\n``{PREFIX}remove -s [show id]``"))
            if not db.canRemove(message.author.id):
                return await message.reply(embed=makeEmbed("Command failed.", "You are already removing right now."))
            if not db.canTrade(message.author.id):
                return await message.reply(
                    embed=makeEmbed("Command failed.", "Cannot remove while trading with someone."))
            else:
                inventory_index = None
                show_id = None
                selected_waifu = None
                cur_arg = args.pop(0)
                total_value = 0
                if cur_arg == "-s":
                    if args:
                        show_arg = args.pop(0)
                        if show_arg.isnumeric():
                            show_id = int(show_arg)
                else:
                    index_arg = cur_arg
                    if not index_arg.isnumeric():
                        return await message.channel.send(embed=makeEmbed("Command failed.",
                                                                          f"Usages:\n``{PREFIX}remove [inventory number]``\n``{PREFIX}remove -s [show id]``"))
                    inventory_index = int(index_arg)
                selected_waifus = db.getWaifus(message.author.id, unpaginated=True, inventory_index=inventory_index,
                                               show_id=show_id)
                if not selected_waifus:
                    return await message.channel.send(
                        embed=makeEmbed("404 Waifu Not Found", "Could not find this waifu in your inventory."))

                if db.canRemove(message.author.id) and db.canTrade(message.author.id):
                    db.disableRemove(message.author.id)
                else:
                    return await message.channel.send(
                        makeEmbed("Something went wrong.", "Unable to perform action."))

                if not show_id:
                    selected_waifu = selected_waifus[0]

                    if selected_waifu["favorite"] == 1:
                        db.enableRemove(message.author.id)
                        return await message.reply(embed=makeEmbed("Remove Blocked",
                                                                   f"""``{selected_waifu["index"]}`` **{selected_waifu["en_name"]}** is a favorite.\nIf you want to remove them from favorites, use ``{PREFIX}unfav [inventory slot]``"""))

                    description = f"""You are about to remove ``{selected_waifu["index"]}`` {makeRarityString(selected_waifu["rarity"])} **{selected_waifu["en_name"]}** #{selected_waifu["image_index"]}
Removing this waifu will award you **{db.getRarityCurrency(selected_waifu["rarity"])}** {CURRENCY}.
If you agree with this removal, respond with ``yes``.
Respond with anything else or wait {REMOVAL_TIMEOUT} seconds to cancel the removal."""
                    embed = makeEmbed("Waifu Removal Confirmation", description)
                    embed.set_thumbnail(url=selected_waifu["image_url"])
                    await message.reply(embed=embed)

                else:
                    description = f"""You are about to remove:\n"""

                    favorites = []
                    true_remove = []

                    for waifu in selected_waifus:
                        if waifu["favorite"] == 1:
                            favorites.append(waifu)
                        else:
                            true_remove.append(waifu)
                        total_value += db.getRarityCurrency(waifu["rarity"])
                        description += f"""``{waifu["index"]}`` {makeRarityString(waifu["rarity"])} **{waifu["en_name"]}** #{waifu["image_index"]}\n"""
                    description += f"""Removing these **{len(selected_waifus)}** waifus will award you **{total_value}** {CURRENCY}.\n"""

                    if favorites:
                        description += "\nIgnored favorites (won't be removed):\n"
                        for favorite in favorites:
                            description += f"""``{favorite["index"]}`` {makeRarityString(favorite["rarity"])} **{favorite["en_name"]}** #{favorite["image_index"]}{" :heart:" if favorite["favorite"] == 1 else ""}\n\n"""

                    description += f"""If you agree with this removal, respond with ``yes``.
Respond with anything else or wait {REMOVAL_TIMEOUT} seconds to cancel the removal."""
                    embed = makeEmbed("Waifus Removal Confirmation", description)
                    selected_waifus = true_remove
                    await message.reply(embed=embed)

                def userIsOriginalUser(incoming_message):
                    if incoming_message.author.id == message.author.id:
                        return True
                    return False

                confirm_message = None
                try:
                    confirm_message = await client.wait_for("message", check=userIsOriginalUser,
                                                            timeout=REMOVAL_TIMEOUT)
                except asyncio.TimeoutError:
                    pass

                if confirm_message and confirm_message.content.lower() == "yes":
                    # Remove waifu.
                    if not show_id:
                        if db.removeWaifu(selected_waifu["waifus_id"]):
                            new_currency = db.getRarityCurrency(selected_waifu["rarity"])
                            db.addUserCurrency(message.author.id, new_currency)
                            embed = makeEmbed("Waifu Let Go",
                                              f"""**{selected_waifu["en_name"]}** has been let go.\n:coin: Your {CURRENCY}: **{db.getUserCurrency(message.author.id)}** (+{new_currency})""")
                            embed.set_thumbnail(url=selected_waifu["image_url"])
                            db.enableRemove(message.author.id)
                            return await confirm_message.reply(embed=embed)
                        else:
                            db.enableRemove(message.author.id)
                            return await message.channel.send(embed=makeEmbed("Removal Failed",
                                                                              f"""Removal of **{selected_waifu["en_name"]}** failed."""))
                    else:
                        total_paid = 0
                        total_removed = 0
                        for waifu in selected_waifus:
                            if not db.removeWaifu(waifu["waifus_id"]):
                                db.enableRemove(message.author.id)
                                return await confirm_message.reply(embed=makeEmbed("Whoops",
                                                                                   f"""Something went wrong. (Removing nonexistent waifu?)\nStopped at waifu {waifu["waifus_id"]}.\nLet go of first {total_removed} waifus and paid out {total_paid}"""))
                            cur_pay = db.getRarityCurrency(waifu["rarity"])
                            db.addUserCurrency(message.author.id, cur_pay)
                            total_paid += cur_pay
                            total_removed += 1
                        embed = makeEmbed("Waifus Let Go",
                                          f"""{len(selected_waifus)} waifus have been let go.\n:coin: Your {CURRENCY}: **{db.getUserCurrency(message.author.id)}** (+{total_value})""")
                        db.enableRemove(message.author.id)
                        return await confirm_message.reply(embed=embed)
                else:
                    if not show_id:
                        db.enableRemove(message.author.id)
                        return await message.channel.send(embed=makeEmbed("Removal Cancelled",
                                                                          f"""Removal of **{selected_waifu["en_name"]}** has been cancelled."""))
                    else:
                        db.enableRemove(message.author.id)
                        return await message.channel.send(embed=makeEmbed("Removal Cancelled",
                                                                          f"""Removal of {len(selected_waifus)} waifus has been cancelled."""))

        elif message.content == f"{PREFIX}profile" or message.content.startswith(f"{PREFIX}profile "):
            args = getMessageArgs("profile", message)

            user = message.author
            if args:
                user_arg = args[0]
                if user_arg.startswith("<@"):
                    # It's a ping
                    user_id = pingToID(user_arg)
                else:
                    # Assume it's an ID
                    user_id = user_arg
                try:
                    # User in current Guild
                    if not message.guild:
                        return await message.reply(
                            embed=makeEmbed("User Lookup Failed", "You cannot look for users in DMs."))
                    user = await message.guild.fetch_member(user_id)
                except (discord.errors.NotFound, discord.errors.HTTPException):
                    # User not in current Guild
                    return await message.channel.send(embed=makeEmbed("Profile Lookup Failed",
                                                                      "Requested user is not in this server."))
            return await message.channel.send(embed=makeProfileEmbed(user))

        elif message.content == f"{PREFIX}roll" or message.content.startswith(f"{PREFIX}roll "):
            args = getMessageArgs("roll", message)
            if args:
                if len(args) > 1 or not args[0].isnumeric():
                    return await message.reply(embed=makeEmbed("Roll Failed", f"Usage: ``{PREFIX}roll [price]``"))
                price = int(args[0])
                if price < 100:
                    return await message.reply(
                        embed=makeEmbed("Roll Failed", f"Minimum roll price: 100 {CURRENCY}."))
            else:
                price = 100

            current_user_currency = db.getUserCurrency(message.author.id)
            if current_user_currency < price:
                return await message.reply(embed=makeEmbed("Roll Failed",
                                                           f"Not enough {CURRENCY}.\nCurrently: **{current_user_currency}**"))
            rolled_waifu, price = db.getDropData(price=price, user_id=message.author.id)
            db.addWaifu(message.author.id, rolled_waifu["image_id"], rolled_waifu["rarity"])
            return await message.reply(embed=makeRollEmbed(message.author, price, rolled_waifu))

        elif message.content == f"{PREFIX}fav" or message.content.startswith(f"{PREFIX}fav "):
            args = getMessageArgs("fav", message)
            if not args or len(args) > 1 or not args[0].isnumeric():
                return await message.reply(
                    embed=makeEmbed("Favorite Failed", f"Usage: ``{PREFIX}fav [inventory slot]``"))
            user_id = message.author.id

            inventory_index = int(args[0])

            selected_waifu = db.getWaifus(user_id, unpaginated=True, inventory_index=inventory_index)[0]
            if not selected_waifu:
                return await message.reply(
                    embed=makeEmbed("Favorite Failed", "Could not find waifu with that inventory number."))
            db.setFavorite(selected_waifu["waifus_id"])
            embed = makeEmbed("Waifu Favorited",
                              f"""``{selected_waifu["index"]}`` {makeRarityString(selected_waifu["rarity"])} **{selected_waifu["en_name"]}** #{selected_waifu["image_index"]}\nadded to favorites.""")
            embed.set_thumbnail(url=selected_waifu["image_url"])
            return await message.reply(embed=embed)

        elif message.content == f"{PREFIX}unfav" or message.content.startswith(f"{PREFIX}unfav "):
            args = getMessageArgs("unfav", message)
            if not args or len(args) > 1 or not args[0].isnumeric():
                return await message.reply(
                    embed=makeEmbed("Unfavorite Failed", f"Usage: ``{PREFIX}unfav [inventory slot]``"))
            user_id = message.author.id

            inventory_index = int(args[0])

            selected_waifu = db.getWaifus(user_id, unpaginated=True, inventory_index=inventory_index)[0]
            if not selected_waifu:
                return await message.reply(
                    embed=makeEmbed("Unfavorite Failed", "Could not find waifu with that inventory number."))
            db.unFavorite(selected_waifu["waifus_id"])
            embed = makeEmbed("Waifu Unfavorited",
                              f"""``{selected_waifu["index"]}`` {makeRarityString(selected_waifu["rarity"])} **{selected_waifu["en_name"]}** #{selected_waifu["image_index"]}\nremoved from favorites.""")
            embed.set_thumbnail(url=selected_waifu["image_url"])
            return await message.reply(embed=embed)

        elif message.content == f"{PREFIX}wager" or message.content.startswith(f"{PREFIX}wager "):
            args = getMessageArgs("wager", message)
            if not args or (args and not args[0].isnumeric()):
                return await message.reply(embed=makeEmbed("Wager Failed", f"Usage: ``{PREFIX}wager [amount]``"))
            wager = int(args[0])
            user_id = message.author.id
            current_user_currency = db.getUserCurrency(user_id)
            if current_user_currency < wager:
                return await message.reply(embed=makeEmbed("Wager Failed",
                                                           f"You don't have enough {CURRENCY}. Currently: **{current_user_currency}**"))
            if not db.subtractUserCurrency(user_id, wager):
                return await message.reply(
                    embed=makeEmbed("Wager Failed", f"Something went wrong. You did not gain/lose any {CURRENCY}."))
            win = numpyrand.choice((True, False))
            if win:
                db.addUserCurrency(user_id, wager * 2)
                return await message.reply(embed=makeEmbed("You Win!",
                                                           f"You doubled your wager!\n:coin: Your {CURRENCY}: **{db.getUserCurrency(user_id)}** (+{wager})"))
            else:
                return await message.reply(embed=makeEmbed("You Lose!",
                                                           f"Too bad, you lost your wager.\n:coin: Your {CURRENCY}: **{db.getUserCurrency(user_id)}** (-{wager})"))

        elif message.content == f"{PREFIX}view" or message.content.startswith(f"{PREFIX}view "):
            args = getMessageArgs("view", message)
            if not args or (args and not args[0].isnumeric()):
                return await message.reply(
                    embed=makeEmbed("Character Lookup Failed", f"Usage: ``{PREFIX}view [character ID]``"))
            char_id = int(args[0])
            waifu_info = db.getCharacterInfo(char_id)
            if not waifu_info:
                return await message.reply(
                    embed=makeEmbed("404 Waifu Not Found", "No character exists with this ID."))
            return await showCharacterInfoEmbed(waifu_info, message)

        elif message.content == f"{PREFIX}daily":
            print("hello")
            user_id = message.author.id
            if db.userCanDaily(user_id):
                db.addDailyCurrency(user_id)
                return await message.reply(embed=makeEmbed(f"Daily {CURRENCY.capitalize()} Received",
                                                           f"You received {db.DAILY_CURRENCY} {CURRENCY}!\n:coin: Your {CURRENCY}: **{db.getUserCurrency(user_id)}** (+{db.DAILY_CURRENCY})\nYou can claim again <t:{generateNextMidnight()}:R>."))
            else:
                return await message.reply(embed=makeEmbed(f"Already Claimed",
                                                           f"You've already claimed your daily {CURRENCY}.\nYou will be able to claim again <t:{generateNextMidnight()}:R>."))

        elif message.content == f"{PREFIX}give" or message.content.startswith(f"{PREFIX}give ") or \
                message.content == f"{PREFIX}gift" or message.content.startswith(f"{PREFIX}gift "):
            if message.content.startswith(f"{PREFIX}give"):
                args = getMessageArgs("give", message)
            else:
                args = getMessageArgs("gift", message)
            failed_embed = makeEmbed("Command Failed", f"Usage: ``{PREFIX}gift @user [amount]``")
            if not args or len(args) != 2:
                return await message.reply(embed=failed_embed)
            # Find out which is the ping
            if isMention(args[0]):
                mention_arg = args[0]
                amount_arg = args[1]
            else:
                mention_arg = args[1]
                amount_arg = args[0]

            recipient = await getUserInGuild(mention_arg, message.guild)
            if not recipient:
                return await message.reply(embed=makeEmbed("Command Failed", f"Recipient not found in server."))
            if recipient.id == message.author.id:
                return await message.reply(
                    embed=makeEmbed("Command Failed", f"Why are you trying to give {CURRENCY} to yourself? Baka."))
            if not amount_arg.isnumeric() or int(amount_arg) < 1:
                return await message.reply(embed=failed_embed)
            amount = int(amount_arg)
            sender_currency = db.getUserCurrency(message.author.id)
            if amount > sender_currency:
                return await message.reply(embed=makeEmbed("Command Failed",
                                                           f"You do not have enough {CURRENCY}.\n:coin: Your {CURRENCY}: **{sender_currency}**"))

            confirmation_embed = makeEmbed("Gift Confirmation",
                                           f"You are about to send **{amount}** {CURRENCY} to **{recipient.display_name}**.\nIf you agree with this transaction, send ``yes`` in this channel.\nSending anything else or waiting {GIFT_TIMEOUT} seconds will cancel this transaction.")
            confirmation_embed.set_thumbnail(url=getUserAvatarURL(recipient, 128))
            await message.reply(embed=confirmation_embed)

            def userIsOriginalUser(incoming_message):
                if incoming_message.author.id == message.author.id:
                    return True
                return False

            confirm_message = None
            try:
                confirm_message = await client.wait_for("message", check=userIsOriginalUser, timeout=GIFT_TIMEOUT)
            except asyncio.TimeoutError:
                pass

            if not confirm_message or not confirm_message.content.lower() == "yes":
                embed = makeEmbed("Gift Cancelled", "Your gift has been cancelled.")
                if not confirm_message:
                    return await message.reply(embed=embed)
                return await confirm_message.reply(embed=embed)

            # Gift confirmed
            if not db.subtractUserCurrency(message.author.id, amount):
                return await message.reply(
                    embed=makeEmbed("Gift Cancelled", f"Something went wrong.\nThe transaction is cancelled."))
            db.addUserCurrency(recipient.id, amount)
            embed = makeEmbed("Gift Successful",
                              f"You have given **{amount}** {CURRENCY} to **{recipient.display_name}**.\n:coin: Your {CURRENCY}: **{db.getUserCurrency(message.author.id)}** (-{amount})")
            embed.set_thumbnail(url=getUserAvatarURL(recipient, 128))
            return await confirm_message.reply(embed=embed)

        elif message.content == f"{PREFIX}upgrade" or message.content.startswith(f"{PREFIX}upgrade "):
            args = getMessageArgs("upgrade", message)
            failed_embed = makeEmbed("Command Failed", f"Usage: ``{PREFIX}upgrade [inventory slot]``")
            if not args or len(args) > 1 or not args[0].isnumeric() or int(args[0]) < 1:
                return await message.reply(embed=failed_embed)
            user_id = message.author.id
            upgrade_waifu = db.getWaifuOfUser(user_id, int(args[0]) - 1)
            if not upgrade_waifu:
                return await message.reply(embed=makeEmbed("Command Failed", f"No waifu found in your inventory with slot ``{args[0]}``."))
            current_upgrades = db.getUserUpgrades(user_id)
            cur_rarity = upgrade_waifu["rarity"]
            amount = UPGRADE_FROM_COSTS[cur_rarity]
            if not amount:
                return await message.reply(embed=makeEmbed("Upgrade Failed", f"Waifu cannot be upgraded further."))
            if amount > current_upgrades:
                return await message.reply(embed=makeEmbed("Upgrade Failed", f"You don't have enough upgrade parts needed to upgrade this waifu.\nNeeded: **{amount}** :nut_and_bolt:\nYou have: **{current_upgrades}** :nut_and_bolt:"))

            # Confirm upgrade
            confirmation_embed = makeEmbed("Upgrade Confirmation",
                                           f"""You are about to upgrade **{upgrade_waifu["en_name"]}**\nfrom {makeRarityString(cur_rarity)} to {makeRarityString(cur_rarity + 1)}.\n:nut_and_bolt: Your upgrade parts after upgrading will be: **{current_upgrades - amount}** (-{amount})\n\nIf you agree with this transaction, send ``yes`` in this channel.\nSending anything else or waiting {UPGRADE_TIMEOUT} seconds will cancel this transaction.""")
            confirmation_embed.set_thumbnail(url=upgrade_waifu["image_url"])
            await message.reply(embed=confirmation_embed)

            def userIsOriginalUser(incoming_message):
                if incoming_message.author.id == message.author.id:
                    return True
                return False

            confirm_message = None
            try:
                confirm_message = await client.wait_for("message", check=userIsOriginalUser, timeout=UPGRADE_TIMEOUT)
            except asyncio.TimeoutError:
                pass

            if not confirm_message or not confirm_message.content.lower() == "yes":
                embed = makeEmbed("Upgrade Cancelled", "Your upgrade has been cancelled.")
                if not confirm_message:
                    return await message.reply(embed=embed)
                return await confirm_message.reply(embed=embed)

            if not db.upgradeUserWaifu(user_id, upgrade_waifu["waifus_id"], amount):
                return await message.reply(embed=makeEmbed("Upgrade Failed", f"Something went wrong. Failed to upgrade waifu."))
            else:
                embed = makeEmbed("Upgrade Successful", f"""**{upgrade_waifu["en_name"]}** has been upgraded to {makeRarityString(cur_rarity + 1)}\n:nut_and_bolt: Your upgrade parts: **{current_upgrades - amount}** (-{amount})""")
                embed.set_thumbnail(url=upgrade_waifu["image_url"])
                return await message.reply(embed=embed)

    # Drops!
    if message.guild and not message.content.startswith(f"{PREFIX}") and db.canDrop(message.guild.id):
        if numpyrand.random() < calcDropChance(message.guild.member_count):
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
                while len(history) > HISTORY_SIZE:
                    history.pop(0)
                db.updateHistory(guild_id, history)
                assigned_channel = client.get_channel(assigned_channel_id)
                embed = makeEmbed("Waifu Drop!",
                                  f"""A waifu dropped, guess their name!\nHint: ``{nt.generateInitials(character_data)}``""")
                embed.set_image(url=character_data["image_url"])
                await assigned_channel.send(embed=embed)

                def isCorrectGuess(incoming_message):
                    if incoming_message.channel.id == assigned_channel_id:
                        if verifyGuess(incoming_message.content.lower(), character_data):
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
                                      f"""**{character_data["en_name"]}** gave up waiting.\nBetter luck next time!\nMAL ID: [{character_data["char_id"]}](https://myanimelist.net/character/{character_data["char_id"]})""")
                    embed.set_image(url=character_data["image_url"])
                    return await assigned_channel.send(embed=embed)
                db.enableDrops(guild_id)
                db.addWaifu(guess.author.id, character_data["image_id"], character_data["rarity"])
                random_bonus = round(numpyrand.uniform(50, 125))
                db.addUserCurrency(guess.author.id, random_bonus)
                upgrade = dropUpgrade()
                if upgrade:
                    db.addUserUpgrades(guess.author.id, 1)
                return await guess.reply(embed=makeDropClaimEmbed(guess.author, character_data, random_bonus, upgrade))
    return


def pingToID(ping_string):
    out = ""
    for char in ping_string:
        if char.isnumeric():
            out += char
    return int(out)


def dropUpgrade():
    if bot_token.isDebug():
        return True
    return numpyrand.random() < 0.1


def calcDropChance(user_count):
    if bot_token.isDebug():
        return 1
    else:
        return min(0.1, (1 / (user_count / 10)))
    # return min(0.1, (1 / (user_count / 10)))


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


def getMessageArgs(command, message):
    return message.content.replace(f"{PREFIX}{command}", "").strip().split()


async def getUserInGuild(requested_user, guild):
    """
    Gets user object from ping or user ID.
    Returns None if user not found in guild.
    :param requested_user: string - User ping or ID
    :param guild: Guild Object - The guild to search the user in.
    :return: User Object
    """
    if isMention(requested_user):
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


def makeRarityString(rarity):
    rarity = int(rarity)

    if rarity < 5:
        max_rarity = 4
        out = "★"
        out += "★" * rarity
        out += "☆" * (max_rarity - rarity)
    else:
        out = "✪✪✪✪✪"

    return out


def generateNextMidnight():
    midnight = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    next_midnight = midnight + datetime.timedelta(days=1)
    return round(time.mktime(next_midnight.timetuple()))


def isMention(argument):
    return argument.startswith("<@") and argument.endswith(">")


def getUserAvatarURL(user, resolution):
    return f"{user.avatar_url}?size={resolution}"


async def showNormalWaifusPage(message, user_id, user_name, cur_page, rarity, name_query, show_id):
    org_embed, total_pages, cur_page = getWaifuPageEmbed(user_id, user_name, cur_page, rarity, name_query, show_id)
    if total_pages < 0:
        return await message.channel.send(embed=org_embed)
    own_message = await message.channel.send(embed=org_embed)
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

        if new_page < 0:
            new_page = total_pages - 1
        elif new_page + 1 > total_pages:
            new_page = 0

        cur_page = new_page
        embed, total_pages, cur_page = getWaifuPageEmbed(user_id, user_name, cur_page, rarity, name_query, show_id)
        if total_pages < 0:
            return await message.channel.send(embed=embed)
        if message.guild:
            await own_message.edit(embed=embed)
            await own_message.remove_reaction(reaction, user)
        else:
            # Workaround because you cannot remove another user's reactions in a DM channel.
            own_message = await message.channel.send(embed=org_embed)
            await own_message.add_reaction(NAV_LEFT_EMOJI)
            await own_message.add_reaction(NAV_RIGHT_EMOJI)
    return


async def showCharacterInfoEmbed(waifu_info, message):
    cur_image = 0
    total_images = len(waifu_info["image_urls"])
    own_message = await message.channel.send(embed=makeCharacterInfoEmbed(waifu_info, cur_image))
    await own_message.add_reaction(NAV_LEFT_EMOJI)
    await own_message.add_reaction(NAV_RIGHT_EMOJI)

    def isValidNavigation(r, u):
        if u != client.user and r.message.id == own_message.id and u.id == message.author.id:
            if r.emoji in NAV_EMOJI:
                return True
        return False

    while True:
        try:
            reaction, user = await client.wait_for("reaction_add", check=isValidNavigation, timeout=CHARACTER_TIMEOUT)
        except asyncio.TimeoutError:
            break
        # Reaction received, edit message.
        new_image = cur_image + NAV_EMOJI[reaction.emoji]

        if new_image < 0:
            new_image = total_images - 1
        elif new_image + 1 > total_images:
            new_image = 0

        cur_image = new_image
        if message.guild:
            await own_message.edit(embed=makeCharacterInfoEmbed(waifu_info, cur_image))
            await own_message.remove_reaction(reaction, user)
        else:
            # Workaround because you cannot remove another user's reactions in a DM channel.
            own_message = await message.channel.send(embed=makeCharacterInfoEmbed(waifu_info, cur_image))
            await own_message.add_reaction(NAV_LEFT_EMOJI)
            await own_message.add_reaction(NAV_RIGHT_EMOJI)
    return


def makeEmbed(title, desciption):
    return discord.Embed(type="rich",
                         title=title,
                         description=desciption,
                         color=EMBED_COLOR,
                         timestamp=datetime.datetime.utcnow())


def getWaifuPageEmbed(user_id, user_name, cur_page, rarity, name_query, show_id):
    page_data = db.getWaifus(user_id, rarity=rarity, name_query=name_query, page_size=PROFILE_PAGE_SIZE, show_id=show_id)
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
            f"""``{waifu["index"]}`` {makeRarityString(waifu["rarity"])} **{waifu["en_name"]}** #{waifu["image_index"]}{" :heart:" if waifu["favorite"] == 1 else ""}""")
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
    description = ""
    if waifu_data["jp_name"]:
        description += f"""{waifu_data["jp_name"]}\n"""
    description += f"""{makeRarityString(waifu_data["rarity"])}\n"""
    description += f"""Image #{waifu_data["image_index"]}\n"""
    description += f"""MAL ID: [{waifu_data["id"]}](https://myanimelist.net/character/{waifu_data["id"]})\n"""
    upgrade_cost = UPGRADE_FROM_COSTS[waifu_data["rarity"]]
    if not upgrade_cost:
        description += f"""Cannot be upgraded further."""
    else:
        description += f"""Upgrade cost: {UPGRADE_FROM_COSTS[waifu_data["rarity"]]} :nut_and_bolt:"""

    embed = makeEmbed(f"""{waifu_data["en_name"]}""", description)
    embed.set_image(url=waifu_data["image_url"])
    embed.set_footer(text=f"{user_name}'s Waifu #{inventory_index}")

    return await message.channel.send(embed=embed)


def makeShowsListEmbed(shows_list):
    shows_strings = []
    for show in shows_list:
        shows_strings.append(
            f"""``{show["id"]}`` **{show["jp_title"]}** ({"Anime" if not show["is_manga"] else "Manga"})""")

    embed = makeEmbed("Show Search", "\n".join(shows_strings))
    return embed


def makeShowWaifusEmbed(show_title_jp, characters):
    characters_string = []
    for character in characters:
        characters_string.append(
            f"""``{character["char_id"]}`` **{character["en_name"]}** | {character["image_count"]} image{"s" if character["image_count"] > 1 else ""}""")
    embed = makeEmbed(f"{show_title_jp}", "\n".join(characters_string))
    return embed


def makeTradeEmbed(user1, user2, user1_offer, user2_offer, user1_currency, user2_currency, user1_confirm, user2_confirm):
    description = ""

    description += f"**{user1.display_name}**'s offer:\n"
    if not user1_offer and user1_currency == 0:
        description += "``Empty``\n"
    else:
        if user1_currency > 0:
            description += f"""{CURRENCY.capitalize()}: **{user1_currency}**\n"""
        for waifu in user1_offer:
            description += f"""{waifu["index"]} | {waifu["char_id"]} **{waifu["en_name"]}** R:{makeRarityString(waifu["rarity"])} #{waifu["image_index"]}\n"""
    description += f"""{":white_check_mark: Confirmed" if user1_confirm else ":x: Unconfirmed"}\n"""

    description += f"\n**{user2.display_name}**'s offer:\n"
    if not user2_offer and user2_currency == 0:
        description += "``Empty``\n"
    else:
        if user2_currency > 0:
            description += f"""{CURRENCY.capitalize()}: **{user2_currency}**\n"""
        for waifu in user2_offer:
            description += f"""{waifu["index"]} | {waifu["char_id"]} **{waifu["en_name"]}** R:{makeRarityString(waifu["rarity"])} #{waifu["image_index"]}\n"""
    description += f"""{":white_check_mark: Confirmed" if user2_confirm else ":x: Unconfirmed"}\n"""

    description += f"""\nAdd waifus with ``{PREFIX}trade add [inventory number]``\nConfirm trade with ``{PREFIX}trade confirm``\nCancel trade with ``{PREFIX}trade cancel``\nFor more features, check ``{PREFIX}help trade``"""

    embed = makeEmbed("Waifu Trade Offer", description)
    return embed


def makeProfileEmbed(user):
    cur_currency = db.getUserCurrency(user.id)
    cur_upgrades = db.getUserUpgrades(user.id)

    title = f"""{user.display_name}'s Profile"""
    descr = f""":coin: {cur_currency} {CURRENCY if cur_currency != 1 else CURRENCY[:-1]}\n"""
    descr += f""":nut_and_bolt: {cur_upgrades} upgrade part{"s" if cur_upgrades != 1 else ""}"""

    embed = makeEmbed(title, descr)
    embed.set_thumbnail(url=getUserAvatarURL(user, 128))
    return embed


def makeRollEmbed(user, price, rolled_waifu):
    title = f"{user.display_name}'s Gacha Roll!"
    descr = f"""You rolled **{rolled_waifu["en_name"]}**.\n"""
    descr += f"""{makeRarityString(rolled_waifu["rarity"])}\n"""
    descr += f"""MAL ID: [{rolled_waifu["char_id"]}](https://myanimelist.net/character/{rolled_waifu["char_id"]})\n"""
    descr += f"""They have filled inventory slot ``{len(db.getWaifus(user.id, unpaginated=True))}``.\n"""
    descr += f""":coin: Your {CURRENCY}: **{db.getUserCurrency(user.id)}** (-{price})\n"""

    embed = makeEmbed(title, descr)
    embed.set_image(url=rolled_waifu["image_url"])
    return embed


def makeCharacterInfoEmbed(waifu_info, cur_image):

    title = waifu_info["en_name"]
    descr = ""
    if waifu_info["jp_name"]:
        descr += f"""{waifu_info["jp_name"]}\n"""
    descr += f"""[{waifu_info["char_id"]}](https://myanimelist.net/character/{waifu_info["char_id"]})\n"""
    descr += f"""**{len(waifu_info["image_urls"])}** images\n"""
    descr += f"""Favorited **{waifu_info["favorites"]}** time{'' if waifu_info["favorites"] == 1 else 's'}\n"""
    descr += f"""\nNumber collected: **{waifu_info["waifu_count"]}**\n"""
    for i in range(0, 6):
        descr += f"""{makeRarityString(i)}: {waifu_info["rarity_count"][i] if i in waifu_info["rarity_count"] else 0}\n"""

    embed = makeEmbed(title, descr)
    embed.set_footer(text=f"""Image #{cur_image + 1} of {len(waifu_info["image_urls"])}""")
    embed.set_image(url=waifu_info["image_urls"][cur_image])

    return embed


def makeDropClaimEmbed(user, character_data, random_bonus, upgrade):
    title = "Waifu Claimed!"
    descr = f"""**{user.display_name}** is correct!\n"""
    descr += f"""You've claimed **{character_data["en_name"]}**.\n"""
    descr += f"""{makeRarityString(character_data["rarity"])}\n"""
    descr += f"""MAL ID: [{character_data["char_id"]}](https://myanimelist.net/character/{character_data["char_id"]})\n"""
    descr += f"""They have filled inventory slot ``{db.getWaifusAmount(user.id)}``.\n"""
    descr += f""":coin: Your {CURRENCY}: **{db.getUserCurrency(user.id)}** (+{random_bonus})"""
    if upgrade:
        descr += f"""\nYou also found an upgrade part!\n"""
        descr += f""":nut_and_bolt: Your upgrade parts: **{db.getUserUpgrades(user.id)}** (+1)"""
    embed = makeEmbed(title, descr)
    embed.set_image(url=character_data["image_url"])
    return embed


client.run(bot_token.getToken())
