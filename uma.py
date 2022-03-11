# UMA #
import asyncio
import math
import re
import time
import requests
import os
from datetime import datetime
import pytz
import constants
import display
from discord import Color
import deepl


UPDATE_LOG = "uma_update.txt"
TRANSLATOR = deepl.Translator(os.getenv("DEEPL_AUTH_KEY"))

def save_last_check():
    with open(UPDATE_LOG, "w") as f:
        f.write(f"{math.floor(time.time())}")


def get_last_check() -> int:
    if os.path.exists(UPDATE_LOG):
        with open(UPDATE_LOG, "r") as f:
            line = f.readline().strip()
            if line.isnumeric():
                return int(line)
    last_check = math.floor(time.time())
    # last_check = math.floor(time.time()) - 604800
    return last_check


def get_last_news() -> list:
    payload = {
        "announce_label": 1,  # 0=all, 1=game, 2=campaign(social media stuff), 3=media
        "limit": 10,
        "offset": 0
    }
    r = requests.post("https://umamusume.jp/api/ajax/pr_info_index?format=json", json=payload)
    return r.json()["information_list"]


def convert_to_epoch(jst_time: str) -> int:
    dt = datetime.strptime(jst_time, "%Y-%m-%d %H:%M:%S")
    tz = pytz.timezone("Japan")
    dt_with_tz = tz.localize(dt)
    return math.floor(dt_with_tz.timestamp())


def get_article_latest_time(article: dict) -> int:
    if "update_at" in article and article["update_at"]:
        # Article has an update, use this time!
        latest_time = article["update_at"]
    else:
        latest_time = article["post_at"]
    return convert_to_epoch(latest_time)


def get_new_news() -> list:
    last_check = get_last_check()

    new_articles = list()

    recent_news = get_last_news()
    for article in recent_news:
        article_time = get_article_latest_time(article)
        if article_time > last_check:
            new_articles.append((article_time, article))

    new_news = sorted(new_articles, key=lambda x: x[0])

    save_last_check()
    return new_news


def clean_message(message: str) -> str:
    return re.sub(r"<.*?>", "", message
                  .replace("</div><br>", "</div><br><br>")
                  .replace("<br>", "\n")
                  .replace("&nbsp;", " ")
                  .replace("&lt;", "<")
                  .replace("&gt;", ">"))


async def run():
    while True and constants.BOT_OBJECT:
        new_news = get_new_news()
        for article_tuple in new_news:
            print(f"{time.time()}\tNew Uma News!")
            article = article_tuple[1]
            translated_title = TRANSLATOR.translate_text(article["title"], target_lang="EN-US")
            raw_message = clean_message(article["message"])[:4000]
            translated_message = TRANSLATOR.translate_text(raw_message, target_lang="EN-US").text \
                .replace("[", "\\[") \
                .replace("]", "\\]")  # Replacing these because of faulty parsing of url with custom text on mobile phones.
            if len(translated_message) > 2000:
                translated_message = translated_message[:1997] + "..."
            if translated_message[-1] != "\n":
                translated_message += "\n"
            translated_message += f"""\n[View source](https://umamusume.jp/news/detail.php?id={article["announce_id"]})"""

            await constants.BOT_OBJECT.send_uma_embed(display.create_embed(
                translated_title,
                translated_message,
                color=Color.from_rgb(105, 193, 12),
                image=article.get("image"),
                footer="Uma Musume News",
                timestamp=datetime.fromtimestamp(article_tuple[0])
            ))

        await asyncio.sleep(750)
