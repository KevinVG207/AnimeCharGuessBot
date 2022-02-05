import time

import constants
import database_tools as db
import display

class Offer:
    '''
    An offer that can be made as part of a trade.
    Can contain money and waifus.
    '''

    def __init__(self):
        self.money = 0
        self.waifus = []
        self.confirmed = False
        self.other = None
    

    def add_waifu(self, waifu):
        '''
        Add a waifu to the trade.
        Returns if the addition was successful.
        '''

        for existing in self.waifus:
            if existing.index == waifu.index:
                return False

        self.waifus.append(waifu)
        return True


    def remove_waifu(self, index):
        '''
        Remove a waifu from the trade by index.
        Returns if the removal was successful.
        '''

        for i, waifu in enumerate(self.waifus):
            if waifu.index == index:
                del self.waifus[i]
                return True

        return False
    

    def text(self, bot):
        '''
        Get a text representation of this offer to be displayed in the trade window.
        '''

        lines = []

        if self.money:
            lines.append(f'{bot.currency.capitalize()}: {self.money}')

        lines.extend(str(waifu) for waifu in self.waifus)

        if not lines:
            lines.append('``Empty``')

        if self.confirmed:
            lines.append(':white_check_mark: Confirmed')
        else:
            lines.append(':x: Unconfirmed')

        return '\n'.join(lines)


class Trade:
    '''
    A trade between two users.
    '''

    def __init__(self, user1, user2):
        self.user1 = user1
        self.user2 = user2

        self.offer1 = Offer()
        self.offer2 = Offer()

        self.offer1.other = self.offer2
        self.offer2.other = self.offer1

        self.reset_timeout()
    

    def __contains__(self, user):
        '''
        Check if a user is party to this trade.
        '''
        return self.user1.id == user or self.user2.id == user
    

    def mark_users_as_trading(self):
        '''
        Flag the participants as in a trade, so they cannot start trading elsewhere.
        '''
        db.disable_trade(self.user1.id)
        db.disable_trade(self.user2.id)
    

    def mark_trade_over(self):
        '''
        Flag the participants as no longer in a trade.
        '''
        db.enable_trade(self.user1.id)
        db.enable_trade(self.user2.id)


    def offer_of(self, user):
        '''
        Get a user's offer.
        '''

        if self.user1.id == user:
            return self.offer1

        if self.user2.id == user:
            return self.offer2
    

    def confirmed(self):
        '''
        Check if both users have confirmed the trade.
        '''
        return self.offer1.confirmed and self.offer2.confirmed


    def perform(self):
        '''
        Perform the trade. returns if successful.
        '''
        return db.trade(self.user1.id, self.user2.id, self.offer1, self.offer2)
    

    def create_embed(self, bot):
        '''
        Create a Discord embed representing the current state of the trade.
        '''

        return display.create_embed(
            'Waifu Trade Offer',
            f"**{self.user1.display_name}**'s offer:\n"
            f'{self.offer1.text(bot)}\n\n'
            f"**{self.user2.display_name}**'s offer:\n"
            f'{self.offer2.text(bot)}\n\n'
            f'Add waifus with ``{bot.prefix}trade add <inventory number>``\n'
            f'Add {bot.currency} with ``{bot.prefix}trade {bot.currency} <amount>``\n'
            f'Confirm trade with ``{bot.prefix}trade confirm``\n'
            f'Cancel trade with ``{bot.prefix}trade cancel``\n'
            f'For more features, check ``{bot.prefix}help trade``'
        )


    def reset_timeout(self):
        '''
        Reset when the trade should timeout.
        '''
        self.timeout = time.time() + constants.TRADE_TIMEOUT
    

    def is_timeout(self):
        '''
        Check if the trade has expired.
        '''
        return time.time() > self.timeout
