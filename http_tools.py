import httpx

_client_obj = None

async def _client():
    global _client_obj

    if _client_obj is None:
        _client_obj = await httpx.AsyncClient().__aenter__()
    
    return _client_obj


async def request(method, url, **kwargs):
    '''
    Make a HTTP request.
    '''

    return await (await _client()).request(method, url, **kwargs)
