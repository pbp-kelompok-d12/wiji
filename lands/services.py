import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.core.cache import cache

NOMINATIM_URL = 'https://nominatim.openstreetmap.org'
NOMINATIM_USER_AGENT = 'Wiji/1.0 (+https://github.com/pbp-kelompok-d12/wiji)'


def nominatim(path, params):
    query = urlencode({**params, 'format': 'jsonv2', 'accept-language': 'id'})
    cache_key = f'nominatim:{path}:{query}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    request = Request(
        f'{NOMINATIM_URL}/{path}?{query}',
        headers={
            'User-Agent': NOMINATIM_USER_AGENT,
            'Accept': 'application/json',
        },
    )
    with urlopen(request, timeout=8) as response:
        data = json.load(response)

    cache.set(cache_key, data, 60 * 60 * 24)
    return data