import asyncio
import os
from dataclasses import dataclass
from urllib.parse import urlencode

import aiohttp

from config import logger


BASE_URL = "https://otpx.org/api/stubs/handler_api.php"
OTPX_API_KEY = os.getenv("OTPX_API_KEY", "").strip()
OTPX_SERVICE = os.getenv("OTPX_SERVICE", "tg").strip() or "tg"


@dataclass(frozen=True)
class OtpxCountry:
    name: str
    code: str
    cost: int
    price: int
    flag: str = "🌍"


def _parse_countries() -> tuple[OtpxCountry, ...]:
    """Parse NAME:COUNTRY_CODE:COST:SELL_PRICE[, ...] from the environment."""
    raw = os.getenv("OTPX_COUNTRIES", "India:22:27:35").strip()
    flags = {"India": "🇮🇳", "USA/Canada": "🇺🇸", "UK": "🇬🇧", "Pakistan": "🇵🇰"}
    countries = []
    for item in raw.split(","):
        parts = [part.strip() for part in item.split(":")]
        if len(parts) != 4:
            logger.warning("Ignoring invalid OTPX_COUNTRIES entry: %s", item)
            continue
        name, code, cost, price = parts
        try:
            cost_int, price_int = int(cost), int(price)
        except ValueError:
            logger.warning("Ignoring non-numeric OTPX pricing entry: %s", item)
            continue
        if not name or not code.isdigit() or cost_int < 0 or price_int < 1:
            logger.warning("Ignoring invalid OTPX pricing entry: %s", item)
            continue
        countries.append(OtpxCountry(name, code, cost_int, price_int, flags.get(name, "🌍")))
    return tuple(countries)


OTPX_COUNTRIES = _parse_countries()


async def _request(params: dict[str, str]) -> str:
    if not OTPX_API_KEY:
        raise RuntimeError("OTPX_API_KEY is not configured")
    query = urlencode({"api_key": OTPX_API_KEY, **params})
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(f"{BASE_URL}?{query}") as response:
            text = (await response.text()).strip()
            if response.status >= 400:
                raise RuntimeError(f"OTPX HTTP {response.status}")
            return text


async def get_balance() -> float:
    response = await _request({"action": "getBalance"})
    if not response.startswith("ACCESS_BALANCE:"):
        raise RuntimeError(response or "OTPX returned an empty balance")
    return float(response.split(":", 1)[1])


async def acquire_number(country: OtpxCountry) -> tuple[str, str]:
    response = await _request(
        {
            "action": "getNumber",
            "service": OTPX_SERVICE,
            "country": country.code,
            "operator": "any",
        }
    )
    if not response.startswith("ACCESS_NUMBER:"):
        raise RuntimeError(response or "OTPX returned no number")
    parts = response.split(":")
    if len(parts) < 3:
        raise RuntimeError("OTPX returned an invalid number response")
    return parts[1], parts[2]


async def get_status(activation_id: str) -> str:
    return await _request({"action": "getStatus", "id": activation_id})


async def cancel_number(activation_id: str) -> str:
    return await _request({"action": "setStatus", "id": activation_id, "status": "8"})


async def wait_for_code(activation_id: str, timeout_seconds: int = 600) -> str:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        response = await get_status(activation_id)
        if response.startswith("STATUS_OK:"):
            return response.split(":", 1)[1]
        if response in {"STATUS_CANCEL", "NO_ACTIVATION", "ACCESS_CANCEL"}:
            raise RuntimeError(response)
        await asyncio.sleep(6)
    raise TimeoutError("Timed out waiting for OTPX SMS")