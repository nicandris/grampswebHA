"""The Gramps HA integration."""

import logging
from datetime import timedelta, datetime, date
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.device_registry import (
    async_get as async_get_device_registry,
    DeviceEntryType,
    DeviceInfo,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.components import persistent_notification
from homeassistant.helpers.translation import async_get_translations
from homeassistant.util import dt as dt_util

from .grampsweb_api import KINDS, GrampsWebAPI, GrampsWebAuthError, GrampsWebError, upcoming
from .const import DOMAIN, CONF_URL, CONF_USERNAME, CONF_PASSWORD, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, CONF_NOTIFY_EVENTS, DEFAULT_NOTIFY_EVENTS, CONF_NOTIFY_MODE, DEFAULT_NOTIFY_MODE, NOTIFY_UNTIL_OVER

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

# Entries kept per list (the all-birthdays attribute shows this many)
LIST_LIMIT = 50
RETRY_AFTER = 15 * 60  # seconds

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Gramps HA from a config entry."""
    url = entry.data.get(CONF_URL)
    api = GrampsWebAPI(url=url, username=entry.data.get(CONF_USERNAME), password=entry.data.get(CONF_PASSWORD))
    coordinator = GrampsWebCoordinator(
        hass, api, entry, scan_interval_hours=entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    # Raises ConfigEntryNotReady (HA retries) or ConfigEntryAuthFailed (reauth)
    await coordinator.async_config_entry_first_refresh()

    device = async_get_device_registry(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title or "Gramps Web",
        manufacturer="Gramps Web",
        model="Birthday Tracker",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=url,
    )
    coordinator.device_id = device.id  # parent of the per-category devices
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Notifications run daily on the cached lists, not on each (weekly) fetch.
    # Dismissals are stored: HA forgets notifications on restart, and the
    # startup check would otherwise bring a dismissed one back.
    coordinator.dismissed_store = _dismissed_store(hass, entry)
    coordinator.dismissed = set(await coordinator.dismissed_store.async_load() or [])
    entry.async_on_unload(
        persistent_notification.async_register_callback(hass, coordinator.on_notification_update)
    )
    await coordinator.async_notify()
    entry.async_on_unload(
        async_track_time_change(hass, coordinator.async_notify, hour=0, minute=0, second=5)
    )
    return True


def _dismissed_store(hass: HomeAssistant, entry: ConfigEntry) -> Store:
    return Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.dismissed")


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete the stored dismissals with the entry."""
    await _dismissed_store(hass, entry).async_remove()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


class GrampsWebCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Gramps Web data."""

    def __init__(self, hass: HomeAssistant, api, entry: ConfigEntry, scan_interval_hours: int = None) -> None:
        """Initialize."""
        if scan_interval_hours is None:
            scan_interval_hours = DEFAULT_SCAN_INTERVAL
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=scan_interval_hours),
        )
        self.api = api
        self.entry = entry
        self._view_key = None
        self._view: dict[str, list[dict]] = {}

    async def _async_update_data(self):
        """Fetch data from API."""
        today = dt_util.now().date()
        try:
            raw = await self.hass.async_add_executor_job(self.api.fetch, today)
        except GrampsWebAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except GrampsWebError as err:
            # retry soon instead of after the (weekly) update interval
            raise UpdateFailed(f"Error communicating with Gramps Web: {err}", retry_after=RETRY_AFTER) from err
        return raw

    def events(self, kind: str) -> list[dict]:
        """Upcoming events of a kind as of today, soonest first.

        Computed from the fetched dates per day, so days until and order stay
        right between (weekly) fetches.
        """
        key = (id(self.data), dt_util.now().date())
        if self._view_key != key:
            self._view_key, self._view = key, {}
        if kind not in self._view:
            self._view[kind] = upcoming(kind, (self.data or {}).get(kind, []), key[1])[:LIST_LIMIT]
        return self._view[kind]

    @callback
    def on_notification_update(self, update_type, notifications) -> None:
        """Remember which of our notifications were dismissed."""
        if update_type != persistent_notification.UpdateType.REMOVED:
            return
        prefix = f"{DOMAIN}_{self.entry.entry_id}_"
        if new := {nid for nid in notifications if nid.startswith(prefix)} - self.dismissed:
            self.dismissed |= new
            self.dismissed_store.async_delay_save(lambda: sorted(self.dismissed), 1)

    async def async_notify(self, now=None) -> None:
        """Refresh the entities for the new day, notify about tomorrow's events
        and remove finished notifications.

        Runs at setup and daily just after midnight, on the cached lists:
        they hold absolute dates, so they stay valid between fetches.
        One notification per kind and day, so its id is known in advance.
        """
        self.async_update_listeners()
        kinds = self.entry.data.get(CONF_NOTIFY_EVENTS, DEFAULT_NOTIFY_EVENTS)
        today = dt_util.now().date()
        tomorrow = (today + timedelta(days=1)).isoformat()

        def notification_id(kind: str, day: str) -> str:
            return f"{DOMAIN}_{self.entry.entry_id}_{kind}_{day}"

        if self.entry.data.get(CONF_NOTIFY_MODE, DEFAULT_NOTIFY_MODE) == NOTIFY_UNTIL_OVER:
            yesterday = (today - timedelta(days=1)).isoformat()
            for kind in KINDS:
                persistent_notification.async_dismiss(self.hass, notification_id(kind, yesterday))

        # Forget dismissals of events that are over (ids end in the event date).
        if old := {nid for nid in self.dismissed if nid[-10:] < today.isoformat()}:
            self.dismissed -= old
            self.dismissed_store.async_delay_save(lambda: sorted(self.dismissed), 1)

        if not kinds:
            return
        strings = await async_get_translations(
            self.hass, self.hass.config.language, "exceptions", {DOMAIN}
        )
        prefix = f"component.{DOMAIN}.exceptions"

        for kind in kinds:
            _, date_key, years_key = KINDS[kind]
            messages = [
                strings[f"{prefix}.{kind}_message.message"].format(
                    name=event.get("person_name"), years=event.get(years_key)
                )
                for event in self.events(kind)
                if str(event.get(date_key, ""))[:10] == tomorrow
            ]
            if messages and notification_id(kind, tomorrow) not in self.dismissed:
                persistent_notification.async_create(
                    self.hass,
                    "\n\n".join(messages),
                    title=strings[f"{prefix}.{kind}_title.message"],
                    notification_id=notification_id(kind, tomorrow),
                )
                _LOGGER.info("%s tomorrow notification: %s", kind, len(messages))
