# Changelog

Newest changes first. This is an experimental fork of
[greewoo/grampswebHA](https://github.com/greewoo/grampswebHA), originally
[EdgarM73/grampswebHA](https://github.com/EdgarM73/grampswebHA).

## 2026.10.2

- Notifications are configurable in setup and **Reconfigure**:
  - **Notify the day before:** birthdays, birthdays of the deceased, deathdays and/or
    anniversaries. Default: birthdays. Leave empty to turn notifications off.
  - **Notification lifetime:** until dismissed (default), or until the event day is over.
- Fixed: the "tomorrow" check only ran when data was fetched, by default once a week, so
  most events never got a notification. It now runs daily just after midnight.
- Fixed: years in a notification are counted to the event day, so an event just after New
  Year no longer shows one year short.
- Events on the same day share one notification.
- Tests run in CI.

## 2026.10.1

- New setup option **Entity names**: English (default, the names used so far) or the language
  Home Assistant is set to.
- **Reconfigure** in the integration's ⋮ menu changes the settings without removing it.
- The "birthday tomorrow" notification follows Home Assistant's language instead of always
  German (English, German, French, Italian, Bosnian).
- Fixed: the notification age was one year too high.
- Fixed: birthdays on the 29th–31st of a month were never announced.
- Fixed: the French, Italian and Bosnian translation files could not be loaded.
- Requires Home Assistant 2026.8.0 (device links use `via_device_id`, the old form stops
  working in 2027.8).
- Brand icon, setup field descriptions, masked password field.
- Repository: CI (hassfest, HACS validation), releases on version bump, Dependabot, license.

Non-English texts are AI-translated.
