"""Setup option for entity-name language + reconfigure, against real HA core."""
from unittest.mock import PropertyMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.gramps_ha.grampsweb_api  # noqa: F401 (patch target)

DOMAIN = "gramps_ha"
API = "custom_components.gramps_ha.grampsweb_api.GrampsWebAPI"
RAW = {"birthdays": [{"person_name": "Ann", "birth_date": "1980-01-01"}],
       "deceased_birthdays": [], "deathdays": [], "anniversaries": []}
BASE = {"url": "https://gramps.example", "username": "u", "password": "p",
        "num_birthdays": 1, "show_deathdays": False, "show_anniversaries": False, "scan_interval": 168}


@pytest.fixture(autouse=True)
def _env(enable_custom_integrations, tmp_path):
    # every entity enabled, so all names can be checked
    enabled = patch("homeassistant.helpers.entity.Entity.entity_registry_enabled_default",
                    new_callable=PropertyMock, return_value=True)
    with patch(f"{API}.fetch", return_value=RAW), patch(f"{API}.test_connection"), enabled:
        yield


def names(hass, entry):
    ent = er.async_get(hass)
    out = {}
    for e in er.async_entries_for_config_entry(ent, entry.entry_id):
        out[e.unique_id.removeprefix(entry.entry_id + "_")] = (e.entity_id, hass.states.get(e.entity_id).name)
    return out


def device_names(hass, entry):
    return sorted(d.name for d in dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id))


async def setup(hass, data):
    entry = MockConfigEntry(domain=DOMAIN, data=data, title="Gramps HA")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_existing_entry_keeps_english_names(hass):
    hass.config.language = "de"
    entry = await setup(hass, BASE)  # no entity_language key: an install from before this change
    n = names(hass, entry)
    assert n["birthday_0_age"][1] == "Birthdays Next Birthday 1 Age"
    assert n["all_birthdays"][1] == "Gramps HA All Upcoming Birthdays"
    assert "Birthdays" in device_names(hass, entry)


async def test_ha_language_names_then_reconfigure_back(hass):
    hass.config.language = "de"
    entry = await setup(hass, {**BASE, "entity_language": "ha"})
    before = names(hass, entry)
    assert before["birthday_0_age"][1] == "Geburtstage Nächster Geburtstag 1 Alter"
    assert before["deceased_birthday_0_name"][1] == "Geburtstage Verstorbener Nächster Geburtstag Verstorbener 1 Name"
    assert "Geburtstage" in device_names(hass, entry)

    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "reconfigure"
    # form is pre-filled from the entry
    defaults = {str(k): k.default() for k in result["data_schema"].schema if callable(getattr(k, "default", None))}
    assert defaults["entity_language"] == "ha" and "password" not in defaults  # stored password not sent back

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {**BASE, "entity_language": "en"})
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert entry.data["entity_language"] == "en"
    after = names(hass, entry)
    assert after["birthday_0_age"][1] == "Birthdays Next Birthday 1 Age"
    assert {k: v[0] for k, v in after.items()} == {k: v[0] for k, v in before.items()}, "entity ids must not change"
    assert "Birthdays" in device_names(hass, entry)


async def test_reconfigure_rejects_bad_url(hass):
    entry = await setup(hass, BASE)
    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {**BASE, "url": "gramps.example"})
    assert result["type"] is FlowResultType.FORM and result["errors"] == {"url": "invalid_url"}


async def test_user_flow_stores_choice(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {**BASE, "entity_language": "ha"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["entity_language"] == "ha"


@pytest.mark.parametrize("lang", ["en", "de", "fr", "it", "bs", "nl"])
async def test_every_language_resolves_all_names(hass, lang):
    hass.config.language = lang
    entry = await setup(hass, {**BASE, "entity_language": "ha", "show_deathdays": True, "show_anniversaries": True})
    n = names(hass, entry)
    assert len(n) == 1 + 7 * 2 + 7 + 8 + 5  # all, birthday, deceased, deathday, anniversary sensors; 5 photos
    assert all(name and "{n}" not in name for _, name in n.values())


async def test_reconfigure_without_password_keeps_it(hass):
    entry = await setup(hass, BASE)
    result = await entry.start_reconfigure_flow(hass)
    data = {k: v for k, v in BASE.items() if k != "password"}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], data)
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["password"] == "p"


@pytest.mark.parametrize(("url", "error"), [
    ("http://gramps.example.com", {"url": "insecure_url"}),
    ("http://192.168.1.5:5000", {}),
    ("http://homeassistant.local:5000", {}),
    ("http://gramps", {}),
    ("https://gramps.example.com", {}),
])
async def test_plain_http_only_on_the_local_network(hass, url, error):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {**BASE, "url": url})
    assert result.get("errors", {}) == error
