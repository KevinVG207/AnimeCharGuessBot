#!/usr/bin/python3

import os

import discord
import logging
import constants
import bot
import internet

# Verify internet connection.
if not internet.verify():
    internet.handle_disconnect()


logger = logging.getLogger('discord')
logger.setLevel(logging.WARNING)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
logger.addHandler(handler)

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
client.run()
