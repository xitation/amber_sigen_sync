"""Coordinator for Amber → Sigen Tariff Sync."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_FEED_IN_SENSOR,
    CONF_GENERAL_SENSOR,
    CONF_PLAN_NAME,
    CONF_SIGEN_DEVICE_ID,
    CONF_SIGEN_PASS_ENC,
    CONF_SIGEN_USER,
    CONF_STATION_ID,
    DEFAULT_PLAN_NAME,
    SIGEN_AUTH_HEADERS,
    SIGEN_AUTH_URL,
    SIGEN_POST_HEADERS,
    SIGEN_TARIFF_URL,
)

_LOGGER = logging.getLogger(__name__)


class AmberSigenCoordinator:
    """Manages auth and tariff sync to Sigen Cloud."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass        = hass
        self.entry       = entry
        self._bearer     = None
        self._unsub      = None
        self.last_sync   = None
        self.last_status = "never_run"
        self.last_error  = None
        self._listeners  = []
        self._tz = ZoneInfo(hass.config.time_zone)

    async def async_setup(self) -> None:
        """Start listening for Amber price changes."""
        general_sensor = self.entry.data.get(
            CONF_GENERAL_SENSOR,
            "sensor.amber_express_home_general_price_detailed"
        )
        self._unsub = async_track_state_change_event(
            self.hass,
            [general_sensor],
            self._handle_price_change,
        )
        _LOGGER.info("AmberSigenSync: listening on %s", general_sensor)

    @callback
    def async_teardown(self) -> None:
        """Remove listeners."""
        if self._unsub:
            self._unsub()

    @callback
    def _handle_price_change(self, event) -> None:
        """Fire sync when Amber publishes a confirmed price."""
        new_state = event.data.get("new_state")
        if new_state is None:
            return
        if new_state.state in ("unavailable", "unknown"):
            return
        # Only sync on confirmed prices, not estimates
        if new_state.attributes.get("estimate", True):
            _LOGGER.debug("AmberSigenSync: skipping estimate price")
            return
        _LOGGER.info("AmberSigenSync: confirmed price received, triggering sync")
        asyncio.create_task(self._sync())

    async def _get_bearer(self) -> str | None:
        """Authenticate with Sigen Cloud and return bearer token."""
        data = self.entry.data
        payload = (
            f"grant_type=password"
            f"&username={data[CONF_SIGEN_USER]}"
            f"&password={data[CONF_SIGEN_PASS_ENC]}"
            f"&userDeviceId={data[CONF_SIGEN_DEVICE_ID]}"
            f"&scope=server"
        )
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    SIGEN_AUTH_URL,
                    headers=SIGEN_AUTH_HEADERS,
                    data=payload,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        _LOGGER.error(
                            "AmberSigenSync: auth failed HTTP %s", resp.status
                        )
                        return None
                    body = await resp.json(content_type=None)
                    token = body.get("data", {}).get("access_token")
                    if not token:
                        _LOGGER.error(
                            "AmberSigenSync: no access_token in response: %s", body
                        )
                        return None
                    _LOGGER.debug("AmberSigenSync: auth OK")
                    return token
        except Exception as err:
            _LOGGER.error("AmberSigenSync: auth exception: %s", err)
            return None

    def _build_payload(self) -> dict | None:
        """Build Sigen single rate payload from current Amber price."""
        data = self.entry.data
        general_sensor = data.get(
            CONF_GENERAL_SENSOR,
            "sensor.amber_express_home_general_price_detailed"
        )
        feed_in_sensor = data.get(
            CONF_FEED_IN_SENSOR,
            "sensor.amber_express_home_feed_in_price_detailed"
        )

        gen_state = self.hass.states.get(general_sensor)
        fit_state  = self.hass.states.get(feed_in_sensor)

        if not gen_state or not fit_state:
            _LOGGER.error("AmberSigenSync: sensor states not found")
            return None

        try:
            # Current prices — $/kWh * 100 = cents
            buy_price  = round(float(gen_state.state) * 100, 5)
            sell_price = round(float(fit_state.state) * 100, 5)
        except (ValueError, TypeError) as err:
            _LOGGER.error("AmberSigenSync: could not parse prices: %s", err)
            return None

        if buy_price <= 0:
            _LOGGER.warning(
                "AmberSigenSync: zero/negative buy price %s — skipping sync",
                buy_price
            )
            return None

        station_id = data.get(CONF_STATION_ID)
        if not station_id:
            _LOGGER.error("AmberSigenSync: no station_id configured")
            return None

        plan_name = data.get(CONF_PLAN_NAME, DEFAULT_PLAN_NAME)

        _LOGGER.info(
            "AmberSigenSync: building payload buy=%.5fc sell=%.5fc",
            buy_price, sell_price
        )

        def make_pricing(price):
            return {
                "dynamicPricing": None,
                "staticPricing": {
                    "providerName": "Amber Electric",
                    "tariffCode":   None,
                    "tariffName":   None,
                    "currencyCode": "Cent",
                    "subAreaName":  None,
                    "planName":     plan_name,
                    "combinedPrices": [{
                        "monthRange": "01-12",
                        "weekPrices": [{
                            "weekRange": "1-7",
                            "timeRange": [{
                                "timeRange": "00:00-24:00",
                                "price": price
                            }]
                        }]
                    }]
                }
            }

        return {
            "stationId": station_id,
            "priceMode": 1,
            "buyPrice":  make_pricing(buy_price),
            "sellPrice": make_pricing(sell_price),
        }

    async def _sync(self) -> None:
        """Full sync: build payload, auth, POST to Sigen."""
        payload = self._build_payload()
        if payload is None:
            self.last_status = "error"
            self.last_error  = "Failed to build tariff payload"
            self._notify_listeners()
            return

        bearer = await self._get_bearer()
        if not bearer:
            self.last_status = "error"
            self.last_error  = "Authentication failed"
            self._notify_listeners()
            return

        headers = {
            **SIGEN_POST_HEADERS,
            "Authorization": f"Bearer {bearer}",
            "Content-Type":  "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    SIGEN_TARIFF_URL,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    body = await resp.text()
                    if resp.status in (200, 201):
                        _LOGGER.info(
                            "AmberSigenSync: tariff sync OK HTTP %s body: %s",
                            resp.status, body
                        )
                        self.last_sync   = datetime.now(self._tz).isoformat()
                        self.last_status = "ok"
                        self.last_error  = None
                    else:
                        _LOGGER.error(
                            "AmberSigenSync: POST failed HTTP %s: %s",
                            resp.status, body
                        )
                        self.last_status = "error"
                        self.last_error  = f"HTTP {resp.status}: {body[:200]}"
        except Exception as err:
            _LOGGER.error("AmberSigenSync: POST exception: %s", err)
            self.last_status = "error"
            self.last_error  = str(err)

        self._notify_listeners()

    def async_add_listener(self, update_callback):
        """Register a listener for state updates."""
        self._listeners.append(update_callback)

    def async_remove_listener(self, update_callback):
        """Remove a listener."""
        self._listeners.remove(update_callback)

    def _notify_listeners(self):
        """Notify all registered listeners."""
        for listener in self._listeners:
            listener()

    async def async_force_sync(self) -> None:
        """Manually trigger a sync regardless of estimate status."""
        _LOGGER.info("AmberSigenSync: manual sync triggered")
        await self._sync()
