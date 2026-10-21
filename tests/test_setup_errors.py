"""Outages and rejected logins reach HA instead of showing empty sensors."""
from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.gramps_ha.grampsweb_api import GrampsWebAuthError, GrampsWebError

DOMAIN = "gramps_ha"
API = "custom_components.gramps_ha.grampsweb_api.GrampsWebAPI"
BASE = {"url": "https://gramps.example", "username": "u", "password": "p",
        "num_birthdays": 1, "show_deathdays": False, "show_anniversaries": False, "scan_interval": 168}
RAW = {"birthdays": [], "deceased_birthdays": [], "deathdays": [], "anniversaries": []}


@pytest.fixture(autouse=True)
def _env(enable_custom_integrations):
    yield


async def setup(hass, error):
    entry = MockConfigEntry(domain=DOMAIN, data=BASE, title="Gramps HA", unique_id="https://gramps.example|u")
    entry.add_to_hass(hass)
    with patch(f"{API}.fetch", side_effect=error):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_outage_retries_setup(hass):
    entry = await setup(hass, GrampsWebError("down"))
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_rejected_login_starts_reauth(hass):
    entry = await setup(hass, GrampsWebAuthError("no"))
    assert entry.state is ConfigEntryState.SETUP_ERROR
    (flow,) = hass.config_entries.flow.async_progress()
    assert flow["context"]["source"] == config_entries.SOURCE_REAUTH and flow["step_id"] == "reauth_confirm"

    with patch(f"{API}.test_connection", side_effect=GrampsWebAuthError("no")):
        result = await hass.config_entries.flow.async_configure(flow["flow_id"], {"password": "bad"})
    assert result["errors"] == {"base": "invalid_auth"}

    with patch(f"{API}.test_connection"), patch(f"{API}.fetch", return_value=RAW):
        result = await hass.config_entries.flow.async_configure(flow["flow_id"], {"password": "new"})
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "reauth_successful"
    assert entry.data["password"] == "new"
    assert entry.state is ConfigEntryState.LOADED


@pytest.mark.parametrize(("error", "reason"), [(GrampsWebAuthError("no"), "invalid_auth"), (GrampsWebError("down"), "cannot_connect")])
async def test_user_flow_tests_the_login(hass, error, reason):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    with patch(f"{API}.test_connection", side_effect=error):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], BASE)
    assert result["type"] is FlowResultType.FORM and result["errors"] == {"base": reason}


async def test_same_instance_and_user_only_once(hass):
    MockConfigEntry(domain=DOMAIN, data=BASE, unique_id="https://gramps.example|u").add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    with patch(f"{API}.test_connection"):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {**BASE, "url": "https://Gramps.example/"})
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "already_configured"


async def test_failed_refresh_keeps_last_data(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=BASE, title="Gramps HA")
    entry.add_to_hass(hass)
    with patch(f"{API}.fetch", return_value={**RAW, "birthdays": [{"person_name": "Ann", "birth_date": "1980-01-01"}]}):
        assert await hass.config_entries.async_setup(entry.entry_id)
    coordinator = entry.runtime_data
    with patch(f"{API}.fetch", side_effect=GrampsWebError("down")):
        await coordinator.async_refresh()
    assert coordinator.last_update_success is False
    assert coordinator.data["birthdays"][0]["person_name"] == "Ann"


async def test_failed_refresh_retries_in_15_minutes(hass, freezer):
    entry = MockConfigEntry(domain=DOMAIN, data=BASE, title="Gramps HA")
    entry.add_to_hass(hass)
    with patch(f"{API}.fetch", return_value=RAW):
        assert await hass.config_entries.async_setup(entry.entry_id)
    with patch(f"{API}.fetch", side_effect=GrampsWebError("down")):
        await entry.runtime_data.async_refresh()
    with patch(f"{API}.fetch", return_value=RAW) as fetch:
        freezer.tick(timedelta(minutes=16))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
    assert fetch.called


async def test_url_is_stored_without_surrounding_spaces(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    with patch(f"{API}.test_connection"), patch(f"{API}.fetch", return_value=RAW):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {**BASE, "url": " https://gramps.example/ "})
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["url"] == "https://gramps.example/"


def test_client_ignores_spaces_in_a_stored_url():
    from custom_components.gramps_ha.grampsweb_api import GrampsWebAPI

    assert GrampsWebAPI(" https://gramps.example/ ").url == "https://gramps.example"


async def test_reauth_cannot_change_the_username(hass):
    entry = await setup(hass, GrampsWebAuthError("no"))
    (flow,) = hass.config_entries.flow.async_progress()
    result = await hass.config_entries.flow.async_configure(flow["flow_id"])
    assert [str(key) for key in result["data_schema"].schema] == ["password"]
    assert entry.data["username"] == "u"


async def test_entries_from_older_versions_get_a_unique_id(hass):
    old = MockConfigEntry(domain=DOMAIN, data={**BASE, "url": "https://Gramps.example/"}, title="Gramps HA")
    twin = MockConfigEntry(domain=DOMAIN, data=BASE, title="Gramps HA")  # same instance and user
    old.add_to_hass(hass)
    twin.add_to_hass(hass)
    with patch(f"{API}.fetch", return_value=RAW):
        await hass.config_entries.async_setup(old.entry_id)
        await hass.async_block_till_done()
    assert old.unique_id == "https://gramps.example|u"
    assert twin.unique_id is None  # left alone: the id is taken
