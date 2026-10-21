"""Sensor platform: unique_ids/entity_ids survive the refactor, each kind reads its own list."""
from datetime import datetime, timedelta
from unittest.mock import PropertyMock, patch

import pytest

import custom_components.gramps_ha.grampsweb_api  # noqa: F401 (patch target)
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

API = "custom_components.gramps_ha.grampsweb_api.GrampsWebAPI"
DATA = {"url": "https://g.example", "username": "u", "password": "p",
        "num_birthdays": 2, "show_deathdays": True, "show_anniversaries": True}
EMPTY = {"birthdays": [], "deceased_birthdays": [], "deathdays": [], "anniversaries": []}

# unique_id suffix -> entity_id, as created by sensor.py before the G13 refactor
BEFORE = {
    'all_birthdays': 'sensor.gramps_ha_all_upcoming_birthdays',
    'anniversary_0_date': 'sensor.anniversaries_next_anniversary_1_date',
    'anniversary_0_days_until': 'sensor.anniversaries_next_anniversary_1_days_until',
    'anniversary_0_image_person1': 'sensor.anniversaries_next_anniversary_1_image_person_1',
    'anniversary_0_image_person2': 'sensor.anniversaries_next_anniversary_1_image_person_2',
    'anniversary_0_link': 'sensor.anniversaries_next_anniversary_1_link',
    'anniversary_0_name': 'sensor.anniversaries_next_anniversary_1_name',
    'anniversary_0_upcoming_date': 'sensor.anniversaries_next_anniversary_1_upcoming_date',
    'anniversary_0_years_together': 'sensor.anniversaries_next_anniversary_1_years_together',
    'anniversary_1_date': 'sensor.anniversaries_next_anniversary_2_date',
    'anniversary_1_days_until': 'sensor.anniversaries_next_anniversary_2_days_until',
    'anniversary_1_image_person1': 'sensor.anniversaries_next_anniversary_2_image_person_1',
    'anniversary_1_image_person2': 'sensor.anniversaries_next_anniversary_2_image_person_2',
    'anniversary_1_link': 'sensor.anniversaries_next_anniversary_2_link',
    'anniversary_1_name': 'sensor.anniversaries_next_anniversary_2_name',
    'anniversary_1_upcoming_date': 'sensor.anniversaries_next_anniversary_2_upcoming_date',
    'anniversary_1_years_together': 'sensor.anniversaries_next_anniversary_2_years_together',
    'birthday_0_age': 'sensor.birthdays_next_birthday_1_age',
    'birthday_0_date': 'sensor.birthdays_next_birthday_1_date',
    'birthday_0_days_until': 'sensor.birthdays_next_birthday_1_days_until',
    'birthday_0_image': 'sensor.birthdays_next_birthday_1_image',
    'birthday_0_link': 'sensor.birthdays_next_birthday_1_link',
    'birthday_0_name': 'sensor.birthdays_next_birthday_1_name',
    'birthday_0_upcoming_date': 'sensor.birthdays_next_birthday_1_upcoming_date',
    'birthday_1_age': 'sensor.birthdays_next_birthday_2_age',
    'birthday_1_date': 'sensor.birthdays_next_birthday_2_date',
    'birthday_1_days_until': 'sensor.birthdays_next_birthday_2_days_until',
    'birthday_1_image': 'sensor.birthdays_next_birthday_2_image',
    'birthday_1_link': 'sensor.birthdays_next_birthday_2_link',
    'birthday_1_name': 'sensor.birthdays_next_birthday_2_name',
    'birthday_1_upcoming_date': 'sensor.birthdays_next_birthday_2_upcoming_date',
    'deathday_0_date': 'sensor.deathdays_next_deathday_1_date',
    'deathday_0_days_until': 'sensor.deathdays_next_deathday_1_days_until',
    'deathday_0_image': 'sensor.deathdays_next_deathday_1_image',
    'deathday_0_link': 'sensor.deathdays_next_deathday_1_link',
    'deathday_0_name': 'sensor.deathdays_next_deathday_1_name',
    'deathday_0_upcoming_date': 'sensor.deathdays_next_deathday_1_upcoming_date',
    'deathday_0_years_ago': 'sensor.deathdays_next_deathday_1_years_ago',
    'deathday_1_date': 'sensor.deathdays_next_deathday_2_date',
    'deathday_1_days_until': 'sensor.deathdays_next_deathday_2_days_until',
    'deathday_1_image': 'sensor.deathdays_next_deathday_2_image',
    'deathday_1_link': 'sensor.deathdays_next_deathday_2_link',
    'deathday_1_name': 'sensor.deathdays_next_deathday_2_name',
    'deathday_1_upcoming_date': 'sensor.deathdays_next_deathday_2_upcoming_date',
    'deathday_1_years_ago': 'sensor.deathdays_next_deathday_2_years_ago',
    'deceased_birthday_0_age': 'sensor.deceased_birthdays_next_deceased_birthday_1_age',
    'deceased_birthday_0_date': 'sensor.deceased_birthdays_next_deceased_birthday_1_date',
    'deceased_birthday_0_days_until': 'sensor.deceased_birthdays_next_deceased_birthday_1_days_until',
    'deceased_birthday_0_image': 'sensor.deceased_birthdays_next_deceased_birthday_1_image',
    'deceased_birthday_0_link': 'sensor.deceased_birthdays_next_deceased_birthday_1_link',
    'deceased_birthday_0_name': 'sensor.deceased_birthdays_next_deceased_birthday_1_name',
    'deceased_birthday_0_upcoming_date': 'sensor.deceased_birthdays_next_deceased_birthday_1_upcoming_date',
    'deceased_birthday_1_age': 'sensor.deceased_birthdays_next_deceased_birthday_2_age',
    'deceased_birthday_1_date': 'sensor.deceased_birthdays_next_deceased_birthday_2_date',
    'deceased_birthday_1_days_until': 'sensor.deceased_birthdays_next_deceased_birthday_2_days_until',
    'deceased_birthday_1_image': 'sensor.deceased_birthdays_next_deceased_birthday_2_image',
    'deceased_birthday_1_link': 'sensor.deceased_birthdays_next_deceased_birthday_2_link',
    'deceased_birthday_1_name': 'sensor.deceased_birthdays_next_deceased_birthday_2_name',
    'deceased_birthday_1_upcoming_date': 'sensor.deceased_birthdays_next_deceased_birthday_2_upcoming_date',
}


