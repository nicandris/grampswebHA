"""Photos come from image entities behind HA's login, not from www/."""
from unittest.mock import patch

from homeassistant.components.image import async_get_image
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.gramps_ha.grampsweb_api  # noqa: F401 (patch target)
import pytest
from custom_components.gramps_ha import _remove_downloaded_photos
from custom_components.gramps_ha.grampsweb_api import GrampsWebError

API = "custom_components.gramps_ha.grampsweb_api.GrampsWebAPI"
DATA = {"url": "https://g.example", "username": "u", "password": "p", "num_birthdays": 1,
        "show_deathdays": False, "show_anniversaries": True}
RAW = {"birthdays": [{"person_name": "Ann", "birth_date": "1980-01-01", "media_handle": "m1"}],
       "deceased_birthdays": [], "deathdays": [],
       "anniversaries": [{"person_name": "Ann & Bob", "marriage_date": "2001-02-03",
                          "media_handle_person1": "m1", "media_handle_person2": None}]}


async def setup(hass):
    entry = MockConfigEntry(domain="gramps_ha", data=DATA, title="Gramps HA")
    entry.add_to_hass(hass)
    with patch(f"{API}.fetch", return_value=RAW):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_photo_is_fetched_with_the_gramps_login(hass, enable_custom_integrations):
    await setup(hass)
    with patch(f"{API}.get_thumbnail", return_value=b"jpeg") as thumbnail:
        image = await async_get_image(hass, "image.birthdays_next_birthday_1_photo")
        await async_get_image(hass, "image.birthdays_next_birthday_1_photo")
    assert image.content == b"jpeg" and image.content_type == "image/jpeg"
    thumbnail.assert_called_once_with("m1")  # cached
    assert hass.states.get("image.anniversaries_next_anniversary_1_photo_person_1").state != "unknown"
    assert hass.states.get("image.anniversaries_next_anniversary_1_photo_person_2").state == "unknown"


def test_old_public_photos_are_deleted(tmp_path):
    folder = tmp_path / "gramps"
    folder.mkdir()
    (folder / "0123456789abcdef0123456789abcdef.jpg").touch()
    _remove_downloaded_photos(str(folder))
    assert not folder.exists()


def test_other_files_in_www_gramps_are_kept(tmp_path):
    folder = tmp_path / "gramps"
    folder.mkdir()
    (folder / "0123456789abcdef0123456789abcdef.jpg").touch()
    (folder / "family.png").touch()
    _remove_downloaded_photos(str(folder))
    assert [p.name for p in folder.iterdir()] == ["family.png"]


async def test_setup_cleans_www_gramps(hass, enable_custom_integrations):
    with patch("custom_components.gramps_ha._remove_downloaded_photos") as remove:
        await setup(hass)
    remove.assert_called_once_with(hass.config.path("www", "gramps"))


async def test_refresh_drops_the_cached_photo(hass, enable_custom_integrations):
    entry = await setup(hass)
    entity_id = "image.birthdays_next_birthday_1_photo"
    with patch(f"{API}.get_thumbnail", return_value=b"old"):
        assert (await async_get_image(hass, entity_id)).content == b"old"
    with patch(f"{API}.fetch", return_value={**RAW}):  # each fetch returns new data
        await entry.runtime_data.async_refresh()
    with patch(f"{API}.get_thumbnail", return_value=b"new"):
        assert (await async_get_image(hass, entity_id)).content == b"new"


async def test_failed_photo_is_logged_once_until_next_refresh(hass, enable_custom_integrations, caplog):
    entry = await setup(hass)
    entity_id = "image.birthdays_next_birthday_1_photo"
    with patch(f"{API}.get_thumbnail", side_effect=GrampsWebError("down")) as thumbnail:
        for _ in range(3):
            with pytest.raises(HomeAssistantError):
                await async_get_image(hass, entity_id)
    assert thumbnail.call_count == 1
    assert caplog.text.count("Could not load photo") == 1
    with patch(f"{API}.fetch", return_value={**RAW}):  # each fetch returns new data
        await entry.runtime_data.async_refresh()
    with patch(f"{API}.get_thumbnail", return_value=b"back"):
        assert (await async_get_image(hass, entity_id)).content == b"back"
