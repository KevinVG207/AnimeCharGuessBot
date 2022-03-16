# UMA #
import asyncio
import math
import re
import time
import requests
import os
import datetime
import pytz

import bot_token
import constants
import display
from discord import Color
import deepl
from bs4 import BeautifulSoup


UPDATE_LOG = "uma_update.txt"
LAST_ARTICLES = "uma_articles.txt"
NAMES_FILE = "uma_names.txt"
TRANSLATOR = deepl.Translator(os.getenv("DEEPL_AUTH_KEY"))


def get_uma_names() -> dict:
    uma_names = dict()
    if os.path.exists(NAMES_FILE):
        with open(NAMES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                jp_name, en_name = line.rstrip().split(";", 1)
                uma_names[jp_name] = en_name
    return uma_names


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
    if bot_token.isDebug():
        last_check -= 604800

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
    return last_check, last_news


def get_last_news() -> list:
    payload = {
        "announce_label": 1,  # 0=all, 1=game, 2=campaign(social media stuff), 3=media
        "limit": 10,
        "offset": 0
    }
    r = requests.post("https://umamusume.jp/api/ajax/pr_info_index?format=json", json=payload)
    return r.json()["information_list"]


def convert_to_epoch(jst_time: str) -> int:
    dt = datetime.datetime.strptime(jst_time, "%Y-%m-%d %H:%M:%S")
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


def get_new_news() -> tuple[list, int]:
    last_check, last_articles = get_last_check()

    new_articles = list()

    recent_news = get_last_news()
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
                  .replace("<br>", "\n\n")
                  .replace("&nbsp;", " ")
                  .replace("&lt;", "<")
                  .replace("&gt;", ">"))


def make_month_day(text: str) -> tuple[int, int]:
    text = text[1:-3]
    month_day = text.split(" ", 1)[0]
    month, day = month_day.split("/", 1)

    return int(month), int(day)


def format_bug_report(message: str) -> str:
    tz = pytz.timezone("Japan")
    localized_now = tz.localize(datetime.datetime.utcnow())

    known_bugs = list()
    fixed_bugs = list()

    first = True
    before = str()

    current_month_day = tuple()
    current_date_str = str()
    current_lines = list()

    in_known = False

    soup = BeautifulSoup(message, "html.parser")
    for element in soup:
        if first:
            first = False
            before = element.text
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
                current_date_str = element.text
                current_lines = list()
            else:
                current_lines.append(element.text)
    if current_lines:
        if current_month_day == (localized_now.month, localized_now.day):
            bug_tuple = (current_date_str, current_lines)
            if in_known:
                known_bugs.append(bug_tuple)
            else:
                fixed_bugs.append(bug_tuple)

    known_segment = str()
    fixed_segment = str()

    if known_bugs:
        known_segment = "\n\n■現在確認している不具合\n" + "\n\n".join([segment[0] + "\n" + "\n".join(segment[1]) for segment in known_bugs])
    if fixed_bugs:
        fixed_segment = "\n\n■修正済みの不具合\n" + "\n\n".join([segment[0] + "\n" + "\n".join(segment[1]) for segment in fixed_bugs])

    out_message = before + known_segment + fixed_segment

    return out_message


async def run():
    uma_names = get_uma_names()
    if not constants.BOT_OBJECT.uma_running:
        constants.BOT_OBJECT.uma_running = True
        while True and constants.BOT_OBJECT:
            new_news, last_check = get_new_news()
            for article_tuple in new_news:
                print(f"""{math.floor(time.time())}\tNew Uma News!\t{article_tuple[1]["announce_id"]}""")
                article = article_tuple[1]

                raw_title = article["title"]
                raw_message = article["message"]

                for jp_name, en_name in uma_names.items():
                    raw_title = raw_title.replace(jp_name, en_name)
                    raw_message = raw_message.replace(jp_name, en_name)

                translated_title = TRANSLATOR.translate_text(raw_title, target_lang="EN-US")

                # Check for special case:
                if article["title"] == "現在確認している不具合について":
                    # This is a bug report news article!
                    raw_message = format_bug_report(raw_message)

                cleaned_message = clean_message(raw_message)[:4000]
                translated_message = TRANSLATOR.translate_text(cleaned_message, target_lang="EN-US").text \
                    .replace("[", "\\[") \
                    .replace("]", "\\]")  # Replacing these because of faulty parsing of url with custom text on mobile phones.
                if len(translated_message) > 2000:
                    translated_message = translated_message[:1997] + "..."
                if translated_message[-1] != "\n":
                    translated_message += "\n"
                translated_message += f"""\n[View source](https://umamusume.jp/news/detail.php?id={article["announce_id"]})"""

                print(translated_message)

                await constants.BOT_OBJECT.send_uma_embed(display.create_embed(
                    translated_title,
                    translated_message,
                    color=Color.from_rgb(105, 193, 12),
                    image=article.get("image"),
                    footer="Uma Musume News",
                    timestamp=datetime.datetime.fromtimestamp(article_tuple[0])
                ))
            delta = datetime.timedelta(hours=1)
            now = datetime.datetime.now()
            next_hour = (now + delta).replace(microsecond=0, second=0, minute=1)
            await asyncio.sleep((next_hour - now).seconds)
