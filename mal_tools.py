import asyncio
import os
import random

import requests
from bs4 import BeautifulSoup
import time
from PIL import Image, ImageOps

import constants
import database_tools as db
import logging
logger = logging.getLogger('discord')


class CharacterImage:

    @classmethod
    async def create(cls, mal_url):
        tmp_file_name = str(random.randint(1, 99999999999999999999)) + ".jpg"
        if not os.path.exists(constants.TMP_DIR):
            os.mkdir(constants.TMP_DIR)

        normal_path = constants.TMP_DIR + "/norm_" + tmp_file_name
        mirror_path = constants.TMP_DIR + "/mirr_" + tmp_file_name
        upside_down_path = constants.TMP_DIR + "/flip_" + tmp_file_name

        image_response = requests.get(mal_url)
        if not image_response.ok:
            return None
        with open(normal_path, 'wb') as f:
            f.write(image_response.content)

        # Flip and mirror the image
        normal_image = Image.open(normal_path)
        if normal_image.mode != "RGB":
            bg_layer = Image.new("RGB", normal_image.size, (255, 255, 255))
            bg_layer.paste(normal_image, mask=normal_image.convert('RGBA').split()[3])
            bg_layer.save(normal_path, "JPEG", quality=90)
            normal_image = bg_layer
        mirror_image = ImageOps.mirror(normal_image)
        mirror_image.save(mirror_path, "JPEG", quality=90)
        upside_down_image = ImageOps.flip(normal_image)
        upside_down_image.save(upside_down_path, "JPEG", quality=90)

        new_image_urls = await constants.BOT_OBJECT.send_character_images(normal_path, mirror_path, upside_down_path)

        os.remove(normal_path)
        os.remove(mirror_path)
        os.remove(upside_down_path)

        return cls(mal_url, new_image_urls[0], new_image_urls[1], new_image_urls[2])

    def __init__(self, mal_url: str, normal_url: str, mirror_url: str, upside_down_url: str):
        self.mal_url = mal_url
        self.normal_url = normal_url
        self.mirror_url = mirror_url
        self.upside_down_url = upside_down_url


class ShowQueue:
    def __init__(self):
        self.running = False
        self.show_queue = []

    def has_next(self):
        return bool(self.show_queue)


    def __len__(self):
        return len(self.show_queue)


    def get_url(self):
        if self.show_queue:
            return self.show_queue[0]
        else:
            return None


    def add_url(self, url):
        self.show_queue.append(url)
    
    def pop(self):
        if self.show_queue:
            return self.show_queue.pop(0)
        return None

def getShowURLSegment(show_url):
    no_domain = show_url.split("myanimelist.net/")[1]
    if "?" in no_domain:
        no_domain = no_domain.split("?", 1)[0]
    if no_domain.startswith("anime/"):
        is_manga = False
    elif no_domain.startswith("manga/"):
        is_manga = True
    else:
        logger.error("Not a valid MAL anime/manga URL!")
        return None, None
    return no_domain.split("/", 1)[1], is_manga


def getShowID(show_url):
    show_url_segment, is_manga = getShowURLSegment(show_url)
    if show_url_segment:
        if show_url_segment.isnumeric():
            return show_url_segment
        show_id = show_url_segment.split("/")[0]
        if show_id.isnumeric():
            return int(show_id)
    return None


