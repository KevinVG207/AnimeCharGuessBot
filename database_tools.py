import random
import sqlite3
import name_tools as nt
from numpy import random as numpyrand

DATABASE_URI = "database/database.db"

DAILY_CURRENCY = 500

def getConnection():
    conn = sqlite3.connect(DATABASE_URI)
    return conn, conn.cursor()


def createDatabase():
    print("Setting up DB.")
    conn, cursor = getConnection()

    create_script = open("database/create.sql")
    sql_as_string = create_script.read()
    cursor.executescript(sql_as_string)
    create_script.close()

    conn.close()
    print("Finished setting up DB")


def bulkInsertCharacter(character_data_list):
    for character_data in character_data_list:
        insertCharacter(character_data)


def insertCharacter(char_data, alt_name=None):
    char_id = char_data["char_id"]
    en_name = char_data["en_name"]
    jp_name = char_data["jp_name"]
    image_urls = char_data["image_urls"]

    if characterExists(char_id):
        print(f"Character {char_id} {en_name} already exists in the database.")
        return

    if not image_urls:
        print(f"Character {char_id} {en_name} does not have any images. Skipping.")
        return

    print(f"Inserting character {char_id} {en_name}")
    conn, cursor = getConnection()

    cursor.execute("""INSERT INTO character (id, en_name, jp_name, alt_name) VALUES (?,?,?,?);""",
                   (char_id, en_name, jp_name, alt_name))

    for image_url in image_urls:
        cursor.execute("""INSERT INTO images (url, character_id) VALUES (?,?);""", (image_url, char_id))

    conn.commit()
    conn.close()


def guildExists(guild_id):
    conn, cursor = getConnection()
    cursor.execute("""SELECT id FROM guild WHERE id = ?;""", (guild_id,))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        # Guild does not exist
        return False
    else:
        # Guild does exist
        return True


def characterExists(char_id):
    conn, cursor = getConnection()
    cursor.execute("""SELECT id FROM character WHERE id = ?;""", (char_id,))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return False
    else:
        return True


def showExistsByMAL(mal_id, is_manga):
    conn, cursor = getConnection()
    cursor.execute("""SELECT id FROM show WHERE mal_id = ? AND is_manga = ?;""", (mal_id, is_manga))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return False
    else:
        return True


def showExists(show_id):
    conn, cursor = getConnection()
    cursor.execute("""SELECT id FROM show WHERE id = ?;""", (show_id,))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return False
    else:
        return True


def waifuExists(waifus_id, connection=None):
    if not connection:
        conn, cursor = getConnection()
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


def assignChannelToGuild(channel_id, guild_id):
    conn, cursor = getConnection()
    if guildExists(guild_id):
        # Guild already exists, update channel.
        cursor.execute("""UPDATE guild SET channel_id = ? WHERE id = ?;""", (channel_id, guild_id))
    else:
        # Guild does not exist, insert it.
        cursor.execute("""INSERT INTO guild (id, channel_id) VALUES (?,?);""", (guild_id, channel_id))
    conn.commit()
    conn.close()


def getAssignedChannelID(guild_id):
    channel_id = None

    conn, cursor = getConnection()
    cursor.execute("""SELECT channel_id FROM guild WHERE id = ?;""", (guild_id,))
    rows = cursor.fetchall()
    conn.close()
    if rows and rows[0]:
        channel_id = rows[0][0]

    return channel_id


def canDrop(guild_id):
    conn, cursor = getConnection()
    cursor.execute("""SELECT can_drop FROM guild WHERE id = ? AND can_drop = 1;""", (guild_id,))
    rows = cursor.fetchall()
    conn.close()
    if rows:
        return True
    else:
        return False


