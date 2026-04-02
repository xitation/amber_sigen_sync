"""Amber to Sigen Sync integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN
from .coordinator import AmberSigenCoordinator

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    coordinator = AmberSigenCoordinator(hass, entry)
    await coordinator.async_setup()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_force_sync(call: ServiceCall) -> None:
        """Handle force sync service call."""
        for coord in hass.data[DOMAIN].values():
            await coord.async_force_sync()

    hass.services.async_register(DOMAIN, "force_sync", handle_force_sync)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator = hass.data[DOMAIN].pop(entry.entry_id)
    coordinator.async_teardown()
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, "force_sync")
    return unloaded