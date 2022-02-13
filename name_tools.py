from collections import Counter
import unicodedata
from unidecode import unidecode

def normalize_romanization(text):
    """
    Normalizes various ways in which Japanese names might be romanized.
    """

    # Strip accents and punctuation.
    nfd_normalized = unicodedata.normalize('NFD', text.lower())
    no_accents = [
        char
        for char in nfd_normalized
        if unicodedata.category(char) not in ('Mn', 'Pd', 'Po')
    ]
    no_accents = unidecode(''.join(no_accents))

    return (
        no_accents
        .replace('sy', 'sh')
        .replace('shi', 'si')
        .replace('chi', 'ti')
        .replace('tsu', 'tu')
        .replace('tsu', 'tu')
        .replace('du', 'zu')
        .replace('oo', 'o')
        .replace('ou', 'o')
        .replace('oh', 'o')
        .replace('uu', 'u')
        .replace('ee', 'e')
        .replace('ei', 'e')
        .replace('ii', 'i')
        .replace('aa', 'a')
        .replace('wi', 'i')
        .replace('we', 'e')
        .replace('wo', 'o')
        .replace('l', 'r')  # Is this too far?
    )


def unordered_normalized(text):
    """
    Returns objects that will be equal over multiple calls if the entered name is the same when normalized and the order is ignored.
    """

    if text is None:
        # Null text should not match anything.
        return object()

    return Counter(
        normalize_romanization(part)
        for part in text.split()
    )


def initials(name):
    """
    Get the initials of a name.
    """

    return ' '.join([
        part[0] + '.'
        for part in name.split()
    ])
