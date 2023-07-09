# UMA #
import asyncio
import math
import re
import time
import requests
import os
import datetime
import pytz
import json

import bot_token
import constants
import display
from discord import Color
import deepl
from bs4 import BeautifulSoup
import logging
logger = logging.getLogger('discord')


UPDATE_LOG = "uma_update.txt"
LAST_ARTICLES = "uma_articles.txt"
NAMES_FILE = "uma_names.txt"
TRANSLATOR = deepl.Translator(os.getenv("DEEPL_AUTH_KEY"))


UMA_NAMES = dict()
if os.path.exists(NAMES_FILE):
    with open(NAMES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            jp_name, en_name = line.rstrip().split(";", 1)
            UMA_NAMES[jp_name] = en_name


def generate_uma_names_file():
    r = requests.get("https://umamusume.jp/app/wp-json/wp/v2/character?per_page=99&page=1")
    parsed = r.json()

    with open(NAMES_FILE, "w", encoding="utf-8") as f:
        for character in parsed:
            f.write(f"""{character["title"]["rendered"]};\n""")


def save_last_check(new_news: list[tuple[int, dict]]):
    with open(UPDATE_LOG, "w") as f:
        f.write(f"{math.floor(time.time())}")
    if not new_news:
        os.remove(LAST_ARTICLES)
    else:
        with open(LAST_ARTICLES, "w") as f:
            for article_tuple in new_news:
                f.write(f"""{article_tuple[1]["announce_id"]}\t{article_tuple[0]}\n""")


def get_last_check() -> tuple[int, dict]:
    last_check = math.floor(time.time())

    if os.path.exists(UPDATE_LOG):
        with open(UPDATE_LOG, "r") as f:
            line = f.readline().strip()
            if line.isnumeric():
                last_check = int(line)

    last_news = dict()
    if os.path.exists(LAST_ARTICLES):
        with open(LAST_ARTICLES, "r") as f:
            for line in f.readlines():
                news_id, timestamp = line.rstrip().split("\t", 1)
                last_news[int(news_id)] = int(timestamp)
    
    if bot_token.isDebug():
        last_check -= 86400
    return last_check, last_news


def get_latest_news() -> list:
    r = requests.get("https://umapyoi.net/api/v1/news/latest/10")
    return r.json()


def convert_to_epoch(jst_time: str) -> int:
    dt = datetime.datetime.strptime(jst_time, "%Y-%m-%d %H:%M:%S")
    tz = pytz.timezone("Japan")
    dt_with_tz = tz.localize(dt)
    return math.floor(dt_with_tz.timestamp())


def short_date_to_epoch(date: str) -> int:
    month_day, hours_minutes = date.split(" ")
    month, day = month_day.split("/")
    hours, minutes = hours_minutes.split(":")
    current_month = datetime.datetime.now().month
    year = datetime.datetime.now().year
    if current_month == 12 and month == "1":
        year = year + 1
    dt = datetime.datetime(year, int(month), int(day), int(hours), int(minutes))
    tz = pytz.timezone("Japan")
    dt_with_tz = tz.localize(dt)
    return math.floor(dt_with_tz.timestamp())


def get_article_latest_time(article: dict) -> int:
    if "update_at" in article and article["update_at"]:
        # Article has an update, use this time!
        latest_time = article["update_at"]
    else:
        latest_time = article["post_at"]
    return latest_time


def get_new_news() -> tuple[list, int]:
    if bot_token.isDebug():
        logger.info("In get news")
    last_check, last_articles = get_last_check()

    new_articles = list()

    recent_news = get_latest_news()
    for article in recent_news:
        article_time = get_article_latest_time(article)
        if article_time > last_check - 120:  # Look for articles up to 2 minutes before the last check.
            if int(article["announce_id"]) in last_articles and article_time <= int(last_articles[article["announce_id"]]):  # If article was found recently, only show it if it has been updated since.
                pass
            else:
                new_articles.append((article_time, article))

    new_news = sorted(new_articles, key=lambda x: x[0])
    if new_news:
        save_last_check(new_news)

    return new_news, last_check


def clean_message(message: str) -> str:
    return re.sub(r"<.*?>", "", message
                  .rstrip()
                  .lstrip()
                  .replace("> ", ">")
                  .replace("<h2", "**<h2")
                  .replace("</h2>", "**<br>")
                  .replace("<br><br>", "\n\n")
                  .replace("<br>", "\n")
                  .replace("&nbsp;", " ")
                  .replace("&lt;", "<")
                  .replace("&gt;", ">"))


def make_month_day(text: str) -> tuple[int, int]:
    text = text[1:-3]
    month_day = text.split(" ", 1)[0]
    month, day = month_day.split("/", 1)

    return int(month), int(day)


def format_bug_report(en_message: str, jp_message: str) -> str:
    tz = pytz.timezone("Japan")
    localized_now = tz.localize(datetime.datetime.utcnow())
    # localized_now = tz.localize(datetime.datetime(2022, 9, 9, 8, 0))

    known_bugs = list()
    fixed_bugs = list()

    first = True
    before = "The following issues are currently occurring in the game."

    current_month_day = tuple()
    current_date_str = str()
    current_lines = list()

    in_known = False

    jp = BeautifulSoup(jp_message, "html.parser")
    en = BeautifulSoup(en_message, "html.parser")

    for element_tuple in zip(list(jp), list(en)):
        element = element_tuple[0]
        if first:
            first = False
        else:
            if not element.text:
                continue
            elif element.text == "■現在確認している不具合":
                in_known = True
            elif element.text == "■修正済みの不具合":
                in_known = False
            elif element.text[0] == "【":
                if current_lines and current_month_day and current_date_str:
                    if current_month_day == (localized_now.month, localized_now.day):
                        bug_tuple = (current_date_str, current_lines)
                        if in_known:
                            known_bugs.append(bug_tuple)
                        else:
                            fixed_bugs.append(bug_tuple)
                current_month_day = make_month_day(element.text)
                current_date_str = element_tuple[1].text
                current_lines = list()
            else:
                current_lines.append(element_tuple[1].get_text(separator="\n").lstrip().rstrip())
    if current_lines:
        if current_month_day == (localized_now.month, localized_now.day):
            bug_tuple = (current_date_str, current_lines)
            if in_known:
                known_bugs.append(bug_tuple)
            else:
                fixed_bugs.append(bug_tuple)

    known_segment = str()
    fixed_segment = str()

    logger.info(f"Known bugs: {len(known_bugs)}, fixed bugs: {len(fixed_bugs)}")

    if known_bugs:
        known_segment = "\n\n**■ Currently confirmed bugs:**\n" + "\n\n".join([segment[0] + "\n" + "\n".join(segment[1]) for segment in known_bugs])
    if fixed_bugs:
        fixed_segment = "\n\n**■ Fixed bugs:**\n" + "\n\n".join([segment[0] + "\n" + "\n".join(segment[1]) for segment in fixed_bugs])

    logger.info(fixed_segment)

    out_message = before + known_segment + fixed_segment

    return out_message


def get_first_img(message: str) -> str:
    soup = BeautifulSoup(message, "html.parser")
    img = soup.find('img')
    if img:
        return img["src"]
    return str()


def replace_names(string: str, prefix='') -> str:
    for jp_name, en_name in UMA_NAMES.items():
        string = string.replace(jp_name, prefix + en_name)
    return string


def load_current_gacha_info():
    r = requests.get("https://umapyoi.net/api/v1/gacha/current")
    r.raise_for_status()
    return r.json()


async def run():
    logger.info("Started uma process")
    if not constants.BOT_OBJECT.uma_running:
        constants.BOT_OBJECT.uma_running = True
        while True and constants.BOT_OBJECT:
            new_news, last_check = get_new_news()
            
            do_ping = False
            for article_tuple in new_news:
                logger.info(f"""{math.floor(time.time())}\tNew Uma News!\t{article_tuple[1]["announce_id"]}""")
                article = article_tuple[1]

                raw_title = article["title"]
                raw_message = article["message"]

                if bot_token.isDebug():
                    continue

                # Deal with image
                image = None
                if article.get("image"):
                    image = article["image"]
                else:
                    # Try getting the image from the article message.
                    image_from_message = get_first_img(raw_message)
                    if image_from_message:
                        image = image_from_message

                translated_title = article["title_english"]
                translated_message = article["message_english"]

                # Check for special case:
                if article["announce_id"] == 155:
                    # This is a bug report news article!
                    logger.info("Bug report found.")
                    translated_message = format_bug_report(translated_message, article['message'])
                else:
                    translated_message = clean_message(translated_message) \
                        .replace("[", "\\[") \
                        .replace("]", "\\]")  # Replacing these because of faulty parsing of url with custom text on mobile phones.

                if len(translated_message) > 2000:
                    translated_message = translated_message[:1997] + "..."
                if translated_message[-1] != "\n":
                    translated_message += "\n"
                translated_message += f"""\n[View full](https://umapyoi.net/news/{article["announce_id"]})"""
                translated_message += f"""\n[View source](https://umapyoi.net/news/{article["announce_id"]}/source)"""

                await constants.BOT_OBJECT.send_uma_embed(display.create_embed(
                    translated_title,
                    translated_message,
                    color=Color.from_rgb(105, 193, 12),
                    image=image,
                    footer="Uma Musume News",
                    timestamp=datetime.datetime.fromtimestamp(article_tuple[0])
                ), do_ping)
                do_ping = False
            delta = datetime.timedelta(hours=1)
            now = datetime.datetime.now()
            next_hour = (now + delta).replace(microsecond=0, second=0, minute=2)
            await asyncio.sleep((next_hour - now).seconds)

async def get_url_token():
    """
    Gets the url token from the gametora website.
    """
    r = requests.get("https://gametora.com/umamusume")
    match = re.search(r"_next\/static\/[^\/]*\/_buildManifest", r.text)
    if match:
        return match.group().rsplit('/', 2)[-2]
    return str()


async def get_gacha_data(url_token):
    return requests.get(f"https://gametora.com/_next/data/{url_token}/umamusume/gacha.json").json()


async def get_main_data(url_token):
    return requests.get(f"https://gametora.com/_next/data/{url_token}/umamusume.json").json()


async def create_banner_embed_old(active_banner, gacha_data, support=False):
    banner_image = f"https://gametora.com/images/umamusume/gacha/img_bnr_gacha_{active_banner['id']}.png"
    banner_thumb = None
    banner_end = active_banner['end']
    banner_card_data = dict()
    char_ids = list()
    for pickup in active_banner['pickups']:
        char_ids.append(pickup[0])
    
    data_key = 'charCardData' if not support else 'supportCardData'
    for card_data in gacha_data['pageProps'][data_key]:
        if card_data['id'] in char_ids:
            banner_card_data[card_data['id']] = card_data
    embed_title = "Current Character Banner" if not support else "Current Support Banner"
    embed_description = f"Banner pickups:\n"
    description_items = list()
    for char_id, card_data in banner_card_data.items():
        if not banner_thumb:
            if not support:
                banner_thumb = f"https://gametora.com/images/umamusume/characters/thumb/chara_stand_{str(char_id)[:-2]}_{char_id}.png"
            else:
                banner_thumb = f"https://gametora.com/images/umamusume/supports/support_card_s_{char_id}.png"
        if not support:
            description_items.append(f"**[{card_data['name']}](https://gametora.com/umamusume/characters/{card_data['url']})**")
        else:
            description_items.append(f"**[{card_data['name']}](https://gametora.com/umamusume/supports/{card_data['url']})**")
    
    embed_description += "\n".join(description_items)
    embed_description += f"\nBanner ends <t:{banner_end}:R>."

    return display.create_embed(embed_title, embed_description, color=Color.from_rgb(105, 193, 12), image=banner_image, thumbnail=banner_thumb)

def create_banner_embed(gacha_info, support=False):
    card_type = gacha_info['card_type']
    embed_title = f"Current {card_type} Banner"

    embed_description = f"Banner pickups:\n"
    for pickup in gacha_info['pickups']:
        rarity = ""
        if card_type == "Outfit":
            rarity = "★" * pickup['default_rarity']
        elif card_type == "Support Card":
            rarity = pickup['rarity_string']
        
        title = pickup['title_en'] if pickup['title_en'] else pickup['title']

        chara_name = pickup['chara_data']['name_en'] if pickup['chara_data']['name_en'] else pickup['chara_data']['name_en_internal']

        embed_description += f"**{rarity} {title} {chara_name}**\n"
    
    embed_description += f"\nBanner ends <t:{gacha_info['end_date']}:R>"

    if not gacha_info['image_url']:
        banner_image = f"https://gametora.com/images/umamusume/gacha/img_bnr_gacha_{gacha_info['id']}.png?t={int(time.time())}"
    else:
        banner_image = gacha_info['image_url']

    return display.create_embed(embed_title, embed_description, color=Color.from_rgb(105, 193, 12), image=banner_image)


async def create_gacha_embeds():
    banners = load_current_gacha_info()
    if not banners:
        return None

    return [create_banner_embed(banner) for banner in banners]