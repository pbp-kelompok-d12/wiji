import json
import math
from datetime import datetime, timedelta
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.core.cache import cache
from django.utils import timezone


NASA_POWER_URL = 'https://power.larc.nasa.gov/api/temporal/daily/point'
REQUEST_TIMEOUT_SECONDS = 10
CACHE_SECONDS = 60 * 60 * 24

# Minta data lebih panjang dari 365 hari karena data NASA POWER
# biasanya tertinggal beberapa hari dari tanggal hari ini.
REQUEST_HISTORY_DAYS = 380
RAIN_30_DAYS = 30
RAIN_YEAR_DAYS = 365
PARAMETER = 'PRECTOTCORR'


def _unavailable(reason):
    """Kembalikan status tanpa membuat atau mengarang data iklim."""
    messages = {
        'coordinates_missing': 'Koordinat lahan belum tersedia.',
        'coordinates_invalid': 'Koordinat lahan tidak valid.',
        'api_unavailable': 'Data iklim sementara tidak tersedia.',
        'response_invalid': 'Respons data iklim tidak valid.',
        'data_incomplete': 'Data curah hujan historis belum lengkap.',
    }

    return {
        'status': 'unavailable',
        'source': 'NASA POWER',
        'reason': reason,
        'message': messages[reason],
        'rainfall_30d': None,
        'rainfall_annual': None,
        'units': {
            'rainfall_30d': 'mm',
            'rainfall_annual': 'mm',
        },
        'period': None,
        'latest_data_date': None,
    }


def fetch_climate_data(lahan, today=None, timeout=REQUEST_TIMEOUT_SECONDS):
    """
    Ambil curah hujan historis untuk koordinat lahan dari NASA POWER.

    Hanya latitude dan longitude yang dikirim ke layanan. Nilai yang
    dikembalikan adalah total curah hujan 30 hari terakhir dan 365 hari
    terakhir, dihitung sampai tanggal data terakhir yang tersedia.
    """
    if lahan.latitude is None or lahan.longitude is None:
        return _unavailable('coordinates_missing')

    try:
        latitude = float(lahan.latitude)
        longitude = float(lahan.longitude)
    except (TypeError, ValueError, OverflowError):
        return _unavailable('coordinates_invalid')

    if (
        not math.isfinite(latitude)
        or not math.isfinite(longitude)
        or not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
    ):
        return _unavailable('coordinates_invalid')

    end_date = today or timezone.localdate()
    start_date = end_date - timedelta(days=REQUEST_HISTORY_DAYS - 1)

    cache_key = (
        f'nasa-power:{latitude:.4f}:{longitude:.4f}:{end_date.isoformat()}'
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    params = urlencode({
        'parameters': PARAMETER,
        'community': 'AG',
        'latitude': latitude,
        'longitude': longitude,
        'start': start_date.strftime('%Y%m%d'),
        'end': end_date.strftime('%Y%m%d'),
        'format': 'JSON',
    })

    request = Request(
        f'{NASA_POWER_URL}?{params}',
        headers={'Accept': 'application/json'},
        method='GET',
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            if getattr(response, 'status', 200) != 200:
                return _unavailable('api_unavailable')

            payload = json.loads(response.read().decode('utf-8'))

    except (URLError, TimeoutError, OSError):
        return _unavailable('api_unavailable')
    except (ValueError, UnicodeDecodeError):
        return _unavailable('response_invalid')

    if not isinstance(payload, dict):
        return _unavailable('response_invalid')

    properties = payload.get('properties')
    if not isinstance(properties, dict):
        return _unavailable('response_invalid')

    parameters = properties.get('parameter')
    if not isinstance(parameters, dict):
        return _unavailable('response_invalid')

    series = parameters.get(PARAMETER)
    if not isinstance(series, dict) or not series:
        return _unavailable('response_invalid')

    rainfall = {}
    for tanggal, value in series.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            continue

        try:
            hari = datetime.strptime(tanggal, '%Y%m%d').date()
        except (TypeError, ValueError):
            continue

        rainfall[hari] = float(value)

    if not rainfall:
        return _unavailable('data_incomplete')

    latest_date = max(rainfall)
    year_start = latest_date - timedelta(days=RAIN_YEAR_DAYS - 1)
    month_start = latest_date - timedelta(days=RAIN_30_DAYS - 1)

    tahunan = []
    for offset in range(RAIN_YEAR_DAYS):
        hari = year_start + timedelta(days=offset)
        if hari not in rainfall:
            return _unavailable('data_incomplete')
        tahunan.append(rainfall[hari])

    tiga_puluh_hari = []
    for offset in range(RAIN_30_DAYS):
        hari = month_start + timedelta(days=offset)
        if hari not in rainfall:
            return _unavailable('data_incomplete')
        tiga_puluh_hari.append(rainfall[hari])

    result = {
        'status': 'available',
        'source': 'NASA POWER',
        'reason': None,
        'message': 'Data iklim berhasil diambil.',
        'rainfall_30d': round(sum(tiga_puluh_hari), 1),
        'rainfall_annual': round(sum(tahunan), 1),
        'units': {
            'rainfall_30d': 'mm',
            'rainfall_annual': 'mm',
        },
        'period': {
            'start': year_start.isoformat(),
            'end': latest_date.isoformat(),
        },
        'latest_data_date': latest_date.isoformat(),
    }

    cache.set(cache_key, result, CACHE_SECONDS)
    return result
