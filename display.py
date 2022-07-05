import asyncio
import datetime
import discord

import constants

RARITY_STRINGS = (
    '★☆☆☆☆',
    '★★☆☆☆',
    '★★★☆☆',
    '★★★★☆',
    '★★★★★',
    '✪✪✪✪✪'
)

def rarity_string(rarity):
    """
    Get the star value text for a rarity.
    """
    return RARITY_STRINGS[rarity]


def create_embed(title, desciption, color = constants.EMBED_COLOR, thumbnail = None, image = None, footer = None, timestamp = None):
    """
    Creates a Discord embed containing text, and optionally other properties.
    """

    if timestamp is None:
        timestamp = datetime.datetime.now()

    embed = discord.Embed(
        type = "rich",
        title = title,
        description = desciption,
        color = color,
        timestamp = timestamp
    )

    if thumbnail is not None:
        embed.set_thumbnail(url = thumbnail)

    if image is not None:
        embed.set_image(url = image)

    if footer is not None:
        embed.set_footer(text = footer)
    
    return embed


async def page(bot, args, elements, title, page_no = None, page_size = 25, timeout = 30, error_message = None):
    """
    Creates a paginated display of a list of elements. The elements will be converted into strings.
    Paging is controlled by Discord buttons, and is locked if too much time passes since the last use.
    """
    if not error_message:
        error_message = "There is nothing to show."

    if not elements:
        await args.message.reply(embed = create_embed(
            title,
            error_message
        ))
        return
    
    pages = 1 + (len(elements) - 1) // page_size

    page_no = (
        0 if page_no is None
        else page_no % pages if page_no < 1
        else min(page_no, pages) - 1
    )

    # Create the text for each page.
    page_texts = []

    for i in range(pages):
        lines = []

        for element in elements[i * page_size : (i + 1) * page_size]:
            lines.append(str(element))

        page_texts.append('\n'.join(lines))

    embed = create_embed(title + f' - Page {page_no + 1}/{pages}', page_texts[page_no])

    if pages > 1:
        # There are multiple pages.

        prev_button = discord.ui.Button(label = '⬅ Prev')
        next_button = discord.ui.Button(label = 'Next ➡')

        button_queue = asyncio.Queue()

        async def prev_cb(interaction):
            if interaction.user.id == args.user.id:
                await button_queue.put(-1)

        async def next_cb(interaction):
            if interaction.user.id == args.user.id:
                await button_queue.put(1)

        prev_button.callback = prev_cb
        next_button.callback = next_cb

        view = discord.ui.View(timeout = timeout)
        view.add_item(prev_button)
        view.add_item(next_button)

        message = await args.message.reply(embed = embed, view = view)

        try:
            while True:
                # Wait on input from buttons.
                movement = await asyncio.wait_for(button_queue.get(), timeout)

                page_no += movement
                page_no %= pages

                # Merge multiple quick presses together.
                if button_queue.empty():
                    embed = create_embed(title + f' - Page {page_no + 1}/{pages}', page_texts[page_no])

                    await message.edit(embed = embed, view = view)

        except asyncio.TimeoutError:
            # No activity for a while, so disable the buttons.
            prev_button.callback = next_button.callback = None
            prev_button.disabled = next_button.disabled = True

            view = discord.ui.View()
            view.add_item(prev_button)
            view.add_item(next_button)

            await message.edit(embed = embed, view = view)
    
    else:
        # There is only one page, so just display that.
        await args.message.reply(embed = embed)