def canTrade(user_id):
    conn, cursor = getConnection()
    cursor.execute("""SELECT can_trade FROM user WHERE id = ? AND can_trade = 1;""", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    if rows:
        return True
    else:
        return False


def canRemove(user_id):
    conn, cursor = getConnection()
    cursor.execute("""SELECT can_remove FROM user WHERE id = ? AND can_trade = 1;""", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    if rows:
        return True
    else:
        return False


def getDropData(history=None, price=None, user_id=None):
    conn, cursor = getConnection()
    if history:
        cursor.execute(
            f"""SELECT DISTINCT id FROM character WHERE droppable = 1 AND id NOT IN ({",".join(["?" for _ in history])});""",
            tuple(history))
    else:
        cursor.execute("""SELECT DISTINCT id FROM character WHERE droppable = 1;""")
    rows = cursor.fetchall()
    # true_rows = []

    # if history:
    #     for row in rows:
    #         if int(row[0]) not in history:
    #             true_rows.append(row)
    #         else:
    #             print(row[0])
    # else:
    #     true_rows = rows

    # Doing this for Jack's paranoia.
    # random.seed()
    # random_number = random.randint(0, len(rows))
    # random.shuffle(true_rows)
    random_number = numpyrand.randint(0, len(rows))
    char_id = rows[random_number][0]
    cursor.execute("""SELECT url, en_name, alt_name, images.id FROM character
    LEFT JOIN images ON character.id = images.character_id
    WHERE images.droppable = 1 AND character.id = ?;""", (char_id,))
    rows2 = cursor.fetchall()

    conn.close()

    random.shuffle(rows2)
    image_url = rows2[0][0]
    en_name = rows2[0][1]
    alt_name = rows2[0][2]
    image_id = rows2[0][3]
    rarity, price = generateRarity(price)

    cur_waifu = {"char_id": char_id,
                 "image_url": image_url,
                 "en_name": en_name,
                 "alt_name": alt_name,
                 "image_id": image_id,
                 "rarity": rarity}

    if price and user_id:
        # We are rolling.
        # Deduct price

        subtractUserCurrency(user_id, price)

        return cur_waifu, price

    return cur_waifu


def disableDrops(guild_id):
    conn, cursor = getConnection()
    cursor.execute("""UPDATE guild SET can_drop = 0 WHERE id = ?;""", (guild_id,))
    conn.commit()
    conn.close()


def enableDrops(guild_id):
    conn, cursor = getConnection()
    cursor.execute("""UPDATE guild SET can_drop = 1 WHERE id = ?;""", (guild_id,))
    conn.commit()
    conn.close()


def enableTrade(user_id):
    conn, cursor = getConnection()
    cursor.execute("""UPDATE user SET can_trade = 1 WHERE id = ?;""", (user_id,))
    conn.commit()
    conn.close()


def disableTrade(user_id):
    conn, cursor = getConnection()
    cursor.execute("""UPDATE user SET can_trade = 0 WHERE id = ?;""", (user_id,))
    conn.commit()
    conn.close()


def enableRemove(user_id):
    conn, cursor = getConnection()
    cursor.execute("""UPDATE user SET can_remove = 1 WHERE id = ?;""", (user_id,))
    conn.commit()
    conn.close()


def disableRemove(user_id):
    conn, cursor = getConnection()
    cursor.execute("""UPDATE user SET can_remove = 0 WHERE id = ?;""", (user_id,))
    conn.commit()
    conn.close()


def enableAllDrops():
    conn, cursor = getConnection()
    cursor.execute("""UPDATE guild SET can_drop = 1;""")
    conn.commit()
    conn.close()


def enableAllTrades():
    conn, cursor = getConnection()
    cursor.execute("""UPDATE user SET can_trade = 1;""")
    conn.commit()
    conn.close()


def enableAllRemoves():
    conn, cursor = getConnection()
    cursor.execute("""UPDATE user SET can_remove = 1;""")
    conn.commit()
    conn.close()


def ensureUserExists(user_id):
    conn, cursor = getConnection()
    cursor.execute("""SELECT id FROM user WHERE id = ?;""", (user_id,))
    rows = cursor.fetchall()
    if not rows:
        # User does not exist
        cursor.execute("""INSERT INTO user (id) VALUES (?);""", (user_id,))
        conn.commit()
    conn.close()


def addWaifu(user_id, image_id, rarity, connection=None):
    ensureUserExists(user_id)
    if not connection:
        conn, cursor = getConnection()
    else:
        conn, cursor = connection
    cursor.execute("""INSERT INTO waifus (user_id, images_id, rarity) VALUES (?,?,?);""", (user_id, image_id, rarity))

    if not connection:
        conn.commit()
        conn.close()


def divideWaifus(waifus_list, chunk_size):
    # looping till length l
    for i in range(0, len(waifus_list), chunk_size):
        yield waifus_list[i:i + chunk_size]


def getWaifus(user_id, rarity=None, name_query=None, show_id=None, page_size=25, unpaginated=False, inventory_index=None):
    ensureUserExists(user_id)
    conn, cursor = getConnection()

    if show_id:
        cursor.execute("""SELECT en_name, s.image_index, rarity, s.char_id, images_id, waifus.id, s.url, waifus.favorite, sc.show_id
FROM waifus
LEFT JOIN (SELECT w.id as id, w.character_id as char_id, c.en_name as en_name, w.row_num as image_index, w.url as url
FROM character c
LEFT JOIN (SELECT id, character_id, url, ROW_NUMBER() OVER (PARTITION BY character_id ORDER BY id) AS row_num FROM images) w
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
LEFT JOIN (SELECT w.id as id, w.character_id as char_id, c.en_name as en_name, w.row_num as image_index, w.url as url
FROM character c
LEFT JOIN (SELECT id, character_id, url, ROW_NUMBER() OVER (PARTITION BY character_id ORDER BY id) AS row_num FROM images) w
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
                     "images_id": row[4],
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
            final_pages = list(divideWaifus(waifus, page_size))

    return final_pages


def removeGuild(guild_id):
    conn, cursor = getConnection()
    cursor.execute("""DELETE FROM guild WHERE id = ?;""", (guild_id,))
    conn.commit()
    conn.close()


def getWaifuCount(user_id):
    ensureUserExists(user_id)
    conn, cursor = getConnection()
    cursor.execute("""SELECT COUNT() FROM waifus WHERE user_id = ? ORDER BY id;""", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return 0
    else:
        return rows[0][0]


def getWaifuImageIndex(waifu_id):
    conn, cursor = getConnection()
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


def getWaifuOfUser(user_id, skip):
    ensureUserExists(user_id)
    conn, cursor = getConnection()
    cursor.execute("""SELECT en_name, jp_name, character_id, url, waifus.id, rarity
FROM waifus
LEFT JOIN images i ON waifus.images_id = i.id
LEFT JOIN character c ON i.character_id = c.id
WHERE user_id = ?
LIMIT ?, 1;""", (user_id, skip))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return None
    return {"en_name": rows[0][0],
            "jp_name": rows[0][1],
            "id": rows[0][2],
            "image_url": rows[0][3],
            "image_index": getWaifuImageIndex(rows[0][4]),
            "rarity": rows[0][5]}


def insertShow(mal_id, jp_title, en_title, is_manga):
    conn, cursor = getConnection()
    print(f"Inserting show {mal_id} {en_title}, is_manga: {is_manga}")

    cursor.execute("""INSERT INTO show (mal_id, jp_title, en_title, is_manga) VALUES (?,?,?,?)""",
                   (mal_id, jp_title, en_title, is_manga))

    conn.commit()
    conn.close()


def getShowIDByMAL(mal_id, is_manga):
    conn, cursor = getConnection()
    cursor.execute("""SELECT id FROM show WHERE mal_id = ? AND is_manga = ?;""", (mal_id, is_manga))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return None
    else:
        return rows[0][0]


def characterHasShow(char_id, show_id):
    conn, cursor = getConnection()
    cursor.execute("""SELECT id FROM show_character WHERE char_id = ? AND show_id = ?;""", (char_id, show_id))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return False
    else:
        return True


def addShowToCharacter(char_id, show_id):
    conn, cursor = getConnection()
    print(f"Adding show {show_id} to character {char_id}")
    cursor.execute("""INSERT INTO show_character (char_id, show_id) VALUES (?,?);""", (char_id, show_id))
    conn.commit()
    conn.close()


def getCharactersWithoutShows():
    conn, cursor = getConnection()
    cursor.execute("""select * from character
left join show_character sc on character.id = sc.char_id
where sc.id is null;""")
    rows = cursor.fetchall()
    conn.close()
    return rows


def getShowsLike(search_query):
    conn, cursor = getConnection()
    wildcard_query = f"%{search_query}%"
    cursor.execute("""SELECT id, jp_title, is_manga FROM show WHERE jp_title LIKE ? or en_title LIKE ? LIMIT 25""",
                   (wildcard_query, wildcard_query))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return None
    else:
        shows_list = []
        for row in rows:
            shows_list.append({
                "id": row[0],
                "jp_title": row[1],
                "is_manga": row[2]
            })
        return shows_list


def getShowTitleJP(show_id):
    conn, cursor = getConnection()
    cursor.execute("""SELECT jp_title FROM show WHERE id = ?""", (show_id,))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return None
    if rows:
        return rows[0][0]


def getCharactersFromShow(show_id):
    conn, cursor = getConnection()
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
                "char_id": row[0],
                "en_name": row[1],
                "image_count": row[2]
            })
        return char_list


def getHistory(guild_id):
    conn, cursor = getConnection()

    cursor.execute("""SELECT history FROM guild WHERE id = ?""", (guild_id,))
    rows = cursor.fetchall()

    conn.close()

    if not rows or not rows[0][0]:
        return None
    else:
        return [int(hist_element) for hist_element in rows[0][0].split(";")]


def updateHistory(guild_id, history):
    history_joined = ";".join([str(hist_element) for hist_element in history])
    conn, cursor = getConnection()
    cursor.execute("""UPDATE guild SET history = ? WHERE id = ?""", (history_joined, guild_id))

    conn.commit()
    conn.close()


def generateRarity(price=None):
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

    random_number = numpyrand.uniform(0.0, max_number)

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


def generateRaritiesForUnsetWaifus():
    conn, cursor = getConnection()
    cursor.execute("""SELECT id FROM waifus WHERE rarity = -1""")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return
    conn, cursor = getConnection()
    for row in rows:
        waifu_id = row[0]
        rarity, price = generateRarity()
        cursor.execute("""UPDATE waifus SET rarity = ? WHERE id = ?""", (rarity, waifu_id))
    conn.commit()
    conn.close()
    return


def trade(user1_id, user2_id, user1_offer, user2_offer):
    conn, cursor = getConnection()

    # Start by deleting existing waifus, ensuring they exist. Then insert waifu for other user.
    for waifu in user1_offer:
        cursor.execute("""SELECT id FROM waifus WHERE id = ? AND user_id = ?""", (waifu["waifus_id"], user1_id))
        rows = cursor.fetchall()
        if not rows:
            conn.close()
            return False
        else:
            cursor.execute("""DELETE FROM waifus WHERE id = ?""", (waifu["waifus_id"],))
            addWaifu(user2_id, waifu["images_id"], waifu["rarity"], connection=(conn, cursor))

    for waifu in user2_offer:
        cursor.execute("""SELECT id FROM waifus WHERE id = ? AND user_id = ?""", (waifu["waifus_id"], user2_id))
        rows = cursor.fetchall()
        if not rows:
            conn.close()
            return False
        else:
            cursor.execute("""DELETE FROM waifus WHERE id = ?""", (waifu["waifus_id"],))
            addWaifu(user1_id, waifu["images_id"], waifu["rarity"], connection=(conn, cursor))

    conn.commit()
    conn.close()
    return True


def removeUselessWaifus():
    conn, cursor = getConnection()

    cursor.execute("""UPDATE character SET droppable = 0 WHERE en_name LIKE '%father%'""")
    cursor.execute("""UPDATE character SET droppable = 0 WHERE en_name LIKE '%grandfather%'""")
    cursor.execute("""UPDATE character SET droppable = 0 WHERE en_name LIKE '%grandpa%'""")
    cursor.execute("""UPDATE character SET droppable = 0 WHERE en_name LIKE '%mother%'""")
    cursor.execute("""UPDATE character SET droppable = 0 WHERE en_name LIKE '%grandmother%'""")
    cursor.execute("""UPDATE character SET droppable = 0 WHERE en_name LIKE '%grandma%'""")
    cursor.execute("""UPDATE character SET droppable = 0 WHERE en_name LIKE '%teacher%'""")

    conn.commit()
    conn.close()


def removeWaifu(waifus_id):
    if not waifuExists(waifus_id):
        return False

    conn, cursor = getConnection()

    cursor.execute("""DELETE FROM waifus WHERE id = ?;""", (waifus_id,))

    conn.commit()
    conn.close()

    return True


def getUserCurrency(user_id):
    ensureUserExists(user_id)
    conn, cursor = getConnection()

    cursor.execute("""SELECT currency FROM user WHERE id = ?;""", (user_id,))
    rows = cursor.fetchall()

    conn.commit()
    conn.close()

    return rows[0][0]


def addUserCurrency(user_id, amount):
    conn, cursor = getConnection()
    cursor.execute("""UPDATE user SET currency = currency + ? WHERE id = ?;""", (amount, user_id))
    conn.commit()
    conn.close()
    print(f"Added {amount} to {user_id}")
    return


def subtractUserCurrency(user_id, amount):
    conn, cursor = getConnection()
    cursor.execute("""UPDATE user SET currency = currency - ? WHERE id = ?;""", (amount, user_id))
    print(f"Subtracted {amount} from {user_id}")
    conn.commit()
    conn.close()
    return


def getRarityCurrency(rarity):
    exchange_rates = {
        0: 100/4,
        1: 300/4,
        2: 1000/4,
        3: 5000/4,
        4: 15000/4,
        5: 75000/4
    }
    return round(exchange_rates[rarity])


def addDailyCurrency():
    conn, cursor = getConnection()

    cursor.execute("""SELECT id FROM user;""")
    rows = cursor.fetchall()
    conn.close()
    for row in rows:
        addUserCurrency(row[0], DAILY_CURRENCY)


def setFavorite(waifus_id):
    conn, cursor = getConnection()

    cursor.execute("""UPDATE waifus SET favorite = 1 WHERE id = ?""", (waifus_id,))

    conn.commit()
    conn.close()


def unFavorite(waifus_id):
    conn, cursor = getConnection()

    cursor.execute("""UPDATE waifus SET favorite = 0 WHERE id = ?""", (waifus_id,))

    conn.commit()
    conn.close()


def getShowsFromCharacter(char_id, connection=None):
    if connection:
        conn, cursor = connection
    else:
        conn, cursor = getConnection()

    show_list = []

    cursor.execute("""SELECT DISTINCT show_id FROM show_character WHERE char_id = ?""", (char_id,))
    rows = cursor.fetchall()
    for row in rows:
        show_list.append(int(row[0]))

    if not connection:
        conn.close()

    return show_list
