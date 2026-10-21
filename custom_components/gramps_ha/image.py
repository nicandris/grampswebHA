"""Photos of the people behind the upcoming events.

Image entities are served through HA's authenticated image proxy, so the
photos are not written to www/ (which /local/ serves without a login).
"""

from __future__ import annotations

import logging

from homeassistant.components.image import Image, ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import CONF_NUM_BIRTHDAYS, DEFAULT_NUM_BIRTHDAYS
from .grampsweb_api import GrampsWebError
from .sensor import KINDS, GrampsEntity, kind_device, remove_stale_entities

_LOGGER = logging.getLogger(__name__)

# kind -> (unique_id suffix, media key) per photo of a slot
PHOTOS = {
    "birthdays": (("photo", "media_handle"),),
    "deceased_birthdays": (("photo", "media_handle"),),
    "deathdays": (("photo", "media_handle"),),
    "anniversaries": (("photo_person1", "media_handle_person1"), ("photo_person2", "media_handle_person2")),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one photo entity per person of each event slot."""
    coordinator = entry.runtime_data
    num = entry.data.get(CONF_NUM_BIRTHDAYS, DEFAULT_NUM_BIRTHDAYS)
    photos = [
        GrampsPhoto(coordinator, entry, kind, index, key, media_key)
        for kind, (_, _, option, _) in KINDS.items()
        if option is None or entry.data.get(*option)
        for index in range(num)
        for key, media_key in PHOTOS[kind]
    ]
    remove_stale_entities(hass, entry, "image", photos)
    async_add_entities(photos)


class GrampsPhoto(GrampsEntity, ImageEntity):
    """Thumbnail of the n-th upcoming event's person, fetched with the Gramps login."""

    _attr_content_type = "image/jpeg"  # Gramps Web thumbnails are JPEG

    def __init__(self, coordinator, entry: ConfigEntry, kind: str, index: int, key: str, media_key: str) -> None:
        GrampsEntity.__init__(self, coordinator)
        ImageEntity.__init__(self, coordinator.hass)
        prefix = KINDS[kind][0]
        self._kind, self._index, self._media_key = kind, index, media_key
        self._media: str | None = None
        self._attr_unique_id = f"{entry.entry_id}_{prefix}_{index}_{key}"
        self._attr_name = coordinator.names[f"{prefix}_{key}"].format(n=index + 1)
        self._attr_device_info = kind_device(coordinator, entry, kind)
        self._sync()

    def _sync(self) -> None:
        events = self.coordinator.events(self._kind)
        media = events[self._index].get(self._media_key) if self._index < len(events) else None
        if media != self._media:
            self._media = media
            self._cached_image = None
            self._attr_image_last_updated = dt_util.utcnow() if media else None

    @callback
    def _handle_coordinator_update(self) -> None:
        self._sync()
        super()._handle_coordinator_update()

    async def async_image(self) -> bytes | None:
        if not self._media:
            return None
        if self._cached_image is None:
            try:
                content = await self.hass.async_add_executor_job(self.coordinator.api.get_thumbnail, self._media)
            except GrampsWebError as err:
                _LOGGER.warning("Could not load photo from Gramps Web: %s", err)
                return None
            self._cached_image = Image(self._attr_content_type, content)
        return self._cached_image.content