@pytest.fixture
def all_enabled():
    with patch("homeassistant.helpers.entity.Entity.entity_registry_enabled_default",
               new_callable=PropertyMock, return_value=True):
        yield


async def setup(hass, raw, data=DATA):
    entry = MockConfigEntry(domain="gramps_ha", data=data, title="Gramps HA")
    entry.add_to_hass(hass)
    with patch(f"{API}.fetch", return_value=raw):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def registry(hass, entry, domain="sensor"):
    return {
        e.unique_id.removeprefix(entry.entry_id + "_"): e.entity_id
        for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        if e.domain == domain
    }


async def test_unique_ids_and_entity_ids_unchanged(hass, enable_custom_integrations):
    entry = await setup(hass, EMPTY)
    assert registry(hass, entry) == BEFORE


async def test_deathdays_and_anniversaries_without_living_birthdays(hass, enable_custom_integrations, freezer, all_enabled):
    freezer.move_to("2026-10-21 12:00:00")
    raw = {**EMPTY,
           "deathdays": [{"person_name": "Cat", "death_date": "2000-10-25", "person_handle": "h"}],
           "anniversaries": [{"person_name": "Dan & Eve", "marriage_date": "2001-10-23", "family_handle": "F"}]}
    await setup(hass, raw)
    assert hass.states.get("sensor.deathdays_next_deathday_1_name").state == "Cat"
    assert hass.states.get("sensor.deathdays_next_deathday_1_days_until").state == "4"
    assert hass.states.get("sensor.deathdays_next_deathday_1_link").state == "https://g.example/person/h"
    assert hass.states.get("sensor.anniversaries_next_anniversary_1_years_together").state == "25"
    assert hass.states.get("sensor.anniversaries_next_anniversary_1_link").state == "https://g.example/family/F"
    assert hass.states.get("sensor.birthdays_next_birthday_1_name").state == "unknown"


