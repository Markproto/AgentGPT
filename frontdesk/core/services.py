"""
External service integrations for J. Austin Front Desk.
"""

import logging
import time
from functools import lru_cache

import requests

logger = logging.getLogger(__name__)

# Fortune Reserve API (FizTrade/Dillon Gage data)
FORTUNE_RESERVE_URL = "https://fortunereserve.com/wp-json/fortune-reserve/v1/spot-prices"

# Cache TTL in seconds
PRICE_CACHE_TTL = 60

# Module-level cache
_price_cache = {
    "data": None,
    "timestamp": 0,
}


def fetch_metal_prices():
    """
    Fetch live precious metal prices from Fortune Reserve API.

    Returns real bid/ask spreads from FizTrade/Dillon Gage.
    Caches results for PRICE_CACHE_TTL seconds.

    Returns:
        dict: {
            "success": bool,
            "prices": [
                {
                    "metal": "XAU",
                    "name": "Gold",
                    "bid": 2650.80,
                    "ask": 2652.40,
                    "spot": 2651.60,
                    "change": -12.50,
                    "changePercent": -0.47,
                },
                ...
            ],
            "timestamp": "Thursday, Jan 16 10:30:00 AM",
            "source": "FizTrade via Fortune Reserve",
            "cached": bool,
        }
    """
    global _price_cache

    # Check cache
    now = time.time()
    if _price_cache["data"] and (now - _price_cache["timestamp"]) < PRICE_CACHE_TTL:
        result = _price_cache["data"].copy()
        result["cached"] = True
        return result

    try:
        response = requests.get(
            FORTUNE_RESERVE_URL,
            timeout=5,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("success") or not data.get("data"):
            logger.warning("Fortune Reserve API returned unsuccessful response")
            return {"success": False, "error": "API returned unsuccessful response"}

        # Transform to our format
        prices = []
        order_map = {"XAU": 1, "XAG": 2, "XPT": 3, "XPD": 4}

        for key, metal in data["data"].items():
            symbol = metal.get("symbol")
            if not symbol:
                continue

            bid = float(metal.get("bid", 0))
            ask = float(metal.get("ask", 0))

            if not bid or not ask:
                continue

            prices.append({
                "metal": symbol,
                "name": metal.get("name", key.title()),
                "bid": bid,
                "ask": ask,
                "spot": round((bid + ask) / 2, 2),
                "spread": round(ask - bid, 2),
                "change": float(metal.get("change", 0)) if metal.get("change") is not None else None,
                "changePercent": float(metal.get("changePercent", 0)) if metal.get("changePercent") is not None else None,
                "order": order_map.get(symbol, 99),
            })

        # Sort by order
        prices.sort(key=lambda x: x["order"])

        result = {
            "success": True,
            "prices": prices,
            "timestamp": data.get("timestamp", ""),
            "source": data.get("source", "Fortune Reserve"),
            "cached": False,
        }

        # Update cache
        _price_cache["data"] = result
        _price_cache["timestamp"] = now

        return result

    except requests.exceptions.Timeout:
        logger.error("Fortune Reserve API timeout")
        return {"success": False, "error": "Price service timeout"}
    except requests.exceptions.RequestException as e:
        logger.error(f"Fortune Reserve API error: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error fetching prices: {e}")
        return {"success": False, "error": "Unexpected error"}


def get_metal_price(symbol):
    """
    Get price for a specific metal.

    Args:
        symbol: Metal symbol (XAU, XAG, XPT, XPD)

    Returns:
        dict or None: Price data for the metal
    """
    data = fetch_metal_prices()
    if not data.get("success"):
        return None

    for price in data.get("prices", []):
        if price["metal"] == symbol.upper():
            return price

    return None
