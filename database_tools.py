import asyncio
import datetime
import os.path
import random
import sqlite3

import bot_token
import constants
import mal_tools
import name_tools as nt
import logging
logger = logging.getLogger('discord')

WORKING_DIR = os.path.dirname(os.path.realpath(__file__))
DATABASE_URI = WORKING_DIR + "/database/database.db"

DAILY_CURRENCY = 500


def get_connection():
    conn = sqlite3.connect(DATABASE_URI)
    return conn, conn.cursor()


def create_database():
    logger.info("Setting up DB.")
    conn, cursor = get_connection()

    create_script = open("database/create.sql")
    sql_as_string = create_script.read()
    cursor.executescript(sql_as_string)
    create_script.close()

    conn.close()
    logger.info("Finished setting up DB")


def bulk_insert_character(character_data_list):
    for character_data in character_data_list:
        insert_character(character_data)


def insert_character(char_data, alt_name=None, overwrite=False):
    char_id = char_data["char_id"]
    en_name = char_data["en_name"]
    jp_name = char_data["jp_name"]
    images = char_data["images"]

    exists = character_exists(char_id)

    if exists and not overwrite:
        logger.warn(f"Character {char_id} {en_name} already exists in the database and not overwriting.")
        return

    if not images:
        logger.warn(f"Character {char_id} {en_name} does not have any images. Skipping.")
        return

    logger.info(f"Inserting character {char_id} {en_name}")
    conn, cursor = get_connection()

    if overwrite and exists:
        # Character exists but we are overwriting its data.
        # UNLESS it has an alt_name set, because it might have been manually changed.
        cursor.execute("""UPDATE character SET en_name = ?, jp_name = ? WHERE id = ? AND alt_name = NULL;""",
                        (en_name, jp_name, char_id))
    else:
        if not exists:
            cursor.execute("""INSERT INTO character (id, en_name, jp_name, alt_name) VALUES (?,?,?,?);""",
                        (char_id, en_name, jp_name, alt_name))
    
    for image in images:
        if not character_has_image(cursor, char_id, image.mal_url):
            logger.info(f"Inserting image {image.mal_url}")
            cursor.execute("""INSERT INTO images (character_id, mal_url, normal_url, mirror_url, flipped_url) VALUES (?,?,?,?,?);""", (char_id, image.mal_url, image.normal_url, image.mirror_url, image.upside_down_url))
        else:
            logger.warn(f"Character {char_id} already has image with MAL URL {image.mal_url}. Skipping image.")

    conn.commit()
    conn.close()


def guild_exists(guild_id):
    conn, cursor = get_connection()
    cursor.execute("""SELECT id FROM guild WHERE id = ?;""", (guild_id,))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        # Guild does not exist
        return False
    else:
        # Guild does exist
        return True


def character_exists(char_id):
    conn, cursor = get_connection()
    cursor.execute("""SELECT id FROM character WHERE id = ?;""", (char_id,))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return False
    else:
        return True


def show_exists_by_mal(mal_id, is_manga):
    conn, cursor = get_connection()
    cursor.execute("""SELECT id FROM show WHERE mal_id = ? AND is_manga = ?;""", (mal_id, is_manga))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return False
    else:
        return True


def show_exists(show_id):
    conn, cursor = get_connection()
    cursor.execute("""SELECT id FROM show WHERE id = ?;""", (show_id,))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return False
    else:
        return True


def waifu_exists(waifus_id, connection=None):
    if not connection:
        conn, cursor = get_connection()
    else:
        conn, cursor = connection
    cursor.execute("""SELECT id FROM waifus WHERE id = ?;""", (waifus_id,))
    rows = cursor.fetchall()

    if not connection:
        conn.close()

    if not rows:
        return False
    else:
        return True


def assign_channel_to_guild(channel_id, guild_id):
    conn, cursor = get_connection()
    if guild_exists(guild_id):
        # Guild already exists, update channel.
        cursor.execute("""UPDATE guild SET channel_id = ? WHERE id = ?;""", (channel_id, guild_id))
    else:
        # Guild does not exist, insert it.
        cursor.execute("""INSERT INTO guild (id, channel_id) VALUES (?,?);""", (guild_id, channel_id))
    conn.commit()
    conn.close()


