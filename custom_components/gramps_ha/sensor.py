"""Sensor platform for Gramps Web integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_NUM_BIRTHDAYS,
    CONF_SHOW_ANNIVERSARIES,
    CONF_SHOW_DEATHDAYS,
    CONF_SHOW_DECEASED_BIRTHDAYS,
    CONF_URL,
    DEFAULT_NUM_BIRTHDAYS,
    DEFAULT_SHOW_ANNIVERSARIES,
    DEFAULT_SHOW_DEATHDAYS,
    DEFAULT_SHOW_DECEASED_BIRTHDAYS,
    DOMAIN,
)

Event = dict[str, Any]


@dataclass(frozen=True, kw_only=True)
class GrampsSensorDescription(SensorEntityDescription):
    """One field of an event slot; key is the unique_id suffix."""

    value_fn: Callable[[Event, str], Any]
    name_key: str | None = None  # translation key suffix, when it differs from key


def _date(key: str) -> Callable[[Event, str], date | None]:
    return lambda event, _: date.fromisoformat(event[key]) if event.get(key) else None


def _field(key: str) -> Callable[[Event, str], Any]:
    return lambda event, _: event.get(key)


def _link(path: str, key: str) -> Callable[[Event, str], str | None]:
    return lambda event, url: f"{url}/{path}/{event[key]}" if event.get(key) else None


def _fields(origin: str, upcoming: str, years: str, years_icon: str, years_unit: str | None,
            name_icon: str, upcoming_icon: str, images: tuple, link: tuple) -> tuple:
    """The sensors of one event slot."""
    return (
        GrampsSensorDescription(key="name", icon=name_icon, value_fn=_field("person_name")),
        GrampsSensorDescription(key=years, icon=years_icon, native_unit_of_measurement=years_unit,
                                value_fn=_field(years)),
        GrampsSensorDescription(key="date", icon="mdi:calendar", device_class=SensorDeviceClass.DATE,
                                value_fn=_date(origin)),
        GrampsSensorDescription(key="upcoming_date", icon=upcoming_icon, device_class=SensorDeviceClass.DATE,
                                value_fn=_date(upcoming)),
        GrampsSensorDescription(key="days_until", icon="mdi:calendar-clock", native_unit_of_measurement="days",
                                value_fn=_field("days_until")),
        *(
            GrampsSensorDescription(key=key, name_key=name_key, icon="mdi:image-outline",
                                    entity_registry_enabled_default=False, value_fn=_field(image_key))
            for key, name_key, image_key in images
        ),
        GrampsSensorDescription(key="link", icon="mdi:link", entity_registry_enabled_default=False,
                                value_fn=_link(*link)),
    )


_BIRTHDAY = _fields("birth_date", "next_birthday", "age", "mdi:numeric", None, "mdi:account", "mdi:cake",
                    (("image", None, "image_url"),), ("person", "person_handle"))

# kind -> (unique_id/translation prefix, device model, enabling option, fields)
KINDS: dict[str, tuple[str, str, tuple[str, bool] | None, tuple]] = {
    "birthdays": ("birthday", "Birthdays", None, _BIRTHDAY),
    "deceased_birthdays": (
        "deceased_birthday", "Deceased Birthdays", (CONF_SHOW_DECEASED_BIRTHDAYS, DEFAULT_SHOW_DECEASED_BIRTHDAYS), _BIRTHDAY,
    ),
    "deathdays": (
        "deathday", "Deathdays", (CONF_SHOW_DEATHDAYS, DEFAULT_SHOW_DEATHDAYS),
        _fields("death_date", "next_deathday", "years_ago", "mdi:history", None, "mdi:skull", "mdi:skull",
                (("image", None, "image_url"),), ("person", "person_handle")),
    ),
    "anniversaries": (
        "anniversary", "Anniversaries", (CONF_SHOW_ANNIVERSARIES, DEFAULT_SHOW_ANNIVERSARIES),
        _fields("marriage_date", "next_anniversary", "years_together", "mdi:numeric", "years",
                "mdi:heart-multiple", "mdi:heart",
                (("image_person1", "image_person_1", "image_url_person1"),
                 ("image_person2", "image_person_2", "image_url_person2")),
                ("family", "family_handle")),
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gramps Web sensors from a config entry."""
    coordinator = entry.runtime_data

    num = entry.data.get(CONF_NUM_BIRTHDAYS, DEFAULT_NUM_BIRTHDAYS)
    sensors: list[SensorEntity] = [
        GrampsEventSensor(coordinator, entry, kind, index, description)
        for kind, (_, _, option, fields) in KINDS.items()
        if option is None or entry.data.get(*option)
        for index in range(num)
        for description in fields
    ]
    sensors.append(GrampsWebAllBirthdaysSensor(coordinator, entry))
    remove_stale_entities(hass, entry, "sensor", sensors)
    async_add_entities(sensors)


