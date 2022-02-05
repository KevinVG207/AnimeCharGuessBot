import asyncio
import discord
import random
import string
from urllib.parse import urlparse

import constants
import database_tools as db
import display

class Character:
    @classmethod
    def from_data(cls, data):
        '''
        Create a Character object using data from the database.
        '''

        images = data.get('image_urls')

        image_count = data.get('image_count')

        if images is not None:
            image_count = len(images)

        return cls(data['id'], data.get('jp_name'), data['en_name'], data.get('alt_name'), image_count, images, data.get('favorites'), data.get('waifu_count'), data.get('rarity_count'))
    

    @classmethod
    def from_id(cls, chara_id):
        '''
        Retrieve a character from the database by id.
        '''

        data = db.get_character_info(chara_id)

        if data:
            return cls.from_data(data)

        else:
            return None


    def __init__(self, character_id, ja_name, en_name, alt_name, image_count, images = None, favs = None, collected = None, rarity_data = None):
        self.character_id = character_id
        self.ja_name = ja_name
        self.en_name = en_name
        self.alt_name = alt_name
        self.image_count = image_count
        self.images = images
        self.favs = favs
        self.collected = collected

        if rarity_data is None:
            self.rarity_data = None
        else:
            self.rarity_data = []
            for i in range(6):
                self.rarity_data.append(rarity_data.get(i, 0))
    

    def __eq__(self, other):
        return type(self) == type(other) and self.character_id == other.character_id

    
    def source_string(self):
        '''
        Get a string containing the source websites for the character's data.
        '''
        return f'MAL ID: [{self.character_id}](https://myanimelist.net/character/{self.character_id})'

    
    async def display_info(self, reply_to):
        '''
        Create an interactive Discord embed showing the characters data, and allow the user to view the characters images.
        '''

        lines = []

        if self.ja_name:
            lines.append(self.ja_name)

        lines.append(self.source_string())

        lines.append(f'**{self.image_count}** images')

        if self.favs == 1:
            lines.append('Favorited **1** time')
        else:
            lines.append(f'Favorited **{self.favs}** times')

        lines.append(f'\nNumber collected: **{self.collected}**')

        for i in range(6):
            lines.append(f'{display.rarity_string(i)}: {self.rarity_data[i]}')

        text = '\n'.join(lines)

        embed = display.create_embed(self.en_name, text)

        if self.images:
            embed.set_image(url = self.images[0])
            embed.set_footer(text = f'Image #1 of {self.image_count}')

        if self.image_count > 1:
            # Multiple images, add buttons to view them.

            image_no = 0
            
            prev_button = discord.ui.Button(label = '⬅ Prev')
            next_button = discord.ui.Button(label = 'Next ➡')

            button_queue = asyncio.Queue()

            async def prev_cb(interaction):
                if interaction.user.id == reply_to.author.id:
                    await button_queue.put(-1)

            async def next_cb(interaction):
                if interaction.user.id == reply_to.author.id:
                    await button_queue.put(1)

            prev_button.callback = prev_cb
            next_button.callback = next_cb

            view = discord.ui.View(timeout = constants.PROFILE_TIMEOUT)
            view.add_item(prev_button)
            view.add_item(next_button)

            message = await reply_to.reply(embed = embed, view = view)

            try:
                while True:
                    movement = await asyncio.wait_for(button_queue.get(), constants.PROFILE_TIMEOUT)

                    image_no += movement
                    image_no %= len(self.images)

                    if button_queue.empty():
                        embed = display.create_embed(self.en_name, text)

                        embed.set_image(url = self.images[image_no])
                        embed.set_footer(text = f'Image #{image_no + 1} of {self.image_count}')

                        await message.edit(embed = embed, view = view)

            except asyncio.TimeoutError:
                prev_button.callback = next_button.callback = None
                prev_button.disabled = next_button.disabled = True

                view = discord.ui.View()
                view.add_item(prev_button)
                view.add_item(next_button)

                await message.edit(embed = embed, view = view)

        else:
            await reply_to.reply(embed = embed)


