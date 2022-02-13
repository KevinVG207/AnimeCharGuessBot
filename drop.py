import random
import time

import constants
import database_tools as db
import display
import name_tools as nt
import util
from waifu import Waifu

class Drop:
    """
    A random drop.
    """

    @classmethod
    async def create(cls, channel):
        """
        Create a new random drop.
        """
        history = db.get_history(channel.guild.id)
        data = db.get_drop_data(history)
        waifu = Waifu.from_data(data)

        random_number = random.random()
        if random_number < 0.47:
            image_url = waifu.normal_url
        elif random_number < 0.94:
            image_url = waifu.mirror_url
        else:
            image_url = waifu.flipped_url

        if not await util.verify_url(image_url):
            # Fallback to MAL URL.
            image_url = waifu.image_url
            if not await util.verify_url(image_url):
                return await cls.create(channel)

        db.update_history(channel.guild.id, history, data)
        return cls(waifu, channel, image_url)


    def __init__(self, waifu, channel, image_url):
        self.waifu = waifu
        self.channel = channel
        self.drop_image_url = image_url
    

    def guess_matches(self, guess):
        """
        Check if a message is a correct guess.
        """

        return nt.unordered_normalized(guess) in (
            nt.unordered_normalized(self.waifu.character.en_name),
            nt.unordered_normalized(self.waifu.character.alt_name),
            nt.unordered_normalized(self.waifu.character.ja_name)
        )
        

    def create_guess_embed(self):
        """
        Create a Discord embed showing the initial challenge.
        """

        return display.create_embed(
            'Waifu Drop!',
            f'A waifu dropped, guess their name!\nHint: ``{nt.initials(self.waifu.character.en_name)}``',
            image = self.drop_image_url
        )
    

    def create_timeout_embed(self):
        """
        Create a Discord embed for this drop timing out.
        """

        return display.create_embed(
            'Timed out!',
            f'**{self.waifu.character.en_name}** gave up waiting.\nBetter luck next time!\n{self.waifu.character.source_string()}',
            image = self.waifu.image_url
        )