async def test_days_until_and_order_follow_the_day_without_a_fetch(hass, enable_custom_integrations, freezer):
    await hass.config.async_set_time_zone("Europe/Amsterdam")
    zone = dt_util.get_time_zone("Europe/Amsterdam")
    # 23:30 local is already the next day in UTC: days must follow HA's time zone
    freezer.move_to(datetime(2026, 10, 20, 23, 30, tzinfo=zone))
    raw = {**EMPTY, "birthdays": [{"person_name": "Ann", "birth_date": "1990-10-21"},
                                  {"person_name": "Bob", "birth_date": "1990-10-23"}]}
    await setup(hass, raw)
    days, name = "sensor.birthdays_next_birthday_1_days_until", "sensor.birthdays_next_birthday_1_name"
    assert (hass.states.get(name).state, hass.states.get(days).state) == ("Ann", "1")

    for expected in [("Ann", "0"), ("Bob", "1"), ("Bob", "0")]:
        nxt = dt_util.start_of_local_day(dt_util.now() + timedelta(days=1)) + timedelta(seconds=5)
        freezer.move_to(nxt)
        async_fire_time_changed(hass, nxt)
        await hass.async_block_till_done()
        assert (hass.states.get(name).state, hass.states.get(days).state) == expected
    assert hass.states.get("sensor.birthdays_next_birthday_2_upcoming_date").state == "2027-10-21"


async def test_all_birthdays_is_opt_in_and_not_recorded(recorder_mock, hass, enable_custom_integrations):
    from homeassistant.components.recorder.history import get_significant_states
    from pytest_homeassistant_custom_component.components.recorder.common import async_wait_recording_done

    raw = {**EMPTY, "birthdays": [{"person_name": "Ann", "birth_date": "1980-01-01"}]}
    entry = await setup(hass, raw)
    entity_id = "sensor.gramps_ha_all_upcoming_birthdays"
    registry_entry = er.async_get(hass).async_get(entity_id)
    assert registry_entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION

    er.async_get(hass).async_update_entity(entity_id, disabled_by=None)
    with patch(f"{API}.fetch", return_value=raw):
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
    assert hass.states.get(entity_id).attributes["birthdays"][0]["person_name"] == "Ann"
    await async_wait_recording_done(hass)
    history = await recorder_mock.async_add_executor_job(
        get_significant_states, hass, dt_util.utcnow() - timedelta(hours=1), None, [entity_id]
    )
    assert history[entity_id] and all("birthdays" not in s.attributes for s in history[entity_id])


async def test_deceased_birthdays_can_be_turned_off(hass, enable_custom_integrations):
    entry = await setup(hass, EMPTY, {**DATA, "show_deceased_birthdays": False})
    assert registry(hass, entry) == {k: v for k, v in BEFORE.items() if not k.startswith("deceased_")}
    assert not any(k.startswith("deceased_") for k in registry(hass, entry, "image"))


async def test_fewer_slots_remove_the_old_entities(hass, enable_custom_integrations):
    entry = await setup(hass, EMPTY)
    hass.config_entries.async_update_entry(entry, data={**DATA, "num_birthdays": 1, "show_anniversaries": False})
    with patch(f"{API}.fetch", return_value=EMPTY):
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
    assert registry(hass, entry) == {
        k: v for k, v in BEFORE.items() if "_1_" not in k and not k.startswith("anniversary_")
    }
    assert sorted(registry(hass, entry, "image")) == ["birthday_0_photo", "deathday_0_photo", "deceased_birthday_0_photo"]


async def test_link_and_image_sensors_are_opt_in(hass, enable_custom_integrations):
    entry = await setup(hass, EMPTY)
    disabled = {
        e.unique_id.removeprefix(entry.entry_id + "_")
        for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        if e.disabled_by and e.domain == "sensor"
    }
    assert disabled == {k for k in BEFORE if k.endswith(("_link", "_image", "_image_person1", "_image_person2"))} | {"all_birthdays"}