class Waifu:
    '''
    A waifu with a rarity and image that is maybe owned by someone.
    '''

    @classmethod
    def from_data(cls, data, user = None):
        '''
        Create a Waifu object using data from the database.
        '''

        if data is None:
            return None

        card_index = data.get('card_index')

        if card_index is not None:
            card_index += 1

        return cls(Character.from_data(data), data.get('image_index'), data.get('image_url'), data.get('rarity'), data.get('image_id'), user, card_index, data.get('waifus_id'), data.get('favorite'))


    @classmethod
    def from_user_index(cls, user, index):
        '''
        Fetch and create a waifu from a user and an inventory number.
        '''

        data = db.get_waifu_data_of_user(user.id, index)

        if data is None:
            return None

        return cls.from_data(data, user)


    def __init__(self, character, image, image_url, rarity, image_id = None, owner = None, index = None, waifu_id = None, fav = None):
        self.character = character
        self.image = image
        self.image_url = image_url
        self.rarity = rarity
        self.image_id = image_id
        self.owner = owner
        self.index = index
        self.waifu_id = waifu_id

        # `fav` might be some other truthy or falsy value, like 0 or 1
        if fav is not None:
            fav = bool(fav)

        self.fav = fav
    

    def __str__(self):
        if self.owner is None:
            return f'{display.rarity_string(self.rarity)} **{self.character.en_name}** #{self.image}'

        else:
            text = f'``{self.index}`` {display.rarity_string(self.rarity)} **{self.character.en_name}** #{self.image}'

            if self.fav:
                text += ' :heart:'

            return text
    

    def create_view_embed(self):
        '''
        Create a Discord embed showing information about this waifu.
        '''

        lines = []
    
        if self.character.ja_name:
            lines.append(self.character.ja_name)
    
        lines.append(display.rarity_string(self.rarity))
        lines.append(f'Image {self.image}')
        lines.append(self.character.source_string())
    
        upgrade_cost = constants.UPGRADE_FROM_COSTS.get(self.rarity)

        if upgrade_cost:
            lines.append(f'Upgrade cost: {upgrade_cost} :nut_and_bolt:')
        else:
            lines.append('Cannot be upgraded')
    
        embed = display.create_embed(
            self.character.en_name,
            '\n'.join(lines),
            image = self.image_url
        )
    
        if self.owner:
            embed.set_footer(text = f"{self.owner.display_name}'s waifu #{self.index}")
    
        return embed
    

    def create_roll_embed(self, currency, total, price):
        '''
        Create a Discord embed for when this waifu is rolled in the gatcha.
        '''

        lines = [f'You rolled **{self.character.en_name}**\n']
        lines.append(display.rarity_string(self.rarity))
        lines.append(f'Image {self.image}')
        lines.append(self.character.source_string())
        
        lines.append(f'\nThey have filled inventory slot ``{self.index}``')
        lines.append(f':coin: Your {currency}: {total} (-{price})')

        return display.create_embed(
            f"{self.owner.display_name}'s Gatcha Roll",
            '\n'.join(lines),
            image = self.image_url
        )
    

    def obfuscated_url(self):
        '''
        The waifu's image's URL, but with some unused parameters to slow down googlers.
        '''

        url = urlparse(self.image_url)

        # Be consistent for each URL to reduce strain on Discord's cache.
        rng = random.Random(self.image_url)

        # Add some useless escapes. I think Discord might remove these, however.
        newpath = ''.join([
            '%3' + c
            if c.isnumeric() and not rng.randint(0, 2)
            else c
            for c in url.path
        ])

        if not url.query:
            key = ''.join([
                rng.choice(string.ascii_letters)
                for i in range(rng.randint(5,16))
            ])

            # Try to invoke Google unit conversion.
            value = '"+in+' + rng.choice((
                'meters', 'centimeters', 'kilometers', 'miles', 'feet', 'yards', 'inches',
                'seconds', 'minutes', 'hours', 'days', 'years',
                'grams', 'kilograms', 'ounces', 'pounds', 'stone'
            ))

            newquery = f'{key}={value}'

        else:
            newquery = ''

        return f'{url.scheme}://{url.netloc}{newpath}?{newquery}'
