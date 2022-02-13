import os
import time

import requests

import bot_token
import constants
import util
from datetime import datetime


def verify():
    try:
        resp = requests.request('head', constants.VERIFICATION_URL)

    except Exception:
        return False

    return resp.status_code == 200


def handle_disconnect():
    print(f"{datetime.now()} Failed to connect to the internet.")
    retries = 0
    while retries < 4 or time.time() - constants.START_TIME < 600:
        # Sleep for 30 seconds.
        time.sleep(30)
        print(f"{datetime.now()} Checking for reconnect...")
        if verify():
            print(f"{datetime.now()} Reconnected.")
            return
        retries += 1

    # Retries failed, reboot system.
    print(f"{datetime.now()} Reconnecting failed. Rebooting.")
    reboot()

def reboot():
    if bot_token.isDebug():
        quit(404)
    os.system("sudo reboot")