async def downloadInsertShowCharacters(show_url, overwrite=False):
    show_url_segment, is_manga = getShowURLSegment(show_url)
    mal_id = getShowID(show_url)
    if not show_url_segment or not mal_id:
        logger.error("Show url not found.")
        return -1
    logger.info("="*20)
    logger.info(f"{is_manga}, {show_url_segment}")

    if show_url_segment.isnumeric():
        if is_manga:
            request_url = f"https://myanimelist.net/manga/{mal_id}"
        else:
            request_url = f"https://myanimelist.net/anime/{mal_id}"

        await asyncio.sleep(20)
        page = requests.get(request_url)

        if not page.ok:
            logger.error(f"Error in get-request {request_url}")
            return

        soup = BeautifulSoup(page.content, "html.parser")

        character_href = soup.find_all('a', text="More characters")[0]['href']
        if not character_href:
            logger.error(f"Could not find character href on page {request_url}")
            return
        if not character_href.startswith("https://"):
            character_href = """https://myanimelist.net""" + character_href
    
    else:
        if is_manga:
            character_href = f"https://myanimelist.net/manga/{show_url_segment}/characters"
        else:
            character_href = f"https://myanimelist.net/anime/{show_url_segment}/characters"

    await asyncio.sleep(20)
    page = requests.get(character_href)
    soup = BeautifulSoup(page.content, "html.parser")

    if not is_manga:
        jp_title_element = soup.find("h1", class_="title-name")
    else:
        jp_title_element = soup.find("span", itemprop="name")
    if not jp_title_element:
        logger.error(f"Could not find JP Anime Title for {show_url_segment}")
        return -1
    jp_title = jp_title_element.text
    en_title_element = soup.find("p", class_="title-english")
    en_title = en_title_element.text if en_title_element else None

    if is_manga:
        if jp_title_element.find("span", class_="title-english"):
            jp_title = jp_title_element.contents[0]
            en_title = jp_title_element.find("span", class_="title-english").text

    if not db.show_exists_by_mal(mal_id, is_manga):
        db.insert_show(mal_id, jp_title, en_title, is_manga)

    show_id = db.get_show_id_by_mal(mal_id, is_manga)

    if not is_manga:
        character_tables = soup.find_all("table", class_="js-anime-character-table")
    else:
        character_tables = soup.find_all("table", class_="js-manga-character-table")

    character_count = len(character_tables)
    logger.info(f"Found {character_count} characters.")

    for character_table in character_tables:
        character_url = character_table.find_all("a", href=True)[0]
        character_id = getCharacterIDFromURL(character_url["href"])
        if not overwrite:
            # Check if already exists and ignore if so.
            if db.character_exists(character_id):
                if db.character_has_show(character_id, show_id):
                    logger.warn(f"Character {character_id} already exists.")
                    continue
                else:
                    # Add show to character.
                    db.add_show_to_character(character_id, show_id)
                    continue
        character_data = await downloadCharacterFromURL(character_url["href"])
        db.insert_character(character_data, overwrite=overwrite)
        db.add_show_to_character(character_id, show_id)


def getCharacterIDFromURL(character_url):
    return character_url.split("myanimelist.net/character/")[1].split("/")[0]


async def downloadCharacterFromURL(character_url):
    return await downloadCharacter(character_url.split("myanimelist.net/character/")[1].split("/")[0])


async def downloadCharacter(char_id):
    logger.info(f"Downloading character {char_id}")
    await asyncio.sleep(20)

    page = requests.get(f"https://myanimelist.net/character/{char_id}")
    soup = BeautifulSoup(page.content, "html.parser")

    full_name = soup.find_all("h2", class_="normal_header")[0].text
    logger.info(full_name)
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

    image_objects = await getImages(image_page_url, char_id)

    return {"char_id": char_id,
            "en_name": en_name.strip(),
            "jp_name": jp_name.strip() if jp_name else jp_name,
            "images": image_objects}


async def getImages(image_page_url, char_id):
    await asyncio.sleep(2)
    image_page = requests.get(image_page_url)
    img_soup = BeautifulSoup(image_page.content, "html.parser")

    image_urls = []
    images = img_soup.find_all("a", class_="js-picture-gallery")
    for image in images:
        if "/images/characters/" in image["href"]:
            image_urls.append(image["href"])

    # Remove duplicates
    image_urls = list(dict.fromkeys(image_urls))

    existing_image_urls = db.get_character_image_urls(char_id)

    image_objects = list()
    for image_url in image_urls:
        if image_url not in existing_image_urls:
            await asyncio.sleep(30)
            image_objects.append(await CharacterImage.create(image_url))

    return image_objects


async def run_queue(show_queue: ShowQueue):
    while show_queue.has_next():
        await downloadInsertShowCharacters(show_queue.get_url(), overwrite=True)
        show_queue.pop()
    show_queue.running = False

def show_url_from_id(mal_id, is_manga):
    base = """https://myanimelist.net/"""
    if is_manga:
        base += "manga/"
    else:
        base += "anime/"
    base += str(mal_id)
    return base