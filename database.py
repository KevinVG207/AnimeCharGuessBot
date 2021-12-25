import random
import sqlite3

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


def insertCharacter(char_data):
    """TODO: Replace character if it already exists."""
    char_id, en_name, jp_name, image_urls = char_data
    print(f"Inserting character {en_name}")
    conn, cursor = getConnection()

    cursor.execute("""INSERT INTO character (id, en_name, jp_name) VALUES (?,?,?)""", (char_id, en_name, jp_name))

    char_pk = cursor.lastrowid

    for image_url in image_urls:
        cursor.execute("""INSERT INTO images (url, character_id) VALUES (?,?)""", (image_url, char_pk))

    conn.commit()
    conn.close()


def guildExists(guild_id):
    conn, cursor = getConnection()
    cursor.execute("""SELECT id FROM guild WHERE id = ?""", (guild_id,))
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
    cursor.execute("""SELECT id FROM character WHERE id = ?""", (char_id,))
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
        cursor.execute("""UPDATE guild SET channel_id = ? WHERE id = ?""", (channel_id, guild_id))
    else:
        # Guild does not exist, insert it.
        cursor.execute("""INSERT INTO guild (id, channel_id) VALUES (?,?)""", (guild_id, channel_id))
    conn.commit()
    conn.close()


def getAssignedChannelID(guild_id):
    channel_id = None

    conn, cursor = getConnection()
    cursor.execute("""SELECT channel_id FROM guild WHERE id = ?""", (guild_id,))
    rows = cursor.fetchall()
    conn.close()
    if rows and rows[0]:
        channel_id = rows[0][0]

    return channel_id


def canDrop(guild_id):
    conn, cursor = getConnection()
    cursor.execute("""SELECT can_drop FROM guild WHERE id = ? AND can_drop = 1""", (guild_id,))
    rows = cursor.fetchall()
    conn.close()
    if rows:
        return True
    else:
        return False


def getDropData():
    conn, cursor = getConnection()
    cursor.execute("""SELECT id FROM character""")
    rows = cursor.fetchall()
    random.shuffle(rows)
    char_id = rows[0][0]
    cursor.execute("""SELECT url, en_name, images.id FROM character
    LEFT JOIN images ON character.id = images.character_id
    WHERE character.id = ?;""", (char_id,))
    rows = cursor.fetchall()
    conn.close()
    random.shuffle(rows)
    image_url = rows[0][0]
    en_name = rows[0][1]
    image_id = rows[0][2]
    return {"char_id": char_id,
            "image_url": image_url,
            "en_name": en_name,
            "image_id": image_id}


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


def ensureUserExists(user_id):
    conn, cursor = getConnection()
    cursor.execute("""SELECT id FROM user WHERE id = ?""", (user_id,))
    rows = cursor.fetchall()
    if not rows:
        # User does not exist
        cursor.execute("""INSERT INTO user (id) VALUES (?)""", (user_id,))
        conn.commit()
    conn.close()


def saveWin(user_id, image_id):
    ensureUserExists(user_id)
    conn, cursor = getConnection()
    cursor.execute("""INSERT INTO user_img (user_id, images_id) VALUES (?,?)""", (user_id, image_id))
    conn.commit()
    conn.close()
    print("Saved win!")


def getWaifus(user_id):
    waifus = []
    ensureUserExists(user_id)
    conn, cursor = getConnection()
    cursor.execute("""SELECT en_name, COUNT(character_id)
    FROM user_img
    LEFT JOIN images on user_img.images_id = images.id
    LEFT JOIN character c on images.character_id = c.id
    WHERE user_id = ?
    GROUP BY character_id;""", (user_id,))
    rows = cursor.fetchall()
    for row in rows:
        waifus.append({"en_name": row[0],
                       "amount": row[1]})
    conn.close()
    return waifus
