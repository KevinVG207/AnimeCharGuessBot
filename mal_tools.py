import requests
from bs4 import BeautifulSoup
import time
import database as db


def getAnimeURLSegment(anime_url):
    return anime_url.split("myanimelist.net/anime/")[1] if "myanimelist.net/anime/" in anime_url else None


def downloadInsertAnimeCharacters(anime_url, overwrite=False):
    anime_url_segment = getAnimeURLSegment(anime_url)
    print(anime_url_segment)
    time.sleep(1)
    page = requests.get(f"https://myanimelist.net/anime/{anime_url_segment}/characters")
    soup = BeautifulSoup(page.content, "html.parser")

    character_tables = soup.find_all("table", class_="js-anime-character-table")

    character_count = len(character_tables)
    print(f"Found {character_count} characters.")

    for character_table in character_tables:
        character_url = character_table.find_all("a", href=True)[0]
        character_id = getCharacterIDFromURL(character_url["href"])
        if not overwrite:
            # Check if already exists and ignore if so.
            if db.characterExists(character_id):
                print(f"Character {character_id} already exists.")
                continue
        db.insertCharacter(downloadCharacterFromURL(character_url["href"]))


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
