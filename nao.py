from bs4 import BeautifulSoup as bs
import requests
import datetime
import pytz
import util

def get_sauce(image_url, min_similarity=90):
    url = "https://saucenao.com/search.php"
    form_data = {
        "file": b"",
        "url": image_url,
        "dbs[]": [9, 25]
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    }
    r = requests.post(url, headers=headers, data=form_data)
    r.raise_for_status()
    soup = bs(r.content, "html.parser")
    results = soup.find_all("div", class_="result")
    real_results = []

    for result in results:
        try:
            similarity = float(result.find("div", class_="resultsimilarityinfo").text[:-1])
        except:
            similarity = 0
        if similarity >= min_similarity:
            real_results.append(result)
    return real_results


def find_pixiv_or_twitter_source(image_url):
    results = get_sauce(image_url)
    for result in results:
        source = result.find("div", class_="resultcontentcolumn").find("a").get("href")
        if "pixiv.net" in source or "twitter.com" in source or "x.com" in source or "nicovideo.jp" in source:
            if "pixiv.net" in source:
                source = source.replace("pixiv.net", "phixiv.net")
            else:
                source = source.replace("twitter.com", "vxtwitter.com").replace("x.com", "vxtwitter.com")
            return source
    return None

def make_message_text_if_source(image_url, message):
    source = find_pixiv_or_twitter_source(image_url)
    if source:
        return f"🚨🚨 WEE WOO WEE WOO 🚨🚨\n<@{message.author.id}> posted cringe (an unsourced image)!\nThe bot was able to find it on saucenao.com, **so there's no excuse for you not to do the same.**\nPlease post the source next time, or at least try to find it using <https://saucenao.com>\nAs punishment. You are now in timeout for 60 seconds!\nUse this time to repent and change your ways. (And touch grass 草)"
    return None

async def check_images(message):
    urls = list(util.get_image_urls(message.content))

    if message.content and not urls:
        # Don't check messages with content.
        # The user might have already posted the source.
        return
    


    if message.attachments:
        for attachment in message.attachments:
            if attachment.content_type.startswith("image"):
                urls.append(attachment.url)
    
    try:
        for url in urls:
            if url:
                message_text = make_message_text_if_source(url, message)
                if message_text:
                    await message.reply(message_text)
                    await message.author.timeout(datetime.datetime.now(pytz.UTC) + datetime.timedelta(seconds=60), reason="You posted cringe. Go touch grass.")
                    return
                    # message_text = make_message_text_if_source(attachment.url, message)
                    # if message_text:
                    #     await message.reply(message_text)
                    #     await message.author.timeout(datetime.datetime.now(pytz.UTC) + datetime.timedelta(seconds=60), reason="You posted cringe. Go touch grass.")
                    #     return
    except Exception as e:
        return

def main():
    # asyncio.run(get_sauce("https://pbs.twimg.com/media/F0b_qoJacAAZQlz.jpg"))
    results = get_sauce("https://pbs.twimg.com/media/F0b_qoJacAAZQlz.jpg")
    print(results)

if __name__ == "__main__":
    main()