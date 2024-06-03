import asyncio
import os
import time
import re
from urllib.parse import urlparse

import aiohttp.client_exceptions
import discord
from discord.ext import tasks
import random
import shlex
import textwrap

import command as cmd
import constants
import database_tools as db
import display
import internet
import mal_tools
from drop import Drop
import name_tools as nt
from show import Show
from trade import Trade
import uma
import util
import waifu_filter
import nao
from waifu import Waifu, Character
import logging
logger = logging.getLogger('discord')

_command_map = dict()

def command(*commands, **kwargs):
    """ Decorator to add a command to the bot. """
    global _command_map

    command_object = cmd.Command(**kwargs)

    def add_command(function):
        global _command_map

        command_object.set_function(function)

        for command_name in commands:
            _command_map[command_name] = command_object

        return function

    return add_command



class AnimeCharGuessBot(discord.Client):
    command_map = None

    def __init__(self, token, prefix, admins, currency, resource_server, resource_channel, **kwargs):
        super().__init__(**kwargs)
        
        self.token = token
        self.prefix = prefix
        self.admins = admins
        self.currency = currency
        self.resource_server = resource_server
        self.resource_channel_id = resource_channel
        self.resource_channel = None
        self.show_queue = mal_tools.ShowQueue()
        self.cooldowns = {}

        self.active_trades = set()
        self.active_drops = dict()

        self.uma_running = False


    async def on_ready(self):
        """
        Runs on the bot connecting to Discord for the first time.
        """
        constants.BOT_OBJECT = self

        db.enable_all_trades()
        db.enable_all_removes()

        await internet.send_downtime_message(from_reboot=True)

        logger.info(f"Bot has logged in as {self.user}")
        for g in self.guilds:
            logger.info(f"{g.name}, {g.id}")
            if g.id == self.resource_server:
                self.resource_channel = await g.fetch_channel(self.resource_channel_id)

        logger.info(f"Resource channel: {self.resource_channel.id}")

        # loop = asyncio.get_event_loop()
        # loop.create_task(uma.run())


    async def on_guild_remove(self, guild):
        db.remove_guild(guild.id)


    async def on_message(self, message):
        """
        Runs every time the bot can see a new message.

        Used for two things:
            - Handling commands
            - Triggering random drops
        """

        # Ignore messages from bots, including this one.
        if message.author.bot:
            return
        
        # # If the message has images, check for unsourced images.
        await nao.check_images(message)

        # Makes the bot completely case insensitive.
        message_content = message.content.lower()
        
        if message_content.startswith(self.prefix):
            # This message is a command.

            # Strip the prefix and read the command.
            without_prefix = message_content[len(self.prefix):]
            
            split_command = without_prefix.split(maxsplit = 1)
            command_name = split_command[0]

            if len(split_command) == 2:
                arguments_string = split_command[1]
            else:
                arguments_string = ''

            # Try and find the requested command.
            command_object = AnimeCharGuessBot.command_map.get(command_name)

            if command_object:
                # The command exists, run it.
                is_server_admin = message.channel.permissions_for(message.author).administrator
                is_bot_admin = self.is_bot_admin(message.author.id)
                is_in_cooldown = self.is_in_cooldown(message.author.id)

                arguments = cmd.CommandArguments(
                    message = message,
                    command = command_name,
                    arguments_string = arguments_string,
                    is_server_admin = is_server_admin,
                    is_bot_admin = is_bot_admin,
                    is_in_cooldown = is_in_cooldown
                )

                try:
                    await command_object.run(self, arguments)
                except aiohttp.client_exceptions.ClientConnectorError:
                    await self.on_disconnect()

        elif message_content and message.guild:
            # Not a command, but we are in a guild
            
            # Handle Twitter/X links
            await self.fix_urls(message, ['twitter.com', 'x.com'], "https://vxtwitter.com")
            await self.fix_urls(message, ['pixiv.net'], "https://phixiv.net")
            
            # We might want to drop or check if a drop guess is correct.
            drop = self.active_drops.get(message.guild.id)

            if isinstance(drop, Drop) and message.channel.id == db.get_assigned_channel_id(message.guild.id) and drop.guess_matches(message_content):
                # A drop is currently running, and the message was a correct guess, so reward the guesser.
                del self.active_drops[message.guild.id]
                await self.give_drop(drop, message)

            elif drop is None and random.random() < self.drop_chance(message.guild):
                # A drop was not running, so start one.
                await self.drop(message.guild)


    async def on_disconnect(self):
        await internet.handle_disconnect()
        return


    async def send_admin_dm(self, embed):
        for admin_id in self.admins:
            admin_user = await self.fetch_user(admin_id)
            await admin_user.send(embed=embed)
        return


    async def send_uma_embed(self, embed, do_ping=False):
        uma_channel = self.get_channel(int(os.environ[f'{constants.ENVVAR_PREFIX}UMA_CHANNEL']))
        if uma_channel:
            uma_role = uma_channel.guild.get_role(950481988928823296)  # TODO: Replace this hardcoded id
            if uma_role and do_ping:
                await uma_channel.send(uma_role.mention, embed=embed)
            else:
                await uma_channel.send(embed=embed)
        return


    def format(self, message):
        """
        Formats a string with constants defined by the bot. (And also the next daily reset.)

        Used by help messages, as they are not created dynamically.
        """

        return message.replace('%PREFIX%', self.prefix).replace('%CURRENCY%', self.currency).replace('%DAILYRESET%', str(util.next_daily_reset()))
    

    def drop_chance(self, guild):
        """
        Get the chance per message of a random drop happening in a guild.
        """

        # return 10 / max(100, (guild.member_count * 0.75))
        return 10.0 / max(100, (guild.member_count * 0.25))


    def is_bot_admin(self, user_id):
        """
        Check if a user is an admin of the bot.
        """

        return str(user_id) in self.admins


    def is_in_cooldown(self, user_id):
        """
        Check if a user is currently in cooldown.
        """
        return time.time() - self.cooldowns.get(user_id, 0) < constants.COOLDOWN_SECONDS


    def set_cooldown(self, user_id):
        """
        Sets the cooldown time of a user.
        """
        self.cooldowns[user_id] = time.time()


    def run(self):
        """
        Creates an event loop and runs the bot, blocking.
        """

        super().run(self.token)
    

    def start_trade(self, user1, user2):
        """
        Creates a trade between two users.
        """

        if user1.id == user2.id or not db.can_trade(user1.id, self) or not db.can_trade(user2.id, self) or not db.can_remove(user1.id) or not db.can_remove(user2.id):
            return None

        trade = Trade(user1, user2)

        trade.mark_users_as_trading()

        self.active_trades.add(trade)

        return trade
    

    def remove_trade(self, trade):
        """
        Removes a trade and allows the participating users to trade again.
        """

        self.active_trades.remove(trade)
        trade.mark_trade_over()


    def timeout_trades(self):
        """
        Quietly remove any trades that have been inactive for too long.
        """

        timed_out = []

        for trade in self.active_trades:
            if trade.is_timeout():
                timed_out.append(trade)

        for trade in timed_out:
            self.remove_trade(trade)


    def get_trade_involving(self, user_id):
        """
        Finds what trade, if any, a user is currently part of.
        """

        self.timeout_trades()

        for trade in self.active_trades:
            if user_id in trade:
                return trade
    

    async def yes_message(self, orig_msg, timeout = constants.REMOVAL_TIMEOUT):
        """
        Waits for a user to say "yes" or a timeout to occur.

        Returns if "yes" was said, and the confimation or denial message.
        """

        try:
            next_msg = await self.wait_for('message', check = lambda msg: msg.author.id == orig_msg.author.id, timeout = timeout)
        except asyncio.TimeoutError:
            return False, orig_msg

        return ((next_msg.channel and next_msg.channel.id) == (orig_msg.channel and orig_msg.channel.id) and next_msg.content.lower() == 'yes'), next_msg


    async def drop(self, guild):
        """
        Run a random drop in a guild.
        """
        # return

        assigned_channel_id = db.get_assigned_channel_id(guild.id)

        if not assigned_channel_id:
            # Guild has no assigned channel, so don't drop.
            return

        channel = self.get_channel(assigned_channel_id)

        if not channel:
            # Assigned channel does not exist, so don't drop.
            return


        drop = self.active_drops.get(guild.id)

        # Mark the channel as having a drop, so new drops aren't created when there is already one being made
        self.active_drops[guild.id] = True

        # If the channel already had a drop, a new one was forced. Show the timeout embed for it before replacing.
        if isinstance(drop, Drop):
            self.active_drops[guild.id] = True
            await channel.send(embed = drop.create_timeout_embed())

        drop = await Drop.create(channel)

        self.active_drops[guild.id] = drop

        await channel.send(embed = drop.create_guess_embed())

        await asyncio.sleep(constants.DROP_TIMEOUT)

        if self.active_drops.get(guild.id) is drop:
            # After timeout, this is still the active drop, so cancel it and reveal the answer.
            del self.active_drops[guild.id]
            await channel.send(embed = drop.create_timeout_embed())


    async def give_drop(self, drop, message):
        """
        Reward a user for guessing a drop.
        """

        bonus = random.randint(50, 125)
        upgrade = not random.randint(0, 9)

        db.add_user_currency(message.author.id, bonus)
        db.add_waifu(message.author.id, drop.waifu.image_id, drop.waifu.rarity)

        lines = [
            f'**{message.author.display_name}** is correct!',
            f"You've claimed **{drop.waifu.character.en_name}**.",
            display.rarity_string(drop.waifu.rarity),
            drop.waifu.character.source_string(),
            f'They have filled inventory slot ``{db.get_waifusAmount(message.author.id)}``.',
            f':coin: Your {self.currency}: **{db.get_user_currency(message.author.id)}** (+{bonus})'
        ]

        if upgrade:
            db.add_user_upgrades(message.author.id, 1)
            lines.append(f'You also found an upgrade part!\n:nut_and_bolt: Your upgrade parts: **{db.get_user_upgrades(message.author.id)}** (+1)')

        await message.reply(embed = display.create_embed(
            'Waifu Claimed!',
            '\n'.join(lines),
            image = drop.waifu.image_url
        ))
    
    async def fix_urls(self, message, domains_list, new_prefix, suppress=True):
        url_regex = r'https?:\/\/[^\s]+'
        urls = re.findall(url_regex, message.content)

        vxtwitter_urls = []

        for url in urls:
            # Skip suppressed URLs.
            if url.endswith('>'):
                continue

            try:
                parsed_url = urlparse(url)
            except:
                continue
            domain = parsed_url.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            if domain in domains_list:
                vx_url = new_prefix + parsed_url.path
                vxtwitter_urls.append(vx_url)
        
        if vxtwitter_urls:
            reply = await message.reply('\n'.join(vxtwitter_urls), mention_author=False)
            # view = display.DeleteButtonView(message.author, reply, 20)
            # await reply.edit(view=view)

            if suppress:
                # Hide the original embed as well as check if it's been deleted.
                @tasks.loop(seconds=2, count=30)
                async def hide_embed():
                    try:
                        await message.edit(suppress=True)
                    except discord.errors.NotFound:
                        await reply.delete()
                        hide_embed.stop()
                    return

                hide_embed.start()
        
        return


    async def send_character_images(self, normal_path, mirror_path, upside_down_path):
        """
        Sends images to the resource channel and returns the image URLs.
        """
        files = (discord.File(fp=normal_path),
                 discord.File(fp=mirror_path),
                 discord.File(fp=upside_down_path))
        message = await self.resource_channel.send(files=files)
        return [attachment.url for attachment in message.attachments]


    @command('a.reboot', require_bot_admin=True, only_in_assigned_channel=False)
    async def command_admin_reboot(self, args):
        """
        Reboots the bot. (Bot admin only)

        When this command is executed, the bot will be restarted.
        """

        if args.arguments_string:
            return cmd.BAD_USAGE

        await args.message.reply(embed = display.create_embed("Rebooting.", "Now rebooting..."))
        internet.reboot()


    @command('a.drop', require_bot_admin = True)
    async def command_admin_drop(self, args):
        """
        Force a drop to occur. (Bot admin only)

        Forces a drop to occur in this guild. If there is already a drop running, it will be cancelled.
        """

        if args.arguments_string:
            return cmd.BAD_USAGE

        await self.drop(args.guild)


    @command('a.setmoney', require_bot_admin = True)
    async def command_admin_setmoney(self, args):
        """
        Change a user's money. (Bot admin only)

        Usage: ``%PREFIX%%COMMAND% [user] <money>``
        """

        arg_list = args.arguments_string.split()

        if len(arg_list) == 1:
            user = args.user

        elif len(arg_list) == 2:
            user = await util.parse_user(arg_list[0], args.guild)

        else:
            return cmd.BAD_USAGE

        if not arg_list[-1].isnumeric():
            return cmd.BAD_USAGE

        target = int(arg_list[-1])
        wealth = db.get_user_currency(user.id)
        change = target - wealth
        db.add_user_currency(user.id, change)

        await args.message.reply(embed = display.create_embed(
            'Money Updated',
            f"**{user.display_name}**'s {self.currency} changed from {wealth} to **{target}** ({change:+})."
        ))


    @command('a.add', require_bot_admin=True)
    async def command_admin_add(self, args):
        """
        Adds a new show to the bot. (Bot admin only)

        Places a MAL URL into the adding queue.
        Usage: ``%PREFIX%a.add <MAL URL>``
        """

        if not args.arguments_string:
            return cmd.BAD_USAGE

        url_string = args.arguments_string

        self.show_queue.add_url(url_string)

        await args.message.reply(embed = display.create_embed("Show added to queue", f"Queue length: {len(self.show_queue)}"))

        if not self.show_queue.running:
            self.show_queue.running = True
            await mal_tools.run_queue(self.show_queue)

        return

    @command('a.queue', require_bot_admin=True)
    async def command_admin_queue(self, args):
        """
        Displays the bot's show queue.
        """
        await display.page(self, args, self.show_queue.show_queue, "Current show queue.")


    @command('a.update', require_bot_admin=True)
    async def command_admin_update(self, args):
        """
        Developer command that does whatever the dev wants it to do right now.
        """
        skip = args.arguments_string
        if skip != '':
            if skip.isnumeric():
                skip = int(skip)
            else:
                args.message.reply(embed = display.create_embed("Incorrect argument", "Not a number"))
                return
        else:
            skip = None

        show_urls = db.get_all_show_mal_urls()
        if skip:
            show_urls = show_urls[skip:]

        for show_url in show_urls:
            self.show_queue.add_url(show_url)
        
        if not self.show_queue.running:
            self.show_queue.running = True
            await mal_tools.run_queue(self.show_queue)
        
        return


    @command('a.log', require_bot_admin=True)
    async def command_admin_log(self, args):
        """
        DM the last log messages to the developer.
        """
        amount = args.arguments_string
        if not amount:
            amount = 1
        elif not amount.isnumeric() or int(amount) > 50 or int(amount) < 1:
            await args.message.reply(embed = display.create_embed("Incorrect argument", "Please enter a valid number."))
            return
        
        amount = int(amount)

        log_lines = list()
        with open(constants.LOG_FILE, "r") as log_file:
            lines = log_file.read().splitlines()
            if amount > len(lines):
                amount = len(lines)
            log_lines = lines[-amount:]
        
        await self.send_admin_dm(display.create_embed("Log snippet", "```" + "\n".join(["    " + line for line in log_lines]) + "```"))
        await args.message.reply(embed = display.create_embed("Log sent", "A log snippet has been sent to the developer."))
        return
        

    # @command('a.changename', require_bot_admin=True)
    # async def command_admin_changename(self, args):
    #     """
    #     Changes the English name of a character.
    #     """
    #     if not args.arguments_string:
    #         return cmd.BAD_USAGE
    #
    #     arg_list = args.arguments_string.split(" ", 1)
    #
    #     if len(arg_list) != 2:
    #         return cmd.BAD_USAGE
    #
    #     char_id, en_name = arg_list
    #
    #     if not db.character_exists(char_id):
    #         return await
    #
    #     await db.change_name(char_id, en_name)

    @command('assign', require_server_admin = True, only_in_assigned_channel = False)
    async def command_assign(self, args):
        """
        Assign the bot to a channel. (Admin only)

        Assigns the bot to a channel. The bot will only respond to messages in the channel it has been assigned.
        """

        if args.arguments_string:
            return cmd.BAD_USAGE

        db.assign_channel_to_guild(args.channel.id, args.guild.id)
        await args.message.reply(embed = display.create_embed(
            'Channel Assigned!',
            f"I've been assigned to channel ``#{args.channel.name}``"
        ))
    

    @command('daily')
    async def command_daily(self, args):
        """
        Claim daily %CURRENCY%.

        Claim your daily %CURRENCY%.
        Resets at <t:%DAILYRESET%:t>.
        """

        if args.arguments_string:
            return cmd.BAD_USAGE

        daily_reset = util.next_daily_reset()
        daily_reset = f'<t:{daily_reset}:R>'

        if db.user_can_daily(args.user.id):
            db.add_daily_currency(args.user.id)
            
            wealth = db.get_user_currency(args.user.id)
            await args.message.reply(embed = display.create_embed(
                f'Daily {self.currency.capitalize()} Received',
                f'You received {db.DAILY_CURRENCY}!\n'
                f':coin: Your {self.currency}: **{wealth}** (+{db.DAILY_CURRENCY})\n'
                f'You can claim again {daily_reset}.'
            ))

        else:
            await args.message.reply(embed = display.create_embed(
                'Already Claimed',
                f"You've already claimed your daily {self.currency}.\n"
                f'You will be able to claim again {daily_reset}.'
            ))


    @command('drop')
    async def command_drop(self, args):
        """
        See what the current random drop is.
        """

        if args.arguments_string:
            return cmd.BAD_USAGE
        
        if not args.guild:
            await args.message.reply(embed = display.create_embed(
                'No Drop',
                'Drops are not available in DMs.'
            ))
            return

        drop = self.active_drops.get(args.guild.id)

        if isinstance(drop, Drop):
            await args.message.reply(embed = drop.create_guess_embed())

        else:
            await args.message.reply(embed = display.create_embed(
                'No Drop',
                'There is not currently a drop running.'
            ))


    # These commands are handled by the same function as they are mostly the same.
    @command('fav', 'unfav')
    async def command_fav(self, args):
        """
        Favorite or unfavourite a waifu.

        Add or remove a waifu in your inventory from your favorites.

        Usage:
        ``%PREFIX%fav <inventory number> ...`` or
        ``%PREFIX%unfav <inventory number> ...``
        """

        try:
            indices = [int(i) for i in args.arguments_string.split()]

        except ValueError:
            return cmd.BAD_USAGE

        if not indices:
            return cmd.BAD_USAGE

        adding = args.command == 'fav'

        changed = []

        for i in indices:
            waifu = Waifu.from_user_index(args.user, i)

            if waifu:
                if adding:
                    db.set_favorite(waifu.waifu_id)
                else:
                    db.unfavorite(waifu.waifu_id)

                changed.append(waifu)

            # We don't want to show the heart emoji here.
            waifu.fav = False

        if changed:
            lines = [
                *(str(waifu) for waifu in changed),
                'added to favorites.' if adding else 'removed from favorites.'
            ]

            await args.message.reply(embed = display.create_embed(
                'Waifu Favorited' if adding else 'Waifu Unfavorited',
                '\n'.join(lines),
                thumbnail = waifu.image_url
            ))
            
        else:
            await args.message.reply(embed = display.create_embed(
                'Favorite Failed' if adding else 'Unfavorite Falied',
                'That waifu was not found in your inventory'
            ))
    

    @command('give', 'gift')
    async def command_give(self, args):
        """
        Give a user %CURRENCY%.

        Gift some of your %CURRENCY% to someone else.

        Usage: ``%PREFIX%%COMMAND% <user> <amount> [-y]``
        """

        arg_list = args.arguments_string.split()

        yes_flag = False

        if '-y' in arg_list:
            yes_flag = True
            arg_list.remove('-y')

        if len(arg_list) != 2 or not arg_list[1].isnumeric():
            return cmd.BAD_USAGE

        if not args.guild:
            return cmd.NO_LOOKUP_IN_DM

        recipient = await util.parse_user(arg_list[0], args.guild)
        amount = int(arg_list[1])

        if recipient is None:
            return cmd.USER_NOT_FOUND

        if recipient.id == args.user.id:
            await args.message.reply(embed = display.create_embed(
                'Command Failed',
                'You cannot send money to yourself.'
            ))
            return

        wealth = db.get_user_currency(args.user.id)

        if amount > wealth:
            await args.message.reply(embed = display.create_embed(
                'Gift Failed',
                f'You do not have enough {self.currency}.'
            ))
            return

        reply_to = args.message

        if not yes_flag:
            await args.message.reply(embed = display.create_embed(
                'Gift Confirmation',
                f'You are about to send **{amount}** {self.currency} to **{recipient.display_name}**.\n'
                f'If you agree to this transaction, say ``yes`` in this channel.\n'
                f'Saying anything else or waiting {constants.GIFT_TIMEOUT} seconds will cancel.',
                thumbnail = util.avatar(recipient)
            ))

            confirm, reply_to = await self.yes_message(args.message, timeout = constants.GIFT_TIMEOUT)

            if not confirm:
                await reply_to.reply(embed = display.create_embed(
                    'Gift Cancelled',
                    'You gift has been cancelled.'
                ))

                return

        if not db.subtract_user_currency(args.user.id, amount):
            await reply_to.reply(embed = display.create_embed(
                'Gift Failed',
                'Something went wrong.'
            ))

            return

        db.add_user_currency(recipient.id, amount)

        await reply_to.reply(embed = display.create_embed(
            'Gift Successful',
            f'You have given **{amount}** {self.currency} to **{recipient.display_name}**.\n'
            f':coin: Your {self.currency}: **{wealth - amount}** (-{amount})',
            thumbnail = util.avatar(recipient)
        ))


    @command('help', only_in_assigned_channel = False)
    async def command_help(self, args):
        """
        Show this help message. Use ``%PREFIX%help [command]`` to get help for a specific command.

        Display information about a command. Use ``%PREFIX%help`` to get a list of commands, and ``%PREFIX%help [command]`` to get more information on a specific command.
        """

        if args.arguments_string:
            # Looking for help for a specific command.
            command_name = args.arguments_string

            # Strip the command prefix if it was supplied.
            if command_name.startswith(self.prefix):
                command_name = command_name[len(self.prefix):]

            command_object = AnimeCharGuessBot.command_map.get(command_name)

            if command_object:
                # Command exists.
                help_title = f'Help for {self.prefix}{command_name}'

                # Use the most detailed help message available.
                help_message = command_object.long_help or command_object.short_help or 'No help information is available for this command.'

                # Add usage text if available.
                if command_object.usage:
                    help_message += f'\n\n{command_object.usage}'

                help_message = self.format(help_message).replace('%COMMAND%', command_name)

                await args.message.reply(embed = display.create_embed(help_title, help_message))

            else:
                # Command does not exist.
                await args.message.reply(embed = display.create_embed(
                    'Unknown Command',
                    'This command does not exist. Make sure you have spelled it correctly.'
                ))

        else:
            # No argument passed, show general help.
            command_names = dict()

            # Create a map of command objects to their names.
            for command_name, command_object in AnimeCharGuessBot.command_map.items():
                if command_object in command_names:
                    command_names[command_object] += f', {command_name}'
                else:
                    command_names[command_object] = command_name

            # Build help message box using the short help summaries.
            message_text = '\n'.join([
                f'**{command_name}**: {command_object.short_help}'
                for command_object, command_name in command_names.items()
                
                # Only show commands with help data that the user has permission to use.
                if command_object.short_help and command_object.check_permissions(args)
            ])

            await args.message.reply(embed = display.create_embed(
                'Bot Help',
                self.format(message_text)
            ))


    @command('ping')
    async def command_ping(self, args):
        """
        Pong.

        Ping command for testing if the bot is responding.
        """

        await args.message.reply('Pong! :ping_pong:')


    @command('profile')
    async def command_profile(self, args):
        """
        View your (or someone else's) profile.

        Display your profile page. Mention a user to see theirs.

        Usage: ``%PREFIX%%COMMAND% [user]``
        """

        if args.arguments_string:
            if not args.guild:
                return cmd.NO_LOOKUP_IN_DM

            user = await util.parse_user(args.arguments_string, args.guild)

        else:
            user = args.user

        if not user:
            return cmd.USER_NOT_FOUND

        money = db.get_user_currency(user.id)
        upgparts = db.get_user_upgrades(user.id)

        await args.message.reply(embed = display.create_embed(
            f"{user.display_name}'s Profile",
            f':coin: {self.currency.capitalize()}: {money}\n'
            f':nut_and_bolt: Upgrade parts: {upgparts}',
            thumbnail = util.avatar(user)
        ))


    @command('remove', 'rm', 'yeet')
    async def command_remove(self, args):
        """
        Let one or more of your waifus go.

        Let one of your waifus go. This will reward you %CURRENCY% depending on the rarity of the waifu.
        (1/4 of %CURRENCY% needed to roll that same rarity.)

        ``-y`` - Automatically confirm removal.
        ``-force`` - Remove favorited waifus too.

        Usage: ``%PREFIX%%COMMAND% <inventory number> ... [-y] [-force]``
        You can also remove multiple waifus by using a search query the same as %PREFIX%waifus.
        """
        
        if db.can_remove(args.user.id) and db.can_trade(args.user.id, self):
            db.disable_remove(args.user.id)

        else:
            await args.message.reply(embed = display.create_embed(
                'Something Went Wrong',
                'Unable to perform action. Are you already removing or trading waifus?'
            ))
            return

        try:
            arg_list = shlex.split(args.arguments_string)

            yes_flag = False
            force_flag = False

            if '-y' in arg_list:
                yes_flag = True
                arg_list.remove('-y')

            if '-force' in arg_list:
                force_flag = True
                arg_list.remove('-force')

            if not arg_list:
                return cmd.BAD_USAGE

            # There are 2 ways of selecting waifus to remove, inventory number, and filter.
            # If every argument is a number, we assume the first way is being used.
            is_number_list = True
            for arg in arg_list:
                if not util.is_int(arg):
                    is_number_list = False
                    break

            to_remove = []
            ignored_favs = []

            if is_number_list:
                # Inventory number method.

                for arg in arg_list:
                    index = int(arg)

                    waifu = Waifu.from_user_index(args.user, index)

                    if not waifu:
                        await args.message.reply(embed = display.create_embed(
                            '404 Waifu not Found',
                            'Could not find that waifu in your inventory.'
                        ))
                        return

                    if waifu.fav and not force_flag:
                        await args.message.reply(embed = display.create_embed(
                            'Removal Blocked',
                            f'{waifu} is a favorite. If you want to remove them from favorites, use ``{self.prefix}unfav {waifu.index}``.'
                        ))
                        return

                    to_remove.append(waifu)

            else:
                # Search filter method.

                try:
                    search_filter = waifu_filter.Filter(arg_list)

                except Exception as e:
                    if 'No such show' in str(e):
                        await args.message.reply(embed = display.create_embed(
                            '404 Series not Found',
                            'That series does not exist.'
                        ))
                        return

                    return cmd.BAD_USAGE

                all_waifus = db.get_all_waifu_data_for_user(args.user.id)
                waifus = search_filter.apply(Waifu.from_data(waifu, args.user) for waifu in all_waifus)
        
                for waifu in waifus:
                    if not waifu.fav or force_flag:
                        to_remove.append(waifu)
                    else:
                        ignored_favs.append(waifu)

                if waifus and not to_remove:
                    await args.message.reply(embed = display.create_embed(
                        'Removal Blocked',
                        f'All matching waifus are favorites. Either unfavorite some or all of them with ``{self.prefix}unfav``, or use ``-force`` to remove them anyway.'
                    ))
                    return

            if not to_remove:
                await args.message.reply(embed = display.create_embed(
                    '404 Waifu not Found',
                    'You have no waifus matching that criteria.'
                ))
                return

            reply_to = args.message

            if len(to_remove) == 1 and not ignored_favs and not yes_flag:
                # Only one waifu is being removed, display a message with their image.

                waifu = to_remove[0]

                await args.message.reply(embed = display.create_embed(
                    'Waifu Removal Confirmation',
                    textwrap.dedent(f"""
                    You are about to remove {waifu}.
                    Removing this waifu will award you **{db.get_rarity_currency(waifu.rarity)}** {self.currency}.
                    If you agree with this removal, respond with ``yes``.
                    Respond with anything else or wait {constants.REMOVAL_TIMEOUT} seconds to cancel the removal.
                    """
                    ).strip(),
                    thumbnail = waifu.image_url
                ))

                confirm, reply_to = await self.yes_message(args.message)

                if reply_to.channel.id != args.channel.id:
                    reply_to = args.message

                if not confirm:
                    await reply_to.reply(embed = display.create_embed(
                        'Removal Cancelled',
                        f'Removal of **{waifu.character.en_name}** cancelled.'
                    ))
                    return

            elif not yes_flag:
                # Multiple waifu removal, display as a list.

                lines = ['You are about to remove:']

                reward = 0

                for waifu in to_remove:
                    lines.append(str(waifu))
                    reward += db.get_rarity_currency(waifu.rarity)

                lines.append(f'\nRemoving these waifus will award you {reward} {self.currency}.')

                if ignored_favs:
                    lines.append("\nIgnored favorites (won't be removed):")
                    for waifu in ignored_favs:
                        lines.append(str(waifu))

                await args.message.reply(embed = display.create_embed(
                    'Waifu Removal Confirmation',
                    '\n'.join(lines)
                ))
                
                confirm, reply_to = await self.yes_message(args.message)

                if reply_to.channel.id != args.channel.id:
                    reply_to = args.message

                if not confirm:
                    await reply_to.reply(embed = display.create_embed(
                        'Removal Cancelled',
                        f'Removal of {len(to_remove)} waifus cancelled.'
                    ))
                    return

            success = []
            failed = []
            reward = 0

            for waifu in to_remove:
                if db.remove_waifu(waifu.waifu_id):
                    success.append(waifu)
                    reward += db.get_rarity_currency(waifu.rarity)
                else:
                    failed.append(waifu)

            if reward:
                db.add_user_currency(args.user.id, reward)

        finally:
            db.enable_remove(args.user.id)

        if not failed and len(success) == 1:
            # There was only one waifu, and it was successfully removed.
            await reply_to.reply(embed = display.create_embed(
                'Waifu Let Go',
                f'**{success[0].character.en_name}** has been let go.\n'
                f':coin: Your {self.currency}: **{db.get_user_currency(args.user.id)}** (+{reward})',
                thumbnail = success[0].image_url
            ))

        elif not failed:
            # Multiple waifus were successfully removed.
            await reply_to.reply(embed = display.create_embed(
                'Waifus Let Go',
                f'{len(success)} waifus have been let go.\n'
                f':coin: Your {self.currency}: **{db.get_user_currency(args.user.id)}** (+{reward})'
            ))
        
        elif success:
            # Some waifus were successfully removed, but others weren't.
            lines = ['Some waifus could not be let go.\n\nSuccessfully removed:']

            for waifu in success:
                lines.append(str(waifu))

            lines.append('\nFailed to remove:')

            for waifu in failed:
                lines.append(str(waifu))

            lines.append('\n:coin: Your {self.currency}: **{db.get_user_currency(args.user.id)}** (+{reward})')

            await reply_to.reply(embed = display.create_embed(
                'Something Went Wrong',
                '\n'.join(lines)
            ))

        else:
            # No waifus were successfully removed.
            await reply_to.reply(embed = display.create_embed(
                'Something Went Wrong',
                'Removal failed.'
            ))


    @command('repeat', 'rep', only_in_assigned_channel=False)
    async def command_repeat(self, args):
        """
        Repeats a message.

        Repeats a message in the current channel.
        Leave the message blank to repeat the last message you sent in the channel.

        Usage: ``%PREFIX%%COMMAND% <message>``
        """
        text = args.arguments_string
        replied_message = args.message

        if not text:
            async for message in args.channel.history(limit=5, before=args.message):
                if message.author == args.message.author:
                    text = message.content
                    replied_message = message
                    await args.message.delete()
                    break

        text = util.clean_mentions(text)

        if not text:
            return

        await replied_message.reply(text)
        return


    @command('roll')
    async def command_roll(self, args):
        """
        Perform a gacha roll. (Default: 100 %CURRENCY%)

        Perform a gacha roll with optional infusion of %CURRENCY%.
        (Default: 100, maximum: 15000)

        Prices for guaranteed rarities:
          ``★★☆☆☆: 300``
          ``★★★☆☆: 1000``
          ``★★★★☆: 5000``
          ``★★★★★: 15000``

        Usage: ``%PREFIX%%COMMAND% [%CURRENCY%]``
        """

        price = 100

        if args.arguments_string:
            if args.arguments_string.isnumeric():
                price = int(args.arguments_string)

            else:
                return cmd.BAD_USAGE

        if not (100 <= price <= 15000):
            await args.message.reply(embed = display.create_embed(
                'Roll Failed',
                'Roll price must be between 100 and 15000'
            ))
            return

        wealth = db.get_user_currency(args.user.id)

        if price > wealth:
            await args.message.reply(embed = display.create_embed(
                'Roll Failed',
                f'Insufficient {self.currency}. Currently: **{wealth}**'
            ))
            return

        waifu_data, price = db.get_drop_data(user_id = args.user.id, price = price)

        db.add_waifu(args.user.id, waifu_data['image_id'], waifu_data['rarity'])

        index = db.get_waifusAmount(args.user.id)
        waifu = Waifu.from_user_index(args.user, index)

        await args.message.reply(embed = waifu.create_roll_embed(self.currency, wealth - price, price))
        

    @command('search')
    async def command_search(self, args, ambiguous_flag = False):
        """
        Find a series.

        Look for anime or manga that the bot has characters of.

        Usage: ``%PREFIX%%COMMAND% <name>``
        """

        query = args.arguments_string.strip()

        if not query:
            return cmd.BAD_USAGE

        # Allow short queries with non-alpha characters so I can search ";" to get SciADV stuff.
        if len(query) < 2 and query.isalpha():
            await args.message.reply(embed = display.create_embed(
                'Query Too Short',
                'The search query must be at least two characters long.'
            ))
            return

        series_list = db.get_shows_like(query)

        if series_list:
            title = 'Search Results'
            lines = []

            if ambiguous_flag:
                title = ':warning: Ambiguous Show Title'
                lines.append('Try one of these show IDs:')

            for series in series_list:
                lines.append(f'``{series["id"]}`` **{series["jp_title"]}** ({"Anime" if not series["is_manga"] else "Manga"})')

            await args.message.reply(embed = display.create_embed(
                title,
                '\n'.join(lines)
            ))

        else:
            lines.append('No results.')
            await args.message.reply(embed = display.create_embed(
                title,
                '\n'.join(lines)
            ))

    
    @command('series', 'show')
    async def command_series(self, args):
        """
        View characters of a series.

        Displays the characters of a show that the bot has.

        Usage: ``%PREFIX%%COMMAND% <show id or name>``
        """

        query = args.arguments_string.strip()

        if not query:
            return cmd.BAD_USAGE

        show_id = -1

        if query.isnumeric():
            # Searching by id.
            show_id = int(query)

        else:
            # Searching by name.
            series_list = db.get_shows_like(query)

            if len(series_list) == 1:
                show_id = series_list[0]['id']

            elif len(series_list) > 1:
                # Ambiguous show: There are multiple series with that name.
                await self.command_search(args, ambiguous_flag=True)
                return

        show = Show.from_id(show_id)

        if not show or not show.characters:
            await args.message.reply(embed = display.create_embed(
                'Command Failed',
                'Show not found.'
            ))
            return
        
        title = show.name
        error = "Show has no characters."

        await display.page(self, args, show.characters, title, 0, constants.SHOW_PAGE_SIZE, constants.SHOW_TIMEOUT, error)


    @command('trade')
    async def command_trade(self, args):
        """
        Start a trade offer with another user.

        Start a trade offer or modify/confirm an existing trade offer.

        Usage: One of
        ``%PREFIX%%COMMAND% <user>`` - Start a trade with ``<user>``
        ``%PREFIX%%COMMAND% add <inventory number>`` - Add a waifu to the trade
        ``%PREFIX%%COMMAND% remove <inventory number>`` - Remove a waifu from the trade
        ``%PREFIX%%COMMAND% %CURRENCY% <amount>`` - Set the amount of currency to trade
        ``%PREFIX%%COMMAND% confirm`` - Confirm the trade
        ``%PREFIX%%COMMAND% cancel`` - Cancel the trade
        """

        arg_list = args.arguments_string.split()

        if not arg_list or len(arg_list) > 2:
            return cmd.BAD_USAGE

        if not args.guild:
            await args.message.reply(embed = display.create_embed(
                'Command Failed',
                'You cannot trade in DMs.'
            ))
            return

        action = arg_list[0]

        src_user = args.user
        trade = self.get_trade_involving(src_user.id)

        if trade is None and action in ('add', 'remove', self.currency, 'confirm', 'cancel'):
            await args.message.reply(embed = display.create_embed(
                'Command Failed',
                'You are not currently trading.'
            ))
            return

        elif trade is not None:
            trade.reset_timeout()
            offer = trade.offer_of(src_user.id)

        if action == 'add':
            if len(arg_list) < 2 or not util.is_int(arg_list[1]):
                return cmd.BAD_USAGE

            waifu = Waifu.from_user_index(src_user, int(arg_list[1]))
            
            if not waifu:
                await args.message.reply(embed = display.create_embed(
                    'Trade Add Failed',
                    "Waifu not found in your inventory."
                ))
                return

            if not offer.add_waifu(waifu):
                await args.message.reply(embed = display.create_embed(
                    'Trade Add Failed',
                    "Waifu is already in your offer."
                ))
                return

            offer.confirmed = offer.other.confirmed = False

        elif action == 'remove':
            if len(arg_list) < 2 or not arg_list[1].isnumeric():
                return cmd.BAD_USAGE

            if not offer.remove_waifu(int(arg_list[1])):
                await args.message.reply(embed = display.create_embed(
                    'Trade Remove Failed',
                    "Waifu was not in trade."
                ))
                return
            
            offer.confirmed = offer.other.confirmed = False

        elif action == self.currency:
            if len(arg_list) < 2 or not arg_list[1].isnumeric():
                return cmd.BAD_USAGE

            amount = int(arg_list[1])

            if amount > db.get_user_currency(src_user.id):
                await args.message.reply(embed = display.create_embed(
                    'Trade Money Failed',
                    'You have insufficient funds.'
                ))
                return

            offer.money = amount
            offer.confirmed = offer.other.confirmed = False

        elif action == 'confirm':
            
            if len(arg_list) > 1:
                return cmd.BAD_USAGE

            offer.confirmed = True

            if trade.confirmed():
                if trade.perform():
                    await args.channel.send(embed = display.create_embed(
                        'Trade Confirmed',
                        'Trade has been confirmed!'
                    ))
                else:
                    await args.channel.send(embed = display.create_embed(
                        'Trade Failed',
                        'Something went wrong.'
                    ))

                self.remove_trade(trade)
                return

        elif action == 'cancel':
            if len(arg_list) > 1:
                return cmd.BAD_USAGE

            self.remove_trade(trade)
            await args.channel.send(embed = display.create_embed(
                'Trade Cancelled',
                'Trade has been cancelled.'
            ))
            return

        else:
            target_user = await util.parse_user(arg_list[0], args.guild)
        
            if not target_user:
                return cmd.USER_NOT_FOUND

            if src_user.id == target_user.id:
                await args.message.reply(embed = display.create_embed(
                    'Command Failed',
                    'You cannot trade with yourself.'
                ))
                return

            if trade:
                await args.message.reply(embed = display.create_embed(
                    'Command Failed',
                    'You are already trading.'
                ))
                return

            trade = self.start_trade(src_user, target_user)

        if trade:
            await args.channel.send(embed = trade.create_embed(self))
        else:
            await args.message.reply(embed = display.create_embed(
                'Command Failed',
                'Unable to start trade.'
            ))


    @command('upgrade')
    async def command_upgrade(self, args):
        """
        Upgrade the star rating of a waifu using upgrade parts.

        Usage: ``%PREFIX%%COMMAND% <inventory number> [-y]``
        """

        args_list = args.arguments_string.split()

        yes_flag = False
        if '-y' in args_list:
            yes_flag = True
            args_list.remove('-y')

        if len(args_list) != 1 or not util.is_int(args_list[0]):
            return cmd.BAD_USAGE

        waifu = Waifu.from_user_index(args.user, int(args_list[0]))

        if waifu is None:
            await args.message.reply(embed = display.create_embed(
                '404 Waifu not Found',
                'That waifu was not found in your inventory.'
            ))

            return

        needed = constants.UPGRADE_FROM_COSTS.get(waifu.rarity)

        if needed is None:
            await args.message.reply(embed = display.create_embed(
                'Upgrade Failed',
                'Waifu cannot be upgraded further.'
            ))

            return

        have = db.get_user_upgrades(args.user.id)

        if needed > have:
            await args.message.reply(embed = display.create_embed(
                'Upgrade Failed',
                f'You do not have enough parts to upgrade that waifu.\n'
                f'Needed: **{needed}** :nut_and_bolt:\n'
                f'Have: **{have}** :nut_and_bolt:'
            ))

            return

        reply_to = args.message

        if not yes_flag:
            await args.message.reply(embed = display.create_embed(
                'Confirm Upgrade',
                f'You are about to upgrade **{waifu.character.en_name}** from {display.rarity_string(waifu.rarity)} to {display.rarity_string(waifu.rarity + 1)}.\n'
                f':nut_and_bolt: Your upgrade parts after upgrading will be: **{have - needed}** (-{needed})\n\n'
                f'If you agree with this transaction, say ``yes`` in this channel.\n'
                f'Saying anything else or waiting {constants.UPGRADE_TIMEOUT} seconds will cancel this transaction.',
                thumbnail = waifu.image_url
            ))

            confirm, reply_to = await self.yes_message(args.message, timeout = constants.UPGRADE_TIMEOUT)

            if not confirm:
                await reply_to.reply(embed = display.create_embed(
                    'Upgrade Cancelled',
                    'Your upgrade has been cancelled.'
                ))

                return

        if db.upgrade_user_waifu(args.user.id, waifu.waifu_id, needed):
            await reply_to.reply(embed = display.create_embed(
                'Upgrade Successful',
                f'**{waifu.character.en_name}** has been upgraded to {display.rarity_string(waifu.rarity + 1)}.\n'
                f':nut_and_bolt: Your upgrade parts: **{have - needed}** (-{needed})',
                thumbnail = waifu.image_url
            ))

        else:
            await reply_to.reply(embed = display.create_embed(
                'Upgrade Failed',
                'Something went wrong'
            ))
            

    @command('view', 'info')
    async def command_view(self, args):
        """
        View details of a character including stats.

        View a character's detail page.

        Usage:
          ``%PREFIX%%COMMAND% <character id>`` or
          ``%PREFIX%%COMMAND% <name>``
        """

        if not args.arguments_string:
            return cmd.BAD_USAGE

        if args.arguments_string.isnumeric():
            # Search by id.
            chara_id = int(args.arguments_string)

        else:
            # Search by name.

            # Try name in supplied order, and reversed.

            # Attempting to normalize here doesn't work, because the characters are queried using LIKE.
            # name_parts = nt.normalize_romanization(args.arguments_string).split()
            
            name_parts = args.arguments_string.split()
            q1 = ' '.join(name_parts)
            q2 = ' '.join(name_parts[::-1])

            if q1 == q2:
                # Name reversed is itself.
                data = db.get_character_data_like(q1)

            else:
                data = [
                    *db.get_character_data_like(q1),
                    *db.get_character_data_like(q2)
                ]

            if not data:
                await args.message.reply(embed = display.create_embed(
                    '404 Waifu not Found',
                    'No waifu with that name exists.'
                ))
                return

            if len(data) > 1:
                # TODO: Make this into a proper page.
                await args.message.reply(embed = display.create_embed(
                    'Ambiguous Search',
                    'There are multiple characters with that name. Try using the character id instead.'
                ))
                return

            chara_id = data[0]['id']
        
        chara = Character.from_id(chara_id)

        if chara:
            await chara.display_info(args.message)

        else:
            await args.message.reply(embed = display.create_embed(
                '404 Waifu not Found',
                'No waifu with that id exists.'
            ))


    @command('wager')
    async def command_wager(self, args):
        """
        Wager %CURRENCY% and have 50% chance to double them.

        Wager %CURRENCY% with a 50% chance of doubling them. (Or losing them :P)

        Usage: ``%PREFIX%%COMMAND% <amount>``
        """

        if not args.arguments_string.isnumeric():
            return cmd.BAD_USAGE

        amount = int(args.arguments_string)

        wealth = db.get_user_currency(args.user.id)

        if amount > wealth:
            await args.message.reply(embed = display.create_embed(
                'Wager Failed',
                f'You do not have enough {self.currency}. Currently: **{wealth}**'
            ))
            return

        if random.randint(0, 1):
            db.add_user_currency(args.user.id, amount)
            await args.message.reply(embed = display.create_embed(
                'You Win!',
                f'You doubled your wager!\n:coin: Your {self.currency}: **{wealth + amount}** (+{amount})'
            ))
        
        else:
            db.subtract_user_currency(args.user.id, amount)
            await args.message.reply(embed = display.create_embed(
                'You Lose...',
                f'Too bad, you lost your wager. Better luck next time.\n:coin: Your {self.currency}: **{wealth - amount}** (-{amount})'
            ))


    @command('waifu')
    async def command_waifu(self, args):
        """
        View one of your collected waifus in more detail.

        View details and the image of a waifu you have collected. Use ``-u`` to view another user's waifus.
        
        Usage: ``%PREFIX%%COMMAND% [-u <user>] <number>``
        """

        arg_list = args.arguments_string.split()

        user = args.user

        if '-u' in arg_list:
            uflag = arg_list.index('-u')

            del arg_list[uflag]

            if uflag == len(arg_list):
                # -u was the final argument.
                return cmd.BAD_USAGE

            if not args.guild:
                return cmd.NO_LOOKUP_IN_DM

            user = await util.parse_user(arg_list[uflag], args.guild)
            
            del arg_list[uflag]
    
        if len(arg_list) == 1 and util.is_int(arg_list[0]):
            waifu_index = int(arg_list[0])
        else:
            return cmd.BAD_USAGE

        if not user:
            return cmd.USER_NOT_FOUND

        waifu = Waifu.from_user_index(user, waifu_index)

        if waifu is None:
            await args.message.reply(embed = display.create_embed(
                '404 Waifu not Found',
                'That waifu does not exist.'
            ))
            return

        
        await args.message.reply(embed = waifu.create_view_embed())


    @command('waifus', 'list')
    async def command_waifus(self, args):
        """
        View your collected waifus.

        View your (or someone else's) collected waifus inventory.

        Usage:
        ``%PREFIX%%COMMAND%
          [user]
          [(-n or -name) <character name (use quotes around name if it has spaces)>]
          [(-s or -series) <series id>]
          [(-sn or -series-name) <series name (use quotes around name if it has spaces)>]
          [(-r or -rarity) <number>]
          [(-f or -fav or -favorite)]
          [(-p or -page) <page number>]``
        """

        arg_list = shlex.split(args.arguments_string)

        user = args.user

        uflag = None

        if '-u' in arg_list:
            uflag = arg_list.index('-u')

            del arg_list[uflag]

            if uflag == len(arg_list):
                # -u was the final argument.
                return cmd.BAD_USAGE

            if not args.guild:
                return cmd.NO_LOOKUP_IN_DM

            user = await util.parse_user(arg_list[uflag], args.guild)
            
            del arg_list[uflag]

        if arg_list and not arg_list[0].startswith('-') and args.guild and uflag is None:
            user = await util.parse_user(arg_list[0], args.guild)
            del arg_list[0]

        if not user:
            return cmd.USER_NOT_FOUND

        page = None

        for flag in ('-p', '-page', '--page'):
            if flag in arg_list:
                pflag = arg_list.index(flag)

                del arg_list[pflag]

                if pflag == len(arg_list):
                    # -p was the final argument.
                    return cmd.BAD_USAGE

                if not util.is_int(arg_list[pflag]):
                    return cmd.BAD_USAGE

                page = int(arg_list[pflag])

                del arg_list[pflag]

        try:
            search_filter = waifu_filter.Filter(arg_list)
        except Exception as e:
            if 'No such show' in str(e):
                await args.message.reply(embed = display.create_embed(
                    '404 Series not Found',
                    'That series does not exist.'
                ))
                return

            return cmd.BAD_USAGE

        all_waifus = db.get_all_waifu_data_for_user(user.id)
        waifus = search_filter.apply(Waifu.from_data(waifu, user) for waifu in all_waifus)

        if not waifus:
            await args.message.reply(embed = display.create_embed(
                '404 Waifu not Found',
                "Selected user does not have any waifus that match the request...\nThey'd better claim some!" if search_filter.filters
                else "Selected user does not have any waifus yet...\nThey'd better claim some!"
            ))
            return

        title = f"{user.display_name}'s Waifus"
        error = "There are no waifus here!"

        await display.page(self, args, waifus, title, page, constants.PROFILE_PAGE_SIZE, constants.PROFILE_TIMEOUT, error)
    
    @command('uma.gacha', only_in_assigned_channel = False)
    async def command_uma_gacha(self, args):
        """
        View the currently active Uma Musume gacha banners.
        """
        gacha_embeds = await uma.create_gacha_embeds()
        if gacha_embeds:
            for embed in gacha_embeds:
                await args.message.reply(embed = embed)
        else:
            await args.message.reply(embed=display.create_embed(
                'No Uma Musume Gacha',
                'No Uma Musume Gacha could be found.'
            ))
        return


AnimeCharGuessBot.command_map = _command_map
