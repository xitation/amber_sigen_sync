"""Sensor platform for Amber → Sigen Tariff Sync."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AmberSigenSyncSensor(coordinator, entry)])


class AmberSigenSyncSensor(SensorEntity):
    """Shows last sync status."""

    _attr_name            = "Amber Sigen Tariff Sync"
    _attr_unique_id       = "amber_sigen_sync_status"
    _attr_icon            = "mdi:lightning-bolt-circle"

    def __init__(self, coordinator, entry):
        self._coordinator = coordinator
        self._entry       = entry
        self._coordinator.async_add_listener(self._handle_coordinator_update)

    def _handle_coordinator_update(self):
        self.schedule_update_ha_state()

    @property
    def state(self):
        return self._coordinator.last_status

    @property
    def extra_state_attributes(self):
        return {
            "last_sync":  self._coordinator.last_sync,
            "last_error": self._coordinator.last_error,
        }

    async def async_will_remove_from_hass(self):
        self._coordinator.async_remove_listener(self._handle_coordinator_update)