def remove_stale_entities(hass: HomeAssistant, entry: ConfigEntry, domain: str, entities: list) -> None:
    """Drop registry entries of slots or kinds that the settings no longer create."""
    registry = er.async_get(hass)
    current = {entity.unique_id for entity in entities}
    for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if registry_entry.domain == domain and registry_entry.unique_id not in current:
            registry.async_remove(registry_entry.entity_id)


def kind_device(coordinator, entry: ConfigEntry, kind: str) -> DeviceInfo:
    """The device that groups one kind's entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{kind}")},
        name=coordinator.names[kind],
        manufacturer="Gramps Web",
        model=KINDS[kind][1],
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=entry.data.get(CONF_URL),
        via_device_id=coordinator.device_id,
    )


class GrampsEntity(CoordinatorEntity):
    """Keeps showing the last fetched data while Gramps Web is unreachable.

    The lists hold absolute dates, so they stay valid between fetches.
    """

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None


class GrampsEventSensor(GrampsEntity, SensorEntity):
    """One field of the n-th upcoming event of a kind."""

    entity_description: GrampsSensorDescription

    def __init__(self, coordinator, entry: ConfigEntry, kind: str, index: int,
                 description: GrampsSensorDescription) -> None:
        super().__init__(coordinator)
        prefix = KINDS[kind][0]
        self.entity_description = description
        self._kind = kind
        self._index = index
        self._base_url = entry.data.get(CONF_URL, "").rstrip("/")
        self._attr_unique_id = f"{entry.entry_id}_{prefix}_{index}_{description.key}"
        self._attr_name = coordinator.names[f"{prefix}_{description.name_key or description.key}"].format(n=index + 1)
        self._attr_device_info = kind_device(coordinator, entry, kind)

    def _event(self) -> Event | None:
        events = self.coordinator.events(self._kind)
        return events[self._index] if self._index < len(events) else None

    @property
    def native_value(self):
        event = self._event()
        return self.entity_description.value_fn(event, self._base_url) if event else None

    @property
    def extra_state_attributes(self):
        if self._kind not in ("birthdays", "deceased_birthdays"):
            return None
        event = self._event()
        if not event:
            return {}
        return {
            key: event.get(key)
            for key in ("person_name", "birth_date", "age", "days_until", "next_birthday", "image_url")
        }


class GrampsWebAllBirthdaysSensor(GrampsEntity, SensorEntity):
    """Representation of all upcoming birthdays sensor."""

    _attr_icon = "mdi:calendar-multiple"
    # Names and birth dates of up to 50 living people: every HA user can read
    # states, so this is opt-in for new installs and kept out of the history DB.
    _attr_entity_registry_enabled_default = False
    _unrecorded_attributes = frozenset({"birthdays"})

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = coordinator.names["all_birthdays"]
        self._attr_unique_id = f"{entry.entry_id}_all_birthdays"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title or "Gramps HA",
            manufacturer="Gramps Web",
            model="Birthdays",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=entry.data.get(CONF_URL),
        )

    @property
    def native_value(self):
        return len(self.coordinator.events("birthdays"))

    @property
    def extra_state_attributes(self):
        return {"birthdays": self.coordinator.events("birthdays")}
