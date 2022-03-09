import asyncio
import math
import os
import time

import requests

import bot_token
import constants
import display
import util
from datetime import datetime


def verify():
    try:
        resp = requests.request('head', constants.VERIFICATION_URL)

    except requests.RequestException:
        return False

    return resp.status_code == 200


async def handle_disconnect(from_reboot = False):
    # Wait and hope it fixes itself.
    if not from_reboot:
        await asyncio.sleep(15)
        if verify():
            return

    print(f"{datetime.now()} Failed to connect to discord.")
    write_downtime()
    retries = 0
    while retries < 8 or time.time() - constants.START_TIME < 600:
        if not bot_token.isDebug():
            print(f"{datetime.now()} Restarting wlan0")
            os.system("sudo ifconfig wlan0 down")
            time.sleep(1)
            os.system("sudo ifconfig wlan0 up")
        # Sleep for 30 seconds.
        time.sleep(15)
        print(f"{datetime.now()} Checking for reconnect...")
        if verify():
            print(f"{datetime.now()} Reconnected.")
            if not from_reboot:
                # If we're from reboot, the bot hasn't started yet.
                # Instead, we just wait until on_ready() calls send_downtime_message().
                await send_downtime_message()
            return
        retries += 1

    # Retries failed, reboot system.
    print(f"{datetime.now()} Reconnecting failed. Rebooting.")
    reboot()


def reboot():
    if bot_token.isDebug():
        quit(404)
    os.system("sudo reboot")


def write_downtime():
    with open("down.time", "w") as f:
        f.write(f"{math.floor(time.time())}")


async def send_downtime_message(from_reboot = False):
    if os.path.exists("down.time") and constants.BOT_OBJECT:
        try:
            f = open("down.time", "r")
            down_time = int(f.readline())
            f.close()
            os.remove("down.time")
            await constants.BOT_OBJECT.send_admin_dm(display.create_embed("Bot was down.", f"From: <t:{down_time}>\nUntil: <t:{math.floor(time.time())}>{' (from reboot)' if from_reboot else ''}"))

        except ValueError:
            pass
    return
