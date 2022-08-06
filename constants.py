import discord
import time
import os

# Constants used by the bot in various places.
import bot_token

ENVVAR_PREFIX = 'ACGB_'
START_TIME = time.time()
VERIFICATION_URL = "https://discord.com/"
WORKING_DIR = os.path.dirname(os.path.realpath(__file__))
LOG_FILE = os.path.join(WORKING_DIR, "log.log")

BOT_OBJECT = None
CHARACTER_TIMEOUT = 30
COOLDOWN_SECONDS = 1
CURRENCY = "credits"
DROP_TIMEOUT = 20 * 60
EMBED_COLOR = discord.Color.red()
GIFT_TIMEOUT = 15
PROFILE_TIMEOUT = 30
PROFILE_PAGE_SIZE = 25
PREFIX = "w." if not bot_token.isDebug() else "ww."
REMOVAL_TIMEOUT = 15
SHOW_PAGE_SIZE = 32
SHOW_TIMEOUT = 30
TRADE_TIMEOUT = 60
UPGRADE_TIMEOUT = 15
HISTORY_SIZE = 500

UPGRADE_FROM_COSTS = {
    0: 1,
    1: 5,
    2: 10,
    3: 20
}

TMP_DIR = "tmp"
