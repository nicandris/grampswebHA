# Changelog

Newest changes first. This is an experimental fork of
[greewoo/grampswebHA](https://github.com/greewoo/grampswebHA), originally
[EdgarM73/grampswebHA](https://github.com/EdgarM73/grampswebHA).

## 2026.10.4

Fixes from a code review. **Read before updating:**

- **Photos:** photos are image entities now (e.g. `image.birthdays_next_birthday_1_photo`).
  They used to be saved to `www/gramps`, which Home Assistant serves to anyone without a
  login; those files are deleted on setup. The image sensors keep their IDs and their entity
  picture, which now comes from the matching image entity (Home Assistant's login-protected
  image proxy), so cards that show the sensor's picture keep working. The sensor's *state* is
  now the Gramps Web URL, which needs a Gramps login: cards that used the state as an image
  URL should use the entity picture or the image entities.
- **Empty slots** are `unknown` instead of `Keine Daten` / `999`. Update automations that
  compared with those values.
- **New installs:** Image and Link sensors and the all-birthdays sensor are disabled by
  default. Existing entities keep their setting, IDs and history.

Changes:

- Fixed: birthdays on 29 February made the person disappear in common years; they now fall
  on 28 February.
- Fixed: "days until" and the order only changed when data was fetched (weekly by default),
  so `days_until == 0` never happened. They now update just after midnight, in Home
  Assistant's time zone.
- Fixed: deathday and anniversary sensors stayed empty when there were no living birthdays.
- Fixed: years together/years ago were one short for events after New Year.
- Fixed: anniversaries counted Banns, Licence and Engagement as weddings, missed the spouse
  (wrong Gramps field), and continued after a divorce or a partner's death; photos could be
  in a different order than the names.
- Fixed: dates marked about/before/after, ranges and estimated dates were shown as exact;
  other calendars are converted. People over 110 without a recorded death no longer get
  birthdays.
- An outage now retries setup (and a failed fetch after 15 minutes) instead of showing empty
  sensors for a week; a rejected password asks you to log in again (reauthentication).
  Setup checks the login and refuses the same instance and user twice.
- Reconfigure no longer shows the stored password; leave it empty to keep it. Plain
  `http://` is only accepted for local addresses.
- New option: turn the deceased-birthdays sensors off.
- Lowering the number of slots or turning a kind off removes the entities it no longer uses.
- The all-birthdays list is not written to the history database.
- Fetching uses 3 requests instead of several per person.
- Removed logging of personal data and of one hard-coded person.
- Removed debug scripts from the repository root that contained credentials; CI actions
  are pinned to commit SHAs with read-only permissions.
- README: correct entity IDs, defaults and required fields.

## 2026.10.3

- Fixed: a dismissed notification came back after every Home Assistant restart on the day
  before the event. Dismissals are now stored and survive restarts; a notification you did
  not dismiss still shows again after a restart.

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
