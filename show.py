import database_tools as db
import waifu

class Show:
    '''
    A series that characters from are available.
    '''

    @classmethod
    def from_id(cls, show_id):
        '''
        Retrieve a show object by it's id.
        '''

        if not db.show_exists(show_id):
            return None

        name = db.get_show_title_jp(show_id)
        char_data = db.get_characters_from_show(show_id)
        charas = [
            waifu.Character.from_data(data)
            for data in char_data
        ]

        return cls(name, charas)
    

    def __init__(self, name, characters):
        self.name = name
        self.characters = characters


    def __contains__(self, character):
        '''
        Check if a character is in this show.
        '''
        return character in self.characters
