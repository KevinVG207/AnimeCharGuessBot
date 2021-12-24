import requests
from bs4 import BeautifulSoup
import time


def downloadCharacter(char_id):
    print(f"Downloading character {char_id}")
    time.sleep(0.5)

    page = requests.get(f"https://myanimelist.net/character/{char_id}")
    soup = BeautifulSoup(page.content, "html.parser")

    full_name = soup.find_all("h2", class_="normal_header")[0].text
    en_name, jp_name = full_name.split(" (")
    jp_name = jp_name.replace(")", "")

    time.sleep(0.5)

    # Images
    image_page_url = None
    all_links = soup.find_all("a", href=True)
    for link in all_links:
        if link["href"].endswith("/pics"):
            image_page_url = link["href"]

    image_urls = downloadImages(image_page_url)

    return char_id, en_name, jp_name, image_urls


def downloadImages(image_page_url):
    image_page = requests.get(image_page_url)
    img_soup = BeautifulSoup(image_page.content, "html.parser")

    image_urls = []
    images = img_soup.find_all("a", class_="js-picture-gallery")
    for image in images:
        if "/images/characters/" in image["href"]:
            image_urls.append(image["href"])

    # Remove duplicates
    return list(dict.fromkeys(image_urls))
