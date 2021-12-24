import sqlite3

DATABASE_URI = "database/database.db"


def getConnection():
    conn = sqlite3.connect(DATABASE_URI)
    return conn, conn.cursor()


def createDatabase():
    print("Setting up DB.")
    conn, cursor = getConnection()

    cursor.execute("""CREATE TABLE character (
    id integer NOT NULL CONSTRAINT id PRIMARY KEY,
    en_name text NOT NULL,
    jp_name text
    );""")

    cursor.execute("""CREATE TABLE images (
    id integer NOT NULL CONSTRAINT images_pk PRIMARY KEY AUTOINCREMENT,
    url text NOT NULL,
    character_id integer NOT NULL,
    CONSTRAINT images_character FOREIGN KEY (character_id)
    REFERENCES character (id)
    );""")

    cursor.execute("""CREATE TABLE guild (
    id integer NOT NULL CONSTRAINT guild_pk PRIMARY KEY,
    channel_id integer,
    can_drop boolean NOT NULL DEFAULT 1
    );""")

    conn.close()
    print("Finished setting up DB")


def insertCharacter(char_data):
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
