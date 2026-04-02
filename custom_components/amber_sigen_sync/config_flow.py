"""Config flow for Amber to Sigen Sync."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import (
    CONF_FEED_IN_SENSOR,
    CONF_GENERAL_SENSOR,
    CONF_PLAN_NAME,
    CONF_SIGEN_DEVICE_ID,
    CONF_SIGEN_PASS_ENC,
    CONF_SIGEN_USER,
    CONF_STATION_ID,
    DEFAULT_FEED_IN_SENSOR,
    DEFAULT_GENERAL_SENSOR,
    DEFAULT_PLAN_NAME,
    DEFAULT_STATION_ID,
    DOMAIN,
)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_SIGEN_USER):                str,
    vol.Required(CONF_SIGEN_PASS_ENC):            str,
    vol.Required(CONF_SIGEN_DEVICE_ID):           str,
    vol.Required(CONF_STATION_ID):                vol.Coerce(int),
    vol.Optional(CONF_GENERAL_SENSOR,
                 default=DEFAULT_GENERAL_SENSOR):  str,
    vol.Optional(CONF_FEED_IN_SENSOR,
                 default=DEFAULT_FEED_IN_SENSOR):  str,
    vol.Optional(CONF_PLAN_NAME,
                 default=DEFAULT_PLAN_NAME):       str,
})


class AmberSigenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            return self.async_create_entry(
                title="Amber to Sigen Sync",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )