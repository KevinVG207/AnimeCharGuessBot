import textwrap
import display
import database_tools as db

BAD_USAGE = object()
USER_NOT_FOUND = object()
NO_LOOKUP_IN_DM = object()

class Command:
    '''
    A command available for the bot.
    '''
    
    def __init__(self, require_server_admin = False, require_bot_admin = False, only_in_assigned_channel = True, ignore_cooldown = False):
        self.require_server_admin = require_server_admin
        self.require_bot_admin = require_bot_admin
        self.only_in_assigned_channel = only_in_assigned_channel
        self.ignore_cooldown = ignore_cooldown
        self.function = None
        self.short_help = None
        self.long_help = None
        self.usage = None
    

    def set_function(self, function):
        '''
        Bind a function to this command.

        This also reads the help and usage text from the docstring.
        '''

        self.function = function

        if function.__doc__:
            helps = textwrap.dedent(function.__doc__).strip().split('\n\n')

            if helps and helps[-1].startswith('Usage:'):
                self.usage = helps[-1]
                del helps[-1]

            if helps:
                self.short_help = helps[0]

            if len(helps) >= 2:
                self.long_help = '\n\n'.join(helps[1:])
    

    def check_permissions(self, arguments):
        '''
        Check if this command can be run by this user.
        '''

        if self.require_server_admin and not arguments.is_server_admin:
            return False

        if self.require_bot_admin and not arguments.is_bot_admin:
            return False

        return True


    async def run(self, bot, arguments):
        '''
        Run the command with some arguments.
        '''
        # Check for cooldown
        if not arguments.is_bot_admin and not self.ignore_cooldown and arguments.is_in_cooldown:
            return
        bot.set_cooldown(arguments.user.id)

        # Check if in the correct channel.
        if self.only_in_assigned_channel and arguments.message.guild and arguments.message.channel.id != db.get_assigned_channel_id(arguments.message.guild.id):
            return

        if self.check_permissions(arguments):
            try:
                result = await self.function(bot, arguments)
            except Exception as e:
                await self.generic_error(arguments)
                raise e

            # Common error messages are handled here instead.
            if result is BAD_USAGE:
                await self.bad_usage_error(bot, arguments)

            if result is USER_NOT_FOUND:
                await self.user_not_found_error(arguments)

            if result is NO_LOOKUP_IN_DM:
                await self.no_lookup_in_dm_error(arguments)

        else:
            await self.permissions_error(arguments)
    

    async def generic_error(self, arguments):
        '''
        Display an error message that does not have any further info about the cause of the error.
        '''
        await arguments.message.reply(embed = display.create_embed('Command Failed', 'An unknown error occurred when running that command. Sorry :('))
    

    async def permissions_error(self, arguments):
        '''
        Display an error message for when a user lacks permission to run a command.
        '''
        await arguments.message.reply(embed = display.create_embed('Permission Denied', 'You do not have permission to use that command.'))


    async def bad_usage_error(self, bot, arguments):
        '''
        Display an error message for when a command is passed invalid arguments.
        '''
        usage_text = self.usage or 'Bad usage.'
        usage_text = bot.format(usage_text).replace('%COMMAND%', arguments.command)
        await arguments.message.reply(embed = display.create_embed('Command Failed', usage_text))

    
    async def user_not_found_error(self, arguments):
        '''
        Display an error message for when a command requests information about a user that does not exist.
        '''
        await arguments.message.reply(embed = display.create_embed('Lookup Failed', 'Requested user is not in this server.'))

    
    async def no_lookup_in_dm_error(self, arguments):
        '''
        Display a message alerting users that they cannot request information about other users in DMs.
        '''
        await arguments.message.reply(embed = display.create_embed('Lookup Failed', 'You cannot look for users in DMs.'))


class CommandArguments:
    '''
    The context passed to a command when it is run.
    '''

    def __init__(self, message, command, arguments_string, is_server_admin, is_bot_admin, is_in_cooldown):
        self.message = message
        self.command = command
        self.arguments_string = arguments_string
        self.is_server_admin = is_server_admin
        self.is_bot_admin = is_bot_admin
        self.is_in_cooldown = is_in_cooldown

        self.user = message.author
        self.channel = message.channel
        self.guild = message.guild
