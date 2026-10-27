import json
import math
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_SECONDS = 5

CURRENT_VARIABLES = (
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
)


def _unavailable(reason):
    """Return status tanpa membuat atau mengarang data cuaca."""
    messages = {
        "coordinates_missing": "Koordinat lahan belum tersedia.",
        "coordinates_invalid": "Koordinat lahan tidak valid.",
        "api_unavailable": "Data cuaca sementara tidak tersedia.",
        "response_invalid": "Respons data cuaca tidak valid.",
    }

    return {
        "status": "unavailable",
        "source": "Open-Meteo",
        "reason": reason,
        "message": messages[reason],
        "timezone": None,
        "current": {},
        "units": {},
    }


def fetch_environmental_data(lahan, timeout=REQUEST_TIMEOUT_SECONDS):
    """
    Ambil kondisi cuaca terkini untuk koordinat lahan.

    Hanya latitude dan longitude yang dikirim ke Open-Meteo.
    Nama pemilik, nama lahan, alamat, dan data pemeriksaan tanah
    tidak ikut dikirim.
    """
    if lahan.latitude is None or lahan.longitude is None:
        return _unavailable("coordinates_missing")

    try:
        latitude = float(lahan.latitude)
        longitude = float(lahan.longitude)
    except (TypeError, ValueError, OverflowError):
        return _unavailable("coordinates_invalid")

    if (
        not math.isfinite(latitude)
        or not math.isfinite(longitude)
        or not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
    ):
        return _unavailable("coordinates_invalid")

    params = urlencode({
        "latitude": latitude,
        "longitude": longitude,
        "current": ",".join(CURRENT_VARIABLES),
        "timezone": "auto",
    })

    request = Request(
        f"{OPEN_METEO_URL}?{params}",
        headers={"Accept": "application/json"},
        method="GET",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            if getattr(response, "status", 200) != 200:
                return _unavailable("api_unavailable")

            payload = json.loads(response.read().decode("utf-8"))

    except (URLError, TimeoutError, OSError):
        return _unavailable("api_unavailable")
    except (ValueError, UnicodeDecodeError):
        return _unavailable("response_invalid")

    if not isinstance(payload, dict):
        return _unavailable("response_invalid")

    current = payload.get("current")
    units = payload.get("current_units")
    timezone = payload.get("timezone")

    if not isinstance(current, dict) or not isinstance(units, dict):
        return _unavailable("response_invalid")

    if not isinstance(timezone, str) or not timezone:
        return _unavailable("response_invalid")

    for variable in CURRENT_VARIABLES:
        value = current.get(variable)

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not isinstance(units.get(variable), str)
        ):
            return _unavailable("response_invalid")

    if not isinstance(current.get("time"), str):
        return _unavailable("response_invalid")

    return {
        "status": "available",
        "source": "Open-Meteo",
        "reason": None,
        "message": "Data cuaca berhasil diambil.",
        "timezone": timezone,
        "current": {
            "time": current["time"],
            **{
                variable: current[variable]
                for variable in CURRENT_VARIABLES
            },
        },
        "units": {
            variable: units[variable]
            for variable in CURRENT_VARIABLES
        },
    }