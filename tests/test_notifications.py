"""Notification settings: which events, lifetime, daily schedule."""
from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant.components import persistent_notification as pn
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

import custom_components.gramps_ha.grampsweb_api  # noqa: F401 (patch target)

DOMAIN = "gramps_ha"
API = "custom_components.gramps_ha.grampsweb_api.GrampsWebAPI"
BASE = {"url": "https://gramps.example", "username": "u", "password": "p",
        "num_birthdays": 1, "show_deathdays": False, "show_anniversaries": False, "scan_interval": 168}
START = "2026-03-10 12:00:00"  # local time


def day(n):  # date n days after START
    return (dt_util.parse_datetime(START).date() + timedelta(days=n)).isoformat()


def on(offset, year):  # the date n days after START, in another year
    return day(offset).replace(day(offset)[:4], str(year), 1)


def lists(offset):
    return {
        "birthdays": [{"person_name": "Ann", "birth_date": on(offset, 1982)}],
        "deceased_birthdays": [{"person_name": "Bob", "birth_date": on(offset, 1936)}],
        "deathdays": [{"person_name": "Cat", "death_date": on(offset, 2019)}],
        "anniversaries": [{"person_name": "Dan & Eve", "marriage_date": on(offset, 2001)}],
    }


STARTED = []


def serve(data):
    patcher = patch(f"{API}.fetch", return_value=data)
    patcher.start()
    STARTED.append(patcher)
    return patcher


def shown(hass):
    return {k: (v["title"], v["message"]) for k, v in pn._async_get_or_create_notifications(hass).items()}


async def setup(hass, offset=1, **extra):
    patches = [serve(lists(offset))]
    entry = MockConfigEntry(domain=DOMAIN, data={**BASE, **extra}, title="Gramps HA")
    entry.add_to_hass(hass)
    global ENTRY_ID
    ENTRY_ID = entry.entry_id
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry, patches


@pytest.fixture(autouse=True)
async def _env(enable_custom_integrations, freezer, hass):
    await hass.config.async_set_time_zone("Europe/Amsterdam")
    freezer.move_to(dt_util.parse_datetime(START).replace(tzinfo=dt_util.get_time_zone("Europe/Amsterdam")))
    yield
    for patcher in STARTED:  # not patch.stopall(): that also stops the plugin's session patches
        patcher.stop()
    STARTED.clear()


async def midnight(hass, freezer):
    nxt = dt_util.start_of_local_day(dt_util.now() + timedelta(days=1)) + timedelta(seconds=5)
    freezer.move_to(nxt)
    async_fire_time_changed(hass, nxt)
    await hass.async_block_till_done()


async def test_default_notifies_living_birthdays_only(hass):
    await setup(hass)
    n = shown(hass)
    assert list(n) == [f"gramps_ha_{ENTRY_ID}_birthdays_{day(1)}"]
    assert n[f"gramps_ha_{ENTRY_ID}_birthdays_{day(1)}"] == ("🎉 Birthday tomorrow!", "Ann has a birthday tomorrow!\n\nTurning 44")


async def test_empty_selection_turns_notifications_off(hass):
    await setup(hass, notify_events=[])
    assert shown(hass) == {}


async def test_every_kind_has_its_text(hass):
    await setup(hass, notify_events=["birthdays", "deceased_birthdays", "deathdays", "anniversaries"])
    msgs = sorted(m for _, m in shown(hass).values())
    assert msgs == sorted([
        "Ann has a birthday tomorrow!\n\nTurning 44",
        "Bob would have turned 90 tomorrow.",
        "Tomorrow it is 7 years since Cat died.",
        "Dan & Eve celebrate 25 years together tomorrow!",
    ])


async def test_daily_job_catches_birthdays_between_weekly_fetches(hass, freezer):
    await setup(hass, offset=3)  # fetched once; birthday in 3 days
    assert shown(hass) == {}
    await midnight(hass, freezer)  # day 1: birthday is in 2 days
    assert shown(hass) == {}
    await midnight(hass, freezer)  # day 2: tomorrow
    assert list(shown(hass)) == [f"gramps_ha_{ENTRY_ID}_birthdays_{day(3)}"]


@pytest.mark.parametrize(("mode", "kept"), [("until_dismissed", True), ("until_over", False)])
async def test_lifetime(hass, freezer, mode, kept):
    await setup(hass, notify_mode=mode)
    await midnight(hass, freezer)  # the birthday itself: still shown
    assert len(shown(hass)) == 1
    await midnight(hass, freezer)  # day after
    assert (len(shown(hass)) == 1) is kept


async def test_same_day_birthdays_share_one_notification(hass):
    data = lists(1)
    data["birthdays"].append({"person_name": "Zoe", "birth_date": "2023-03-11"})
    serve(data)
    entry = MockConfigEntry(domain=DOMAIN, data=BASE, title="Gramps HA")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    ((_title, message),) = shown(hass).values()
    assert message == "Ann has a birthday tomorrow!\n\nTurning 44\n\nZoe has a birthday tomorrow!\n\nTurning 3"


async def test_years_count_to_the_event_day_across_new_year(hass, freezer):
    # Fetched on 28 Dec 2026, but on 1 Jan 2027 it is 37 years since a 1 Jan 1990 death.
    data = lists(1)
    data["deathdays"] = [{"person_name": "Cat", "death_date": "1990-01-01"}]
    serve(data)
    freezer.move_to(dt_util.parse_datetime("2026-12-28 12:00:00").replace(tzinfo=dt_util.get_time_zone("Europe/Amsterdam")))
    entry = MockConfigEntry(domain=DOMAIN, data={**BASE, "notify_events": ["deathdays"]}, title="Gramps HA")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    for _ in range(3):  # 29, 30, 31 Dec
        await midnight(hass, freezer)
    ((_, message),) = shown(hass).values()
    assert message == "Tomorrow it is 37 years since Cat died."


async def restart(hass, entry):
    """HA forgets notifications on restart; the entry then sets up again."""
    pn._async_get_or_create_notifications(hass).clear()
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()


async def test_dismissed_notification_stays_gone_after_restart(hass, hass_storage, freezer):
    entry, _ = await setup(hass)
    (nid,) = shown(hass)
    pn.async_dismiss(hass, nid)
    freezer.tick(2)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass_storage[f"gramps_ha.{entry.entry_id}.dismissed"]["data"] == [nid]
    await restart(hass, entry)
    assert shown(hass) == {}


async def test_undismissed_notification_comes_back_after_restart(hass):
    entry, _ = await setup(hass)
    await restart(hass, entry)
    assert len(shown(hass)) == 1
