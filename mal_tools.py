import requests
from bs4 import BeautifulSoup
import time
import database as db


def getAnimeURLSegment(anime_url):
    return anime_url.split("myanimelist.net/anime/")[1] if "myanimelist.net/anime/" in anime_url else None


def getAnimeID(anime_url):
    anime_url_segment = getAnimeURLSegment(anime_url)
    if anime_url_segment:
        anime_id = anime_url_segment.split("/")[0]
        if anime_id.isnumeric():
            return int(anime_id)
    return None


def downloadInsertAnimeCharacters(anime_url, overwrite=False):
    anime_url_segment = getAnimeURLSegment(anime_url)
    anime_id = getAnimeID(anime_url)
    print(anime_url_segment)
    time.sleep(1)
    page = requests.get(f"https://myanimelist.net/anime/{anime_url_segment}/characters")
    soup = BeautifulSoup(page.content, "html.parser")

    jp_title_element = soup.find("h1", class_="title-name")
    if not jp_title_element:
        print(f"[ERR] Could not find JP Anime Title for {anime_url_segment}")
        return -1
    jp_title = jp_title_element.text
    en_title_element = soup.find("p", class_="title-english")
    en_title = en_title_element.text if en_title_element else None

    if not db.showExistsByMAL(anime_id, False):
        db.insertShow(anime_id, jp_title, en_title, False)

    show_id = db.getShowIDByMAL(anime_id, False)

    character_tables = soup.find_all("table", class_="js-anime-character-table")

    character_count = len(character_tables)
    print(f"Found {character_count} characters.")

    for character_table in character_tables:
        character_url = character_table.find_all("a", href=True)[0]
        character_id = getCharacterIDFromURL(character_url["href"])
        if not overwrite:
            # Check if already exists and ignore if so.
            if db.characterExists(character_id):
                if db.characterHasShow(character_id, show_id):
                    print(f"Character {character_id} already exists.")
                    continue
                else:
                    # Add show to character.
                    db.addShowToCharacter(character_id, show_id)
                    continue
        db.insertCharacter(downloadCharacterFromURL(character_url["href"]))
        db.addShowToCharacter(character_id, show_id)


def getCharacterIDFromURL(character_url):
    return character_url.split("myanimelist.net/character/")[1].split("/")[0]


def downloadCharacterFromURL(character_url):
    return downloadCharacter(character_url.split("myanimelist.net/character/")[1].split("/")[0])


def downloadCharacter(char_id):
    print(f"Downloading character {char_id}", end=" ")
    time.sleep(1)

    page = requests.get(f"https://myanimelist.net/character/{char_id}")
    soup = BeautifulSoup(page.content, "html.parser")

    full_name = soup.find_all("h2", class_="normal_header")[0].text
    print(full_name)
    if " (" in full_name:
        en_name, jp_name = full_name.split(" (", 1)
        jp_name = jp_name.rsplit(")", 1)[0]
    else:
        en_name = full_name
        jp_name = None

    # Images
    image_page_url = None
    all_links = soup.find_all("a", href=True)
    for link in all_links:
        if link["href"].endswith("/pics"):
            image_page_url = link["href"]

    image_urls = downloadImages(image_page_url)

    return {"char_id": char_id,
            "en_name": en_name.strip(),
            "jp_name": jp_name.strip() if jp_name else jp_name,
            "image_urls": image_urls}


def downloadImages(image_page_url):
    time.sleep(1)
    image_page = requests.get(image_page_url)
    img_soup = BeautifulSoup(image_page.content, "html.parser")

    image_urls = []
    images = img_soup.find_all("a", class_="js-picture-gallery")
    for image in images:
        if "/images/characters/" in image["href"]:
            image_urls.append(image["href"])

    # Remove duplicates
    return list(dict.fromkeys(image_urls))
