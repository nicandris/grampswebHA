"""Config flow for Gramps Web integration."""
from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .grampsweb_api import GrampsWebAPI, GrampsWebAuthError, GrampsWebError
from .const import DOMAIN, CONF_URL, CONF_USERNAME, CONF_PASSWORD, CONF_NUM_BIRTHDAYS, DEFAULT_NUM_BIRTHDAYS, CONF_SHOW_DEATHDAYS, CONF_SHOW_ANNIVERSARIES, DEFAULT_SHOW_DEATHDAYS, DEFAULT_SHOW_ANNIVERSARIES, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, CONF_ENTITY_LANGUAGE, DEFAULT_ENTITY_LANGUAGE, ENTITY_LANGUAGE_EN, ENTITY_LANGUAGE_HA, CONF_NOTIFY_EVENTS, NOTIFY_EVENTS, DEFAULT_NOTIFY_EVENTS, CONF_NOTIFY_MODE, NOTIFY_UNTIL_DISMISSED, NOTIFY_UNTIL_OVER, DEFAULT_NOTIFY_MODE

_LOGGER = logging.getLogger(__name__)

# hassfest rejects URLs inside translation strings
PLACEHOLDERS = {"example_url": "https://gramps.example.com"}


def _schema(values: dict[str, Any]) -> vol.Schema:
    """Form schema, pre-filled from values (empty for a new entry)."""
    return vol.Schema(
        {
            vol.Required(CONF_URL, default=values.get(CONF_URL, vol.UNDEFINED)): cv.string,
            vol.Required(CONF_USERNAME, default=values.get(CONF_USERNAME, vol.UNDEFINED)): cv.string,
            vol.Required(CONF_PASSWORD, default=values.get(CONF_PASSWORD, vol.UNDEFINED)): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
            vol.Optional(CONF_NUM_BIRTHDAYS, default=values.get(CONF_NUM_BIRTHDAYS, DEFAULT_NUM_BIRTHDAYS)): cv.positive_int,
            vol.Optional(CONF_SHOW_DEATHDAYS, default=values.get(CONF_SHOW_DEATHDAYS, DEFAULT_SHOW_DEATHDAYS)): cv.boolean,
            vol.Optional(CONF_SHOW_ANNIVERSARIES, default=values.get(CONF_SHOW_ANNIVERSARIES, DEFAULT_SHOW_ANNIVERSARIES)): cv.boolean,
            vol.Optional(CONF_SCAN_INTERVAL, default=values.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): cv.positive_int,
            vol.Optional(CONF_ENTITY_LANGUAGE, default=values.get(CONF_ENTITY_LANGUAGE, DEFAULT_ENTITY_LANGUAGE)): SelectSelector(
                SelectSelectorConfig(
                    options=[ENTITY_LANGUAGE_EN, ENTITY_LANGUAGE_HA],
                    translation_key=CONF_ENTITY_LANGUAGE,
                    mode=SelectSelectorMode.LIST,
                )
            ),
            vol.Optional(CONF_NOTIFY_EVENTS, default=values.get(CONF_NOTIFY_EVENTS, DEFAULT_NOTIFY_EVENTS)): SelectSelector(
                SelectSelectorConfig(
                    options=NOTIFY_EVENTS,
                    multiple=True,
                    translation_key=CONF_NOTIFY_EVENTS,
                    mode=SelectSelectorMode.LIST,
                )
            ),
            vol.Optional(CONF_NOTIFY_MODE, default=values.get(CONF_NOTIFY_MODE, DEFAULT_NOTIFY_MODE)): SelectSelector(
                SelectSelectorConfig(
                    options=[NOTIFY_UNTIL_DISMISSED, NOTIFY_UNTIL_OVER],
                    translation_key=CONF_NOTIFY_MODE,
                    mode=SelectSelectorMode.LIST,
                )
            ),
        }
    )


def _validate(user_input: dict[str, Any]) -> dict[str, str]:
    """Return form errors, empty when the input is usable."""
    errors = {}
    url = user_input.get(CONF_URL, "").strip()
    if not url:
        errors[CONF_URL] = "required"
    elif not url.startswith(("http://", "https://")):
        errors[CONF_URL] = "invalid_url"
    return errors


def _unique_id(user_input: dict[str, Any]) -> str:
    return f"{user_input[CONF_URL].strip().rstrip('/').lower()}|{user_input[CONF_USERNAME]}"


class GrampsHAConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gramps HA."""

    VERSION = 1

    async def _test_login(self, user_input: dict[str, Any]) -> dict[str, str]:
        """Form errors from logging in with user_input, empty on success."""
        api = GrampsWebAPI(
            user_input[CONF_URL].strip(), user_input.get(CONF_USERNAME), user_input.get(CONF_PASSWORD)
        )
        try:
            await self.hass.async_add_executor_job(api.test_connection)
        except GrampsWebAuthError:
            return {"base": "invalid_auth"}
        except GrampsWebError as err:
            _LOGGER.debug("Cannot connect to Gramps Web: %s", err)
            return {"base": "cannot_connect"}
        return {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            errors = _validate(user_input) or await self._test_login(user_input)
            if not errors:
                await self.async_set_unique_id(_unique_id(user_input))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Gramps HA",
                    data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input or {}),
            errors=errors,
            description_placeholders=PLACEHOLDERS,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Gramps Web rejected the stored credentials."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask for the password again."""
        entry = self._get_reauth_entry()
        errors = {}
        if user_input is not None:
            data = {**entry.data, **user_input}
            errors = await self._test_login(data)
            if not errors:
                return self.async_update_reload_and_abort(entry, data_updates=user_input)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default=entry.data.get(CONF_USERNAME, vol.UNDEFINED)): cv.string,
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
            description_placeholders={"url": entry.data.get(CONF_URL, "")},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Change the settings of an existing entry and reload it."""
        entry = self._get_reconfigure_entry()
        errors = {}
        if user_input is not None:
            errors = _validate(user_input) or await self._test_login(user_input)
            if not errors:
                return self.async_update_reload_and_abort(
                    entry, unique_id=_unique_id(user_input), data_updates=user_input
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema({**entry.data, **(user_input or {})}),
            errors=errors,
            description_placeholders=PLACEHOLDERS,
        )
