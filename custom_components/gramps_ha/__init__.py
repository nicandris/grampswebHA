"""The Gramps HA integration."""

import logging
from datetime import timedelta, datetime, date
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
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

from .const import DOMAIN, CONF_URL, CONF_USERNAME, CONF_PASSWORD, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, CONF_NOTIFY_EVENTS, DEFAULT_NOTIFY_EVENTS, CONF_NOTIFY_MODE, DEFAULT_NOTIFY_MODE, NOTIFY_UNTIL_OVER

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

SCAN_INTERVAL = timedelta(hours=6)

# Notifiable event lists: kind -> (event date key, original date key) in each entry
NOTIFY_KEYS = {
    "birthdays": ("next_birthday", "birth_date"),
    "deceased_birthdays": ("next_birthday", "birth_date"),
    "deathdays": ("next_deathday", "death_date"),
    "anniversaries": ("next_anniversary", "marriage_date"),
}


def _years(event: dict, date_key: str, origin_key: str) -> int | str:
    """Years reached on the event day, from the dates themselves.

    The lists' own age/years fields are computed on the fetch day, so they
    are one short when a fetch before New Year serves an event after it.
    """
    try:
        return int(str(event[date_key])[:4]) - int(str(event[origin_key])[:4])
    except (KeyError, TypeError, ValueError):
        return "?"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Gramps HA from a config entry."""
    _LOGGER.info("Setting up Gramps HA integration")

    try:
        from .grampsweb_api import GrampsWebAPI

        hass.data.setdefault(DOMAIN, {})

        url = entry.data.get(CONF_URL)
        username = entry.data.get(CONF_USERNAME)
        password = entry.data.get(CONF_PASSWORD)

        _LOGGER.debug("Gramps Web URL: %s", url)
        _LOGGER.debug("Username provided: %s", bool(username))

        # Register device in device registry
        device_registry = async_get_device_registry(hass)
        device = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title or "Gramps Web",
            manufacturer="Gramps Web",
            model="Birthday Tracker",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=url,
        )
        _LOGGER.debug("Device registered: %s", device.name)

        api = GrampsWebAPI(
            url=url,
            username=username,
            password=password,
            hass_config_path=hass.config.config_dir,
        )

        # Get scan interval from config (in hours), default to DEFAULT_SCAN_INTERVAL
        scan_interval_hours = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        
        coordinator = GrampsWebCoordinator(hass, api, entry, scan_interval_hours=scan_interval_hours)

        # Try initial refresh, but don't fail if it doesn't work
        try:
            await coordinator.async_config_entry_first_refresh()
            _LOGGER.info("Initial data fetch successful")
        except Exception as refresh_err:
            _LOGGER.warning("Initial data fetch failed (will retry): %s", refresh_err)
            # Don't fail setup, just log the warning

        coordinator.device_id = device.id  # parent of the per-category devices
        hass.data[DOMAIN][entry.entry_id] = coordinator

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

        _LOGGER.info("Gramps HA setup completed successfully")
        return True

    except Exception as err:
        _LOGGER.error("Failed to setup Gramps HA: %s", err, exc_info=True)
        return False


def _dismissed_store(hass: HomeAssistant, entry: ConfigEntry) -> Store:
    return Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.dismissed")


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete the stored dismissals with the entry."""
    await _dismissed_store(hass, entry).async_remove()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    try:
        if unload_ok := await hass.config_entries.async_unload_platforms(
            entry, PLATFORMS
        ):
            hass.data[DOMAIN].pop(entry.entry_id)

        return unload_ok
    except Exception as err:
        _LOGGER.error("Failed to unload Gramps HA: %s", err)
        return False


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
        self.last_birthdays = []  # Track previous list for comparison

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            _LOGGER.debug("Fetching birthday data from Gramps Web")
            data = await self.hass.async_add_executor_job(self.api.get_birthdays)
            _LOGGER.debug("Fetched %s birthdays", len(data) if data else 0)
            
            # Fetch birthdays for people who have passed away.
            deceased_birthdays = await self.hass.async_add_executor_job(
                self.api.get_deceased_birthdays
            )
            self.hass.data.setdefault(f"{DOMAIN}_deceased_birthdays", {})[
                self.entry.entry_id
            ] = deceased_birthdays or []
            _LOGGER.debug(
                "Deceased birthdays fetched: %s entries",
                len(deceased_birthdays) if deceased_birthdays else 0,
            )
            
            # Fetch deathdays if enabled
            notify_events = self.entry.data.get(CONF_NOTIFY_EVENTS, DEFAULT_NOTIFY_EVENTS)
            if self.entry.data.get("show_deathdays", False) or "deathdays" in notify_events:
                deathdays = await self.hass.async_add_executor_job(self.api.get_deathdays)
                self.hass.data.setdefault(f"{DOMAIN}_deathdays", {})[self.entry.entry_id] = deathdays or []
                _LOGGER.debug(
                    "Deathdays fetched: %s entries",
                    len(deathdays) if deathdays else 0,
                )
            else:
                _LOGGER.debug("Deathdays disabled in config; skipping fetch")
            
            # Fetch anniversaries if enabled
            if self.entry.data.get("show_anniversaries", False) or "anniversaries" in notify_events:
                anniversaries = await self.hass.async_add_executor_job(self.api.get_anniversaries)
                self.hass.data.setdefault(f"{DOMAIN}_anniversaries", {})[self.entry.entry_id] = anniversaries or []
                _LOGGER.debug(
                    "Anniversaries fetched: %s entries",
                    len(anniversaries) if anniversaries else 0,
                )
            else:
                _LOGGER.debug("Anniversaries disabled in config; skipping fetch")
            
            # Store current list for next comparison
            self.last_birthdays = data or []
            
            return data
        except Exception as err:
            _LOGGER.error("Error fetching data: %s", err, exc_info=True)
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    def _events(self, kind: str) -> list[dict]:
        if kind == "birthdays":
            return self.data or []
        return self.hass.data.get(f"{DOMAIN}_{kind}", {}).get(self.entry.entry_id) or []

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
        """Notify about tomorrow's events and remove finished notifications.

        Runs at setup and daily just after midnight, on the cached lists:
        they hold absolute dates, so they stay valid between fetches.
        One notification per kind and day, so its id is known in advance.
        """
        kinds = self.entry.data.get(CONF_NOTIFY_EVENTS, DEFAULT_NOTIFY_EVENTS)
        today = dt_util.now().date()
        tomorrow = (today + timedelta(days=1)).isoformat()

        def notification_id(kind: str, day: str) -> str:
            return f"{DOMAIN}_{self.entry.entry_id}_{kind}_{day}"

        if self.entry.data.get(CONF_NOTIFY_MODE, DEFAULT_NOTIFY_MODE) == NOTIFY_UNTIL_OVER:
            yesterday = (today - timedelta(days=1)).isoformat()
            for kind in NOTIFY_KEYS:
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
            date_key, origin_key = NOTIFY_KEYS[kind]
            messages = [
                strings[f"{prefix}.{kind}_message.message"].format(
                    name=event.get("person_name"), years=_years(event, date_key, origin_key)
                )
                for event in self._events(kind)
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
