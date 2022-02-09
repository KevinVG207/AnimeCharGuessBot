import time

import constants
import database_tools as db
import display
import http_tools as http
import name_tools as nt
from waifu import Waifu

async def verify_image(url):
    '''
    Check if an image actually exists on the remote server.
    '''

    try:
        resp = await http.request('head', url)
    
    except Exception:
        return False

    return resp.status_code == 200


class Drop:
    '''
    A random drop.
    '''

    @classmethod
    async def create(cls, channel):
        '''
        Create a new random drop.
        '''

        history = db.get_history(channel.guild.id)
        data = db.get_drop_data(history)
        waifu = Waifu.from_data(data)

        if await verify_image(waifu.image_url):
            db.update_history(channel.guild.id, history, data)
            return cls(waifu, channel)

        else:
            return await cls.create(channel)


    def __init__(self, waifu, channel):
        self.waifu = waifu
        self.channel = channel
    

    def guess_matches(self, guess):
        '''
        Check if a message is a correct guess.
        '''

        return nt.unordered_normalized(guess) in (
            nt.unordered_normalized(self.waifu.character.en_name),
            nt.unordered_normalized(self.waifu.character.alt_name),
            nt.unordered_normalized(self.waifu.character.ja_name)
        )
        

    def create_guess_embed(self):
        '''
        Create a Discord embed showing the initial challenge.
        '''

        return display.create_embed(
            'Waifu Drop!',
            f'A waifu dropped, guess their name!\nHint: ``{nt.initials(self.waifu.character.en_name)}``',
            image = self.waifu.obfuscated_url()
        )
    

    def create_timeout_embed(self):
        '''
        Create a Discord embed for this drop timing out.
        '''

        return display.create_embed(
            'Timed out!',
            f'**{self.waifu.character.en_name}** gave up waiting.\nBetter luck next time!\n{self.waifu.character.source_string()}',
            image = self.waifu.image_url
        )
