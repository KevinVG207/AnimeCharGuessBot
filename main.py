#!/usr/bin/python3
import logger as loggermodule
import logging
logger = logging.getLogger('discord')

import bot_token
if bot_token.isDebug():
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Debug mode")

import asyncio
import os

import discord
import constants
import bot
import internet

logger.info("Starting main script.")

# Verify internet connection.
if not internet.verify():
    asyncio.run(internet.handle_disconnect(from_reboot=True))

intents = discord.Intents().all()

token = os.environ[f'{constants.ENVVAR_PREFIX}TOKEN']

resource_server = int(os.environ[f'{constants.ENVVAR_PREFIX}RESOURCE_SERVER'])
resource_channel = int(os.environ[f'{constants.ENVVAR_PREFIX}RESOURCE_CHANNEL'])

admins = [
    admin_id.strip()
    for admin_id in os.environ.get(f'{constants.ENVVAR_PREFIX}ADMIN', '').split(',')
    if admin_id
]

client = bot.AnimeCharGuessBot(token = token,
                               intents = intents,
                               prefix = constants.PREFIX,
                               currency = constants.CURRENCY,
                               admins = admins,
                               resource_server = resource_server,
                               resource_channel = resource_channel)

logger.info("Running client.")

client.run()
