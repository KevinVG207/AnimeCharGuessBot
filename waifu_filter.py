import database_tools as db
import name_tools as nt
from show import Show

class Filter:
    '''
    Filter waifus by a criteria.

    Used in list and some other commands.

    Can filter by name, rarity, series id and name, and favorites.
    '''

    def __init__(self, args):
        self.filters = []

        next_type = None
        for arg in args:
            
            if next_type == 'name' or (next_type is None and not arg.startswith('-')):
                # To avoid name order mattering, split the name up and check each segment.
                for part in arg.split():
                    self.filters.append(lambda waifu, q = nt.normalize_romanization(part): q in nt.normalize_romanization(waifu.character.en_name) or (waifu.character.ja_name and q in waifu.character.ja_name))

            elif next_type == 'rarity':
                self.filters.append(lambda waifu, q = int(arg) - 1: waifu.rarity == q)

            elif next_type == 'series':
                show = Show.from_id(int(arg))

                if not show:
                    raise ValueError('No such show')

                self.filters.append(lambda waifu, q = show: waifu.character in q)
            
            elif next_type == 'seriesname':
                shows = (
                    Show.from_id(show_data['id'])
                    for show_data in db.get_shows_like(arg)
                )

                shows = [show for show in shows if show]

                if not shows:
                    raise ValueError('No such show')

                def search(waifu, show_list = shows):
                    for show in show_list:
                        if waifu.character in show:
                            return True

                    return False

                self.filters.append(search)

            if next_type is not None:
                next_type = None

            elif arg.startswith('-'):
                flag = arg.replace('-', '')
                
                if flag in ('n', 'name'): next_type = 'name'
                elif flag in ('r', 'rarity'): next_type = 'rarity'
                elif flag in ('s', 'series'): next_type = 'series'
                elif flag in ('sn', 'seriesname'): next_type = 'seriesname'

                elif flag in ('f', 'fav', 'favs', 'favorite', 'favorites', 'favourite', 'favourites'):
                    self.filters.append(lambda waifu: waifu.fav)

                else:
                    raise ValueError(f'Unknown flag {arg}')



    def apply(self, waifus):
        '''
        Find the waifus in a list that match the criteria.
        '''

        filtered = []

        for waifu in waifus:
            for f in self.filters:
                if not f(waifu):
                    break

            else:
                filtered.append(waifu)

        return filtered