def get_assigned_channel_id(guild_id):
    channel_id = None

    conn, cursor = get_connection()
    cursor.execute("""SELECT channel_id FROM guild WHERE id = ?;""", (guild_id,))
    rows = cursor.fetchall()
    conn.close()
    if rows and rows[0]:
        channel_id = rows[0][0]

    return channel_id


def can_drop(guild_id):
    conn, cursor = get_connection()
    cursor.execute("""SELECT can_drop FROM guild WHERE id = ? AND can_drop = 1;""", (guild_id,))
    rows = cursor.fetchall()
    conn.close()
    if rows:
        return True
    else:
        return False


def can_trade(user_id):
    conn, cursor = get_connection()
    cursor.execute("""SELECT can_trade FROM user WHERE id = ? AND can_trade = 1;""", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    if rows:
        return True
    else:
        return False


def can_remove(user_id):
    conn, cursor = get_connection()
    cursor.execute("""SELECT can_remove FROM user WHERE id = ? AND can_remove = 1;""", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    if rows:
        return True
    else:
        return False


def get_drop_data(history=None, price=None, user_id=None):
    conn, cursor = get_connection()
    if history:
        if bot_token.isDebug():
            cursor.execute(
                f"""SELECT DISTINCT c.id FROM character c JOIN images i on c.id = i.character_id WHERE c.droppable = 1 AND i.normal_url IS NOT NULL AND c.id NOT IN ({",".join(["?" for _ in history])});""",
                tuple(history))
        else:
            cursor.execute(
                f"""SELECT DISTINCT id FROM character WHERE droppable = 1 AND id NOT IN ({",".join(["?" for _ in history])});""",
                tuple(history))
    else:
        cursor.execute("""SELECT DISTINCT id FROM character WHERE droppable = 1;""")
    rows = cursor.fetchall()

    char_id = random.choice(rows)[0]
    if bot_token.isDebug():
        cursor.execute("""SELECT en_name, alt_name, images.id, jp_name, normal_url, mirror_url, flipped_url FROM character
LEFT JOIN images ON character.id = images.character_id
WHERE images.droppable = 1 AND normal_url IS NOT NULL AND character.id = ?;""", (char_id,))
    else:
        cursor.execute("""SELECT en_name, alt_name, images.id, jp_name, normal_url, mirror_url, flipped_url FROM character
LEFT JOIN images ON character.id = images.character_id
WHERE images.droppable = 1 AND character.id = ?;""", (char_id,))
    rows2 = cursor.fetchall()

    conn.close()

    random.shuffle(rows2)
    en_name = rows2[0][0]
    alt_name = rows2[0][1]
    jp_name = rows2[0][3]
    image_id = rows2[0][2]
    normal_url = rows2[0][4]
    mirror_url = rows2[0][5]
    flipped_url = rows2[0][6]
    rarity, price = generate_rarity(price)

    cur_waifu = {"id": char_id,
                 "en_name": en_name,
                 "jp_name": jp_name,
                 "alt_name": alt_name,
                 "image_url": normal_url,
                 "image_id": image_id,
                 "rarity": rarity,
                 "normal_url": normal_url,
                 "mirror_url": mirror_url,
                 "flipped_url": flipped_url}

    if price and user_id:
        # We are rolling.
        # Deduct price

        subtract_user_currency(user_id, price)

        return cur_waifu, price

    return cur_waifu


def disable_drops(guild_id):
    conn, cursor = get_connection()
    cursor.execute("""UPDATE guild SET can_drop = 0 WHERE id = ?;""", (guild_id,))
    conn.commit()
    conn.close()


def enable_drops(guild_id):
    conn, cursor = get_connection()
    cursor.execute("""UPDATE guild SET can_drop = 1 WHERE id = ?;""", (guild_id,))
    conn.commit()
    conn.close()


def enable_trade(user_id):
    conn, cursor = get_connection()
    cursor.execute("""UPDATE user SET can_trade = 1 WHERE id = ?;""", (user_id,))
    conn.commit()
    conn.close()


def disable_trade(user_id):
    conn, cursor = get_connection()
    cursor.execute("""UPDATE user SET can_trade = 0 WHERE id = ?;""", (user_id,))
    conn.commit()
    conn.close()


def enable_remove(user_id):
    conn, cursor = get_connection()
    cursor.execute("""UPDATE user SET can_remove = 1 WHERE id = ?;""", (user_id,))
    conn.commit()
    conn.close()


def disable_remove(user_id):
    conn, cursor = get_connection()
    cursor.execute("""UPDATE user SET can_remove = 0 WHERE id = ?;""", (user_id,))
    conn.commit()
    conn.close()


def enable_all_drops():
    conn, cursor = get_connection()
    cursor.execute("""UPDATE guild SET can_drop = 1;""")
    conn.commit()
    conn.close()


def enable_all_trades():
    conn, cursor = get_connection()
    cursor.execute("""UPDATE user SET can_trade = 1;""")
    conn.commit()
    conn.close()


def enable_all_removes():
    conn, cursor = get_connection()
    cursor.execute("""UPDATE user SET can_remove = 1;""")
    conn.commit()
    conn.close()


def ensure_user_exists(user_id, connection=None):
    if connection:
        conn, cursor = connection
    else:
        conn, cursor = get_connection()
    cursor.execute("""SELECT id FROM user WHERE id = ?;""", (user_id,))
    rows = cursor.fetchall()
    if not rows:
        # User does not exist
        cursor.execute("""INSERT INTO user (id, last_daily) VALUES (?,?);""", (user_id, datetime.datetime.now()))
        conn.commit()
    if not connection:
        conn.close()


def add_waifu(user_id, image_id, rarity, connection=None):
    ensure_user_exists(user_id)
    if not connection:
        conn, cursor = get_connection()
    else:
        conn, cursor = connection
    cursor.execute("""INSERT INTO waifus (user_id, images_id, rarity) VALUES (?,?,?);""", (user_id, image_id, rarity))

    if not connection:
        conn.commit()
        conn.close()


def divide_waifus(waifus_list, chunk_size):
    # looping till length l
    for i in range(0, len(waifus_list), chunk_size):
        yield waifus_list[i:i + chunk_size]


def get_all_waifu_data_for_user(user_id):
    ensure_user_exists(user_id)
    conn, cursor = get_connection()

    cursor.execute("""SELECT en_name, jp_name, s.image_index, rarity, s.char_id, images_id, waifus.id, s.url, waifus.favorite
FROM waifus
LEFT JOIN (SELECT w.id as id, w.character_id as char_id, c.en_name as en_name, c.jp_name as jp_name, w.row_num as image_index, w.normal_url as url
FROM character c
LEFT JOIN (SELECT id, character_id, normal_url, ROW_NUMBER() OVER (PARTITION BY character_id ORDER BY id) AS row_num FROM images) w
ON w.character_id = c.id) s
ON waifus.images_id = s.id
WHERE waifus.user_id = ?
ORDER BY waifus.id;""", (user_id,))
    rows = cursor.fetchall()
    
    waifus = [
        {
            "en_name": row[0],
            "jp_name": row[1],
            "image_index": row[2],
            "rarity": row[3],
            "id": row[4],
            "image_id": row[5],
            "waifus_id": row[6],
            "card_index": index,
            "image_url": row[7],
            "favorite": row[8]
        }
        for index, row in enumerate(rows)
    ]

    conn.close()

    return waifus

def get_waifus(user_id, rarity=None, name_query=None, show_id=None, page_size=25, unpaginated=False, inventory_index=None):
    ensure_user_exists(user_id)
    conn, cursor = get_connection()

    if show_id:
        cursor.execute("""SELECT en_name, s.image_index, rarity, s.char_id, images_id, waifus.id, s.url, waifus.favorite, sc.show_id
FROM waifus
LEFT JOIN (SELECT w.id as id, w.character_id as char_id, c.en_name as en_name, w.row_num as image_index, w.mal_url as url
FROM character c
LEFT JOIN (SELECT id, character_id, mal_url, ROW_NUMBER() OVER (PARTITION BY character_id ORDER BY id) AS row_num FROM images) w
ON w.character_id = c.id) s
ON waifus.images_id = s.id
LEFT JOIN (
    SELECT char_id, show_id
    FROM show_character
    WHERE show_id = ?
    ) sc
ON sc.char_id = s.char_id
WHERE waifus.user_id = ?
ORDER BY waifus.id;""", (show_id, user_id))
    else:
        cursor.execute("""SELECT en_name, s.image_index, rarity, s.char_id, images_id, waifus.id, s.url, waifus.favorite
FROM waifus
LEFT JOIN (SELECT w.id as id, w.character_id as char_id, c.en_name as en_name, w.row_num as image_index, w.normal_url as url
FROM character c
LEFT JOIN (SELECT id, character_id, normal_url, ROW_NUMBER() OVER (PARTITION BY character_id ORDER BY id) AS row_num FROM images) w
ON w.character_id = c.id) s
ON waifus.images_id = s.id
WHERE waifus.user_id = ?
ORDER BY waifus.id;""", (user_id,))
    rows = cursor.fetchall()
    waifus = []
    final_pages = []
    index = 0

    for row in rows:
        index += 1
        if rarity and rarity >= 0:
            if row[2] != rarity:
                continue
        if name_query and (nt.romanizationFix(name_query.lower()) not in nt.romanizationFix(row[0].lower())):
            continue

        cur_waifu = {"en_name": row[0],
                     "image_index": row[1],
                     "rarity": row[2],
                     "char_id": row[3],
                     "image_id": row[4],
                     "waifus_id": row[5],
                     "index": index,
                     "image_url": row[6],
                     "favorite": row[7]}

        if show_id:
            if row[8] is not None:
                cur_waifu["show_id"] = show_id
            else:
                continue

        if inventory_index and index == inventory_index:
            conn.close()
            return [cur_waifu]

        if not inventory_index:
            waifus.append(cur_waifu)

    conn.close()

    if waifus:
        if unpaginated:
            final_pages = waifus
        else:
            final_pages = list(divide_waifus(waifus, page_size))

    return final_pages


def remove_guild(guild_id):
    conn, cursor = get_connection()
    cursor.execute("""DELETE FROM guild WHERE id = ?;""", (guild_id,))
    conn.commit()
    conn.close()


def get_waifu_count(user_id):
    ensure_user_exists(user_id)
    conn, cursor = get_connection()
    cursor.execute("""SELECT COUNT() FROM waifus WHERE user_id = ? ORDER BY id;""", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return 0
    else:
        return rows[0][0]


def get_waifu_image_index(waifu_id):
    conn, cursor = get_connection()
    cursor.execute("""SELECT s.image_index
FROM waifus
LEFT JOIN (SELECT w.id as id, c.en_name as en_name, w.row_num as image_index
FROM character c
LEFT JOIN (SELECT id, character_id, ROW_NUMBER() OVER (PARTITION BY character_id ORDER BY id) AS row_num FROM images) w
ON w.character_id = c.id) s
ON waifus.images_id = s.id
WHERE waifus.id = ?;""", (waifu_id,))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return -1
    return rows[0][0]


def get_waifu_data_of_user(user_id, waifu_index):
    ensure_user_exists(user_id)

    if waifu_index < 1:
        # Negative numbers are taken from the end.
        count = get_waifu_count(user_id)

        if count == 0:
            return None

        waifu_index %= count

    else:
        # Waifus are 1-indexed.
        waifu_index -= 1

    conn, cursor = get_connection()

    cursor.execute("""SELECT en_name, jp_name, character_id, normal_url, waifus.id, rarity, waifus.images_id, waifus.favorite
FROM waifus
LEFT JOIN images i ON waifus.images_id = i.id
LEFT JOIN character c ON i.character_id = c.id
WHERE user_id = ?
LIMIT ?, 1;""", (user_id, waifu_index))

    row = cursor.fetchone()

    conn.close()

    if not row:
        return None
    return {"en_name": row[0],
            "jp_name": row[1],
            "id": row[2],
            "image_url": row[3],
            "image_index": get_waifu_image_index(row[4]),
            "rarity": row[5],
            "waifus_id": row[4],
            "image_id": row[6],
            "favorite": row[7],
            "card_index": waifu_index}


def insert_show(mal_id, jp_title, en_title, is_manga):
    conn, cursor = get_connection()
    logger.info(f"Inserting show {mal_id} {en_title}, is_manga: {is_manga}")

    cursor.execute("""INSERT INTO show (mal_id, jp_title, en_title, is_manga) VALUES (?,?,?,?)""",
                   (mal_id, jp_title, en_title, is_manga))

    conn.commit()
    conn.close()


def get_show_id_by_mal(mal_id, is_manga):
    conn, cursor = get_connection()
    cursor.execute("""SELECT id FROM show WHERE mal_id = ? AND is_manga = ?;""", (mal_id, is_manga))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return None
    else:
        return rows[0][0]


def character_has_show(char_id, show_id):
    conn, cursor = get_connection()
    cursor.execute("""SELECT id FROM show_character WHERE char_id = ? AND show_id = ?;""", (char_id, show_id))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return False
    else:
        return True

def character_has_image(cursor, char_id, mal_url):
    cursor.execute("""SELECT id FROM images WHERE character_id = ? AND mal_url = ?;""", (char_id, mal_url))
    rows = cursor.fetchall()
    if not rows:
        return False
    else:
        return True


def add_show_to_character(char_id, show_id):
    conn, cursor = get_connection()
    logger.info(f"Adding show {show_id} to character {char_id}")
    cursor.execute("""INSERT INTO show_character (char_id, show_id) VALUES (?,?);""", (char_id, show_id))
    conn.commit()
    conn.close()


def get_characters_without_shows():
    conn, cursor = get_connection()
    cursor.execute("""select * from character
left join show_character sc on character.id = sc.char_id
where sc.id is null;""")
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_character_data_like(search_query):
    conn, cursor = get_connection()
    wildcard_query = f"%{search_query}%"
    cursor.execute('SELECT id, en_name FROM character WHERE en_name LIKE ? or jp_name LIKE ? or alt_name LIKE ? LIMIT 25',
                    (wildcard_query, wildcard_query, wildcard_query))
    
    rows = cursor.fetchall()
    conn.close()

    chara_list = []

    for chara_id, name in rows:
        chara_list.append({
            'id': chara_id,
            'en_name': name
        })
    
    return chara_list


def get_shows_like(search_query):
    conn, cursor = get_connection()
    wildcard_query = f"%{search_query}%"
    cursor.execute("""SELECT id, jp_title, is_manga FROM show WHERE jp_title LIKE ? or en_title LIKE ? LIMIT 25""",
                   (wildcard_query, wildcard_query))
    rows = cursor.fetchall()
    conn.close()
    shows_list = []
    for row in rows:
        shows_list.append({
            "id": row[0],
            "jp_title": row[1],
            "is_manga": row[2]
        })
    return shows_list


def get_show_title_jp(show_id):
    conn, cursor = get_connection()
    cursor.execute("""SELECT jp_title FROM show WHERE id = ?""", (show_id,))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return None
    if rows:
        return rows[0][0]


def get_characters_from_show(show_id):
    conn, cursor = get_connection()
    cursor.execute("""SELECT s.char_id, s.en_name, COUNT(s.char_id) FROM images i
INNER JOIN (
    SELECT sc.char_id, c.en_name FROM show_character sc
    LEFT JOIN character c ON sc.char_id = c.id
    WHERE sc.show_id = ?
    ) s ON s.char_id = i.character_id
GROUP BY s.char_id
ORDER BY s.en_name;""", (show_id,))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return None
    else:
        char_list = []
        for row in rows:
            char_list.append({
                "id": row[0],
                "en_name": row[1],
                "image_count": row[2]
            })
        return char_list


def get_history(guild_id):
    conn, cursor = get_connection()

    cursor.execute("""SELECT history FROM guild WHERE id = ?""", (guild_id,))
    rows = cursor.fetchall()

    conn.close()

    if not rows or not rows[0][0]:
        return None
    else:
        return [int(hist_element) for hist_element in rows[0][0].split(";")]


def update_history(guild_id, history, waifu_data):
    if not history:
        history = list()
    else:
        if len(history) > constants.HISTORY_SIZE:
            history = history[-constants.HISTORY_SIZE:]
        history.pop(0)
    history.append(waifu_data["id"])
    history_joined = ";".join([str(hist_element) for hist_element in history])
    conn, cursor = get_connection()
    cursor.execute("""UPDATE guild SET history = ? WHERE id = ?""", (history_joined, guild_id))

    conn.commit()
    conn.close()


def generate_rarity(price=None):
    max_number = 1.0

    if price and price >= 100:
        if price > 15000:
            price = 15000

        if price > 5000:
            # Slope from 0.015 to 0.005 at 15000
            max_number = (0.005 - 0.015) / (15000 - 5000) * price + 0.02
        elif price > 1000:
            # Slope from 0.075 to 0.015
            max_number = (0.015 - 0.075) / (5000 - 1000) * price + 0.09
        elif price > 300:
            # Slope from 0.25 to 0.075
            max_number = (0.075 - 0.25) / (1000 - 300) * price + 0.325
        else:
            # Slope from 0.75 to 0.25
            max_number = (0.25 - 0.75) / (300 - 100) * price + 1

    random_number = random.uniform(0.0, max_number)

    if random_number < 0.001:
        rarity = 5
    elif random_number < 0.005:
        rarity = 4
    elif random_number < 0.015:
        rarity = 3
    elif random_number < 0.075:
        rarity = 2
    elif random_number < 0.25:
        rarity = 1
    else:
        rarity = 0

    return rarity, price


def generate_rarities_for_unset_waifus():
    conn, cursor = get_connection()
    cursor.execute("""SELECT id FROM waifus WHERE rarity = -1""")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return
    conn, cursor = get_connection()
    for row in rows:
        waifu_id = row[0]
        rarity, price = generate_rarity()
        cursor.execute("""UPDATE waifus SET rarity = ? WHERE id = ?""", (rarity, waifu_id))
    conn.commit()
    conn.close()
    return


def trade(user1_id, user2_id, user1_offer, user2_offer):
    conn, cursor = get_connection()

    # First, check if users have enough currency.
    # Then, remove/add currency
    if user1_offer.money > 0:
        cursor.execute("""SELECT currency FROM user WHERE id = ?;""", (user1_id,))
        row = cursor.fetchone()
        if row[0] < user1_offer.money or not subtract_user_currency(user1_id, user1_offer.money, (conn, cursor)):
            conn.close()
            return False
        add_user_currency(user2_id, user1_offer.money, (conn, cursor))

    if user2_offer.money > 0:
        cursor.execute("""SELECT currency FROM user WHERE id = ?;""", (user2_id,))
        row = cursor.fetchone()
        if row[0] < user2_offer.money or not subtract_user_currency(user2_id, user2_offer.money, (conn, cursor)):
            conn.close()
            return False
        add_user_currency(user1_id, user2_offer.money, (conn, cursor))

    # Start by deleting existing waifus, ensuring they exist. Then insert waifu for other user.
    for waifu in user1_offer.waifus:
        cursor.execute("""SELECT id FROM waifus WHERE id = ? AND user_id = ?""", (waifu.waifu_id, user1_id))
        rows = cursor.fetchall()
        if not rows:
            conn.close()
            return False
        else:
            cursor.execute("""DELETE FROM waifus WHERE id = ?""", (waifu.waifu_id,))
            add_waifu(user2_id, waifu.image_id, waifu.rarity, connection=(conn, cursor))

    for waifu in user2_offer.waifus:
        cursor.execute("""SELECT id FROM waifus WHERE id = ? AND user_id = ?""", (waifu.waifu_id, user2_id))
        rows = cursor.fetchall()
        if not rows:
            conn.close()
            return False
        else:
            cursor.execute("""DELETE FROM waifus WHERE id = ?""", (waifu.waifu_id,))
            add_waifu(user1_id, waifu.image_id, waifu.rarity, connection=(conn, cursor))

    conn.commit()
    conn.close()
    return True


def remove_useless_waifus():
    conn, cursor = get_connection()

    cursor.execute("""UPDATE character SET droppable = 0 WHERE en_name LIKE '%father%'""")
    cursor.execute("""UPDATE character SET droppable = 0 WHERE en_name LIKE '%grandfather%'""")
    cursor.execute("""UPDATE character SET droppable = 0 WHERE en_name LIKE '%grandpa%'""")
    cursor.execute("""UPDATE character SET droppable = 0 WHERE en_name LIKE '%mother%'""")
    cursor.execute("""UPDATE character SET droppable = 0 WHERE en_name LIKE '%grandmother%'""")
    cursor.execute("""UPDATE character SET droppable = 0 WHERE en_name LIKE '%grandma%'""")
    cursor.execute("""UPDATE character SET droppable = 0 WHERE en_name LIKE '%teacher%'""")

    conn.commit()
    conn.close()


def remove_waifu(waifus_id):
    if not waifu_exists(waifus_id):
        return False

    conn, cursor = get_connection()

    cursor.execute("""DELETE FROM waifus WHERE id = ?;""", (waifus_id,))

    conn.commit()
    conn.close()

    return True


def get_user_currency(user_id):
    ensure_user_exists(user_id)
    conn, cursor = get_connection()

    cursor.execute("""SELECT currency FROM user WHERE id = ?;""", (user_id,))
    row = cursor.fetchone()

    conn.commit()
    conn.close()

    return row[0]


def add_user_currency(user_id, amount, connection=None):
    ensure_user_exists(user_id, connection)
    if connection:
        conn, cursor = connection
    else:
        conn, cursor = get_connection()
    cursor.execute("""UPDATE user SET currency = currency + ? WHERE id = ?;""", (amount, user_id))
    conn.commit()
    if not connection:
        conn.close()
    logger.info(f"Added {amount} currency to {user_id}")
    return


def subtract_user_currency(user_id, amount, connection=None):
    ensure_user_exists(user_id, connection)
    if connection:
        conn, cursor = connection
    else:
        conn, cursor = get_connection()
    cursor.execute("""SELECT currency FROM user WHERE id = ?;""", (user_id,))
    row = cursor.fetchone()
    if row[0] < amount:
        if not connection:
            conn.close()
        return False
    cursor.execute("""UPDATE user SET currency = currency - ? WHERE id = ?;""", (amount, user_id))
    conn.commit()
    if not connection:
        conn.close()
    logger.info(f"Subtracted {amount} currency from {user_id}")
    return True


def get_rarity_currency(rarity):
    exchange_rates = {
        0: 100/4,
        1: 300/4,
        2: 1000/4,
        3: 5000/4,
        4: 15000/4,
        5: 75000/4
    }
    return round(exchange_rates[rarity])


def add_daily_currency(user_id):
    ensure_user_exists(user_id)
    add_user_currency(user_id, DAILY_CURRENCY)
    conn, cursor = get_connection()
    cursor.execute("""UPDATE user SET last_daily = ? WHERE id = ?;""", (datetime.datetime.now(), user_id))
    conn.commit()
    conn.close()


def get_user_upgrades(user_id):
    ensure_user_exists(user_id)
    conn, cursor = get_connection()

    cursor.execute("""SELECT upgrades FROM user WHERE id = ?;""", (user_id,))
    row = cursor.fetchone()

    conn.commit()
    conn.close()

    return row[0]


def add_user_upgrades(user_id, amount, connection=None):
    ensure_user_exists(user_id, connection)
    if connection:
        conn, cursor = connection
    else:
        conn, cursor = get_connection()
    cursor.execute("""UPDATE user SET upgrades = upgrades + ? WHERE id = ?;""", (amount, user_id))
    conn.commit()
    if not connection:
        conn.close()
    logger.info(f"Added {amount} upgrades to {user_id}")
    return


def subtract_user_upgrades(user_id, amount, connection=None):
    ensure_user_exists(user_id, connection)
    if connection:
        conn, cursor = connection
    else:
        conn, cursor = get_connection()
    cursor.execute("""SELECT upgrades FROM user WHERE id = ?;""", (user_id,))
    row = cursor.fetchone()
    if row[0] < amount:
        if not connection:
            conn.close()
        return False
    cursor.execute("""UPDATE user SET upgrades = upgrades - ? WHERE id = ?;""", (amount, user_id))
    conn.commit()
    if not connection:
        conn.close()
    logger.info(f"Subtracted {amount} upgrades from {user_id}")
    return True


def set_favorite(waifus_id):
    conn, cursor = get_connection()

    cursor.execute("""UPDATE waifus SET favorite = 1 WHERE id = ?""", (waifus_id,))

    conn.commit()
    conn.close()


def unfavorite(waifus_id):
    conn, cursor = get_connection()

    cursor.execute("""UPDATE waifus SET favorite = 0 WHERE id = ?""", (waifus_id,))

    conn.commit()
    conn.close()


def get_shows_from_character(char_id, connection=None):
    if connection:
        conn, cursor = connection
    else:
        conn, cursor = get_connection()

    show_list = []

    cursor.execute("""SELECT DISTINCT show_id FROM show_character WHERE char_id = ?""", (char_id,))
    rows = cursor.fetchall()
    for row in rows:
        show_list.append(int(row[0]))

    if not connection:
        conn.close()

    return show_list


def get_waifusAmount(user_id):

    conn, cursor = get_connection()

    cursor.execute("""SELECT COUNT(*) FROM waifus WHERE user_id = ?;""", (user_id,))
    rows = cursor.fetchall()

    conn.close()

    return rows[0][0]


def get_character_info(char_id):
    if not character_exists(char_id):
        return None
    conn, cursor = get_connection()

    cursor.execute("""SELECT en_name, jp_name FROM character WHERE id = ?;""", (char_id,))
    row = cursor.fetchone()
    en_name = row[0]
    jp_name = row[1]

    cursor.execute("""SELECT normal_url FROM images WHERE character_id = ?;""", (char_id,))
    rows = cursor.fetchall()
    image_urls = []
    for row in rows:
        image_urls.append(row[0])

    cursor.execute("""SELECT rarity, favorite FROM waifus w INNER JOIN (SELECT id FROM images WHERE character_id = ?) i ON i.id = w.images_id;""", (char_id,))
    rows = cursor.fetchall()
    waifu_count = len(rows)
    rarity_count = {}
    favs_count = 0
    for row in rows:
        cur_rarity = row[0]
        cur_fav = row[1]
        if cur_fav == 1:
            favs_count += 1
        if cur_rarity not in rarity_count:
            rarity_count[cur_rarity] = 1
        else:
            rarity_count[cur_rarity] += 1

    conn.close()

    return {
        "id": char_id,
        "en_name": en_name,
        "jp_name": jp_name,
        "waifu_count": waifu_count,
        "rarity_count": rarity_count,
        "image_urls": image_urls,
        "favorites": favs_count
    }


def user_can_daily(user_id):
    ensure_user_exists(user_id)
    conn, cursor = get_connection()

    date_format = "%d-%m-%Y %H:%M:%S"
    cursor.execute("""SELECT STRFTIME(?, last_daily) FROM user WHERE id = ?;""", (date_format, user_id))
    row = cursor.fetchone()
    conn.close()
    last_datetime = datetime.datetime.strptime(row[0], date_format)
    if last_datetime.date() < datetime.datetime.today().date():
        return True
    return False


def upgrade_user_waifu(user_id, waifus_id, amount):
    ensure_user_exists(user_id)
    conn, cursor = get_connection()

    # Remove upgrades
    if not subtract_user_upgrades(user_id, amount, (conn, cursor)):
        conn.close()
        return False

    # Upgrade waifu
    cursor.execute("""UPDATE waifus SET rarity = rarity + 1 WHERE id = ?;""", (waifus_id,))

    conn.commit()
    conn.close()
    return True

async def update_images():
    conn, cursor = get_connection()
    cursor.execute("""SELECT id, mal_url, character_id FROM images WHERE normal_url IS NULL;""")
    rows = cursor.fetchall()
    for row in rows:
        cur_id = row[0]
        logger.info(f"Updating image {cur_id}, character: {row[2]}")
        mal_url = row[1]
        images_obj = await mal_tools.CharacterImage.create(mal_url)
        if images_obj:
            cursor.execute("""UPDATE images SET normal_url = ?, mirror_url = ?, flipped_url = ? WHERE id = ?;""", (images_obj.normal_url, images_obj.mirror_url, images_obj.upside_down_url, cur_id))
            conn.commit()
        await asyncio.sleep(20)

    conn.commit()
    conn.close()

def get_all_show_mal_urls():
    url_list = list()

    conn, cursor = get_connection()
    cursor.execute("""SELECT mal_id, is_manga FROM show;""")
    rows = cursor.fetchall()
    for row in rows:
        mal_id = row[0]
        is_manga = row[1]
        url_list.append(mal_tools.show_url_from_id(mal_id, is_manga))
    conn.close()

    return url_list

def get_character_image_urls(char_id):
    image_urls = list()
    conn, cursor = get_connection()
    cursor.execute("""SELECT DISTINCT mal_url FROM images WHERE character_id = ?;""", (char_id,))
    rows = cursor.fetchall()
    for row in rows:
        image_urls.append(row[0])
    conn.close()
    return image_urls

# def change_name(char_id, en_name):
#
