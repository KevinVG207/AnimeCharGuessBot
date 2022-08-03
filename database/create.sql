-- Created by Vertabelo (http://vertabelo.com)
-- Last modification date: 2022-08-03 16:38:08.253

-- tables
-- Table: character
CREATE TABLE character (
    id integer NOT NULL CONSTRAINT id PRIMARY KEY,
    en_name text NOT NULL,
    jp_name text,
    alt_name text,
    droppable boolean NOT NULL DEFAULT 1
);

-- Table: guild
CREATE TABLE guild (
    id integer NOT NULL CONSTRAINT guild_pk PRIMARY KEY,
    channel_id integer,
    can_drop boolean NOT NULL DEFAULT 1,
    history text
);

-- Table: images
CREATE TABLE images (
    id integer NOT NULL CONSTRAINT images_pk PRIMARY KEY AUTOINCREMENT,
    mal_url text NOT NULL,
    character_id integer NOT NULL,
    droppable boolean NOT NULL DEFAULT 1,
    normal_url text NOT NULL,
    mirror_url text NOT NULL,
    flipped_url text NOT NULL,
    CONSTRAINT images_character FOREIGN KEY (character_id)
    REFERENCES character (id)
    ON DELETE CASCADE
);

-- Table: show
CREATE TABLE show (
    id integer NOT NULL CONSTRAINT show_pk PRIMARY KEY AUTOINCREMENT,
    mal_id integer NOT NULL,
    is_manga boolean NOT NULL DEFAULT 0,
    jp_title text NOT NULL,
    en_title text,
    mal_url integer
);

-- Table: show_character
CREATE TABLE show_character (
    id integer NOT NULL CONSTRAINT show_character_pk PRIMARY KEY AUTOINCREMENT,
    show_id integer NOT NULL,
    char_id integer NOT NULL,
    CONSTRAINT show_character_show FOREIGN KEY (show_id)
    REFERENCES show (id),
    CONSTRAINT show_character_character FOREIGN KEY (char_id)
    REFERENCES character (id)
);

-- Table: user
CREATE TABLE user (
    id integer NOT NULL CONSTRAINT user_pk PRIMARY KEY,
    currency integer NOT NULL DEFAULT 500,
    upgrades integer NOT NULL DEFAULT 0,
    can_trade boolean NOT NULL DEFAULT 1,
    can_remove boolean NOT NULL DEFAULT 1,
    can_quest boolean NOT NULL DEFAULT 1,
    quest_stamina integer NOT NULL DEFAULT 5,
    last_stamina_use datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_daily datetime NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Table: waifus
CREATE TABLE waifus (
    id integer NOT NULL CONSTRAINT waifus_pk PRIMARY KEY AUTOINCREMENT,
    images_id integer NOT NULL,
    user_id integer NOT NULL,
    rarity integer NOT NULL DEFAULT -1,
    favorite boolean NOT NULL DEFAULT 0,
    CONSTRAINT user_img_images FOREIGN KEY (images_id)
    REFERENCES images (id)
    ON DELETE CASCADE,
    CONSTRAINT user_img_user FOREIGN KEY (user_id)
    REFERENCES user (id)
);

-- End of file.

