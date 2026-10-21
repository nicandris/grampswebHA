"""Constants for the Gramps HA integration."""

DOMAIN = "gramps_ha"
DEFAULT_NAME = "Gramps HA"

CONF_URL = "url"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_NUM_BIRTHDAYS = "num_birthdays"
CONF_SHOW_DEATHDAYS = "show_deathdays"
CONF_SHOW_ANNIVERSARIES = "show_anniversaries"
CONF_SHOW_DECEASED_BIRTHDAYS = "show_deceased_birthdays"
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_NUM_BIRTHDAYS = 6
DEFAULT_SHOW_DEATHDAYS = False
DEFAULT_SHOW_ANNIVERSARIES = False
DEFAULT_SHOW_DECEASED_BIRTHDAYS = True
DEFAULT_SCAN_INTERVAL = 7 * 24  # 7 days in hours
CONF_ENTITY_LANGUAGE = "entity_language"
ENTITY_LANGUAGE_EN = "en"
ENTITY_LANGUAGE_HA = "ha"
DEFAULT_ENTITY_LANGUAGE = ENTITY_LANGUAGE_EN
CONF_NOTIFY_EVENTS = "notify_events"
NOTIFY_EVENTS = ["birthdays", "deceased_birthdays", "deathdays", "anniversaries"]
DEFAULT_NOTIFY_EVENTS = ["birthdays"]
CONF_NOTIFY_MODE = "notify_mode"
NOTIFY_UNTIL_DISMISSED = "until_dismissed"
NOTIFY_UNTIL_OVER = "until_over"
DEFAULT_NOTIFY_MODE = NOTIFY_UNTIL_DISMISSED

ATTR_PERSON_NAME = "person_name"
ATTR_BIRTH_DATE = "birth_date"
ATTR_AGE = "age"
ATTR_DAYS_UNTIL = "days_until"
