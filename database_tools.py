import random
import sqlite3
import name_tools as nt


DATABASE_URI = "database/database.db"


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

    cursor.execute("""INSERT INTO character (id, en_name, jp_name, alt_name) VALUES (?,?,?,?);""", (char_id, en_name, jp_name, alt_name))

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


def getDropData(history=None):
    conn, cursor = getConnection()
    if history:
        cursor.execute(f"""SELECT DISTINCT id FROM character WHERE droppable = 1 AND id NOT IN ({",".join(["?" for _ in history])});""", tuple(history))
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
    random.seed()
    random_number = random.randint(0, len(rows))
    # random.shuffle(true_rows)
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
    rarity = generateRarity()
    return {"char_id": char_id,
            "image_url": image_url,
            "en_name": en_name,
            "alt_name": alt_name,
            "image_id": image_id,
            "rarity": rarity}


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


def enableAllDrops():
    conn, cursor = getConnection()
    cursor.execute("""UPDATE guild SET can_drop = 1;""")
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


def saveWin(user_id, image_id, rarity):
    ensureUserExists(user_id)
    conn, cursor = getConnection()
    cursor.execute("""INSERT INTO waifus (user_id, images_id, rarity) VALUES (?,?,?);""", (user_id, image_id, rarity))
    conn.commit()
    conn.close()


def divideWaifus(waifus_list, chunk_size):
    # looping till length l
    for i in range(0, len(waifus_list), chunk_size):
        yield waifus_list[i:i + chunk_size]


def getWaifus(user_id, rarity, name_query, page_size):
    ensureUserExists(user_id)
    conn, cursor = getConnection()

    cursor.execute("""SELECT en_name, s.image_index, rarity
FROM waifus
LEFT JOIN (SELECT w.id as id, c.en_name as en_name, w.row_num as image_index
FROM character c
LEFT JOIN (SELECT id, character_id, ROW_NUMBER() OVER (PARTITION BY character_id ORDER BY id) AS row_num FROM images) w
ON w.character_id = c.id) s
ON waifus.images_id = s.id
WHERE waifus.user_id = ?
ORDER BY waifus.id;""", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    waifus = []
    final_pages = []
    index = 0

    for row in rows:
        index += 1
        if rarity and rarity >= 0:
            if row[2] != rarity:
                continue
        if name_query and nt.romanizationFix(name_query.lower()) not in nt.romanizationFix(row[0].lower()):
            continue
        waifus.append({"en_name": row[0],
                       "image_index": row[1],
                       "rarity": row[2],
                       "index": index})

    if waifus:
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

    cursor.execute("""INSERT INTO show (mal_id, jp_title, en_title, is_manga) VALUES (?,?,?,?)""", (mal_id, jp_title, en_title, is_manga))

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
    cursor.execute("""SELECT id, jp_title, is_manga FROM show WHERE jp_title LIKE ? or en_title LIKE ? LIMIT 25""", (wildcard_query, wildcard_query))
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
    # Thanks Lunarmagpie
    count, weights = zip(*enumerate((750, 250, 75, 15, 5, 1)))
    rarity = next(iter(random.choices(count, weights=weights)))
    return rarity


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
        rarity = generateRarity()
        cursor.execute("""UPDATE waifus SET rarity = ? WHERE id = ?""", (rarity, waifu_id))
    conn.commit()
    conn.close()
    return
