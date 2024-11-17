import display
import mcstatus
import os

async def get_mc_embed(bot, args):
    try:
        server = await mcstatus.JavaServer.async_lookup(os.getenv('MC_SERVER_IP'))
        status = await server.async_status()
    except:
        return display.create_embed("Minecraft Server Error", "Server could not be reached.")
    
    players = [f"`{player.name}`" for player in status.players.sample]

    await display.page(bot, args, players, "Online: " + str(status.players.online) + "/" + str(status.players.max))
    return None