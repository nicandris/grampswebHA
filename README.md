# Gramps HA Integration for Home Assistant

> **Experimental fork** of [greewoo/grampswebHA](https://github.com/greewoo/grampswebHA), originally [EdgarM73/grampswebHA](https://github.com/EdgarM73/grampswebHA).

This custom integration allows you to integrate data from a Gramps Web instance into Home Assistant and display upcoming birthdays on your dashboard.

I came up with this because I've been using Gramps Web for a while, but only recently discovered that Gramps Web is also available as an add-on: https://github.com/alexbelgium/hassio-addons/tree/master - thank you for that!

And if you already have a family tree, you might as well display family birthdays.

**Note:** Most of this integration is AI-generated, otherwise I wouldn't have had the time to create it.

## Features

- 🎂 Displays the next 6 (configurable) birthdays
- 📅 Days until each event, counted down daily (also between data fetches)
- 🎉 Shows the person's age on their upcoming birthday
- 🧩 7 sensors per birthday: Name, Age, Date, Upcoming Date, Days Until, Image, Link
- 🖼️ Profile photos from Gramps Web as image entities, behind Home Assistant's login
- 🔗 Direct links to persons and families in Gramps Web
- 🔄 Fetches new data once a week by default (configurable)
- 🕯️ Birthdays of deceased people (can be turned off)
- 🪦 **Optional:** upcoming memorial dates/death anniversaries
- 💍 **Optional:** upcoming wedding anniversaries (with photos of both partners and a family link)
- 🔔 Notifications the day before an event
- 🌍 Multilingual: German, English, French, Italian, Bosnian

Only exact dates are used: dates marked *about*, *before*, *after*, ranges and estimated or calculated dates are skipped. Birthdays on 29 February fall on 28 February in common years. People without a recorded death who would be over 110 count as deceased.

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Click on the three dots (⋮) in the top right
3. Select **Custom repositories**
4. Add the repository URL: `https://github.com/nicandris/grampswebHA`
5. Select category: **Integration**
6. Click **Add**
7. Search for "Gramps HA" and install it
8. Restart Home Assistant

### Manual Installation

1. Download the latest version from [GitHub](https://github.com/nicandris/grampswebHA)
2. Extract the archive
3. Copy the `custom_components/gramps_ha` folder to your `<config>/custom_components/` directory
4. Restart Home Assistant

#### Or via Git:

```bash
cd /config/custom_components
git clone https://github.com/nicandris/grampswebHA.git temp
mv temp/custom_components/gramps_ha ./
rm -rf temp
```

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Gramps HA"
4. Enter the following information:
   - **URL**: The URL of your Gramps Web instance (e.g., `https://my-gramps.example.com`). Plain `http://` is only accepted for local addresses, because it sends the password unencrypted.
   - **Username** and **Password** (required): a Gramps Web user. A read-only account with the Member role is enough. Setup checks the login.
   - **Number of Birthdays**: (default: 6) Number of birthdays/deathdays/anniversaries that get their own sensors
   - **Show birthdays of the deceased**: (default: Yes)
   - **Show Deathdays**: (default: No) Show upcoming memorial/death dates
   - **Show Anniversaries**: (default: No) Show upcoming wedding anniversaries
   - **Update interval (hours)**: (default: 168, once a week) How often data is fetched from Gramps Web. A failed fetch is retried after 15 minutes.
   - **Entity names**: (default: English) English, or the language Home Assistant is set to. Changing it renames sensors and devices; entity IDs stay the same.

To change these settings later, open the integration and choose **Reconfigure** from its ⋮ menu (leave the password empty to keep it). If Gramps Web rejects the stored login, Home Assistant asks you to log in again.

## Sensors

For each slot (1 up to the configured number) a set of sensors is created, even if fewer events exist; sensors without data are `unknown`. Entity IDs below are for an English setup; `X` is the slot number.

### Next Birthdays

1. **Name** (`sensor.birthdays_next_birthday_X_name`) - Person's name; its attributes hold age, days until, dates and image URL
2. **Age** (`sensor.birthdays_next_birthday_X_age`) - Age on next birthday
3. **Date** (`sensor.birthdays_next_birthday_X_date`) - Birth date (Date type)
4. **Upcoming Date** (`sensor.birthdays_next_birthday_X_upcoming_date`) - Date of next birthday (Date type)
5. **Days Until** (`sensor.birthdays_next_birthday_X_days_until`) - Days until birthday, `0` on the day
6. **Image** (`sensor.birthdays_next_birthday_X_image`) - Gramps Web URL of the profile picture (needs a Gramps login to open)
7. **Link** (`sensor.birthdays_next_birthday_X_link`) - Link to the person in Gramps Web

`sensor.gramps_ha_all_upcoming_birthdays` counts the upcoming birthdays; its `birthdays` attribute lists up to 50 of them.

### Birthdays of the deceased

The same 7 sensors with the prefix `sensor.deceased_birthdays_next_deceased_birthday_X_`, for people with a recorded death (or over 110). Can be turned off in the settings.

### Next Deathdays/Memorial Dates (optional)

If "Show Deathdays" is enabled, 7 sensors per slot:

1. **Name** (`sensor.deathdays_next_deathday_X_name`) - Name of deceased person
2. **Date** (`sensor.deathdays_next_deathday_X_date`) - Death date (Date type)
3. **Upcoming Date** (`sensor.deathdays_next_deathday_X_upcoming_date`) - Date of next memorial (Date type)
4. **Years Ago** (`sensor.deathdays_next_deathday_X_years_ago`) - Years since the death, on that day
5. **Days Until** (`sensor.deathdays_next_deathday_X_days_until`) - Days until annual memorial
6. **Image** (`sensor.deathdays_next_deathday_X_image`) - Gramps Web URL of the profile picture
7. **Link** (`sensor.deathdays_next_deathday_X_link`) - Link to the person in Gramps Web

### Next Wedding Anniversaries (optional)

If "Show Anniversaries" is enabled, 8 sensors per slot. Only *Marriage* events count; couples with a *Divorce* or *Annulment* event, or with a deceased partner, are left out.

1. **Name** (`sensor.anniversaries_next_anniversary_X_name`) - Names of the spouses
2. **Years Together** (`sensor.anniversaries_next_anniversary_X_years_together`) - Years married, on that day
3. **Date** (`sensor.anniversaries_next_anniversary_X_date`) - Marriage date (Date type)
4. **Upcoming Date** (`sensor.anniversaries_next_anniversary_X_upcoming_date`) - Date of next anniversary (Date type)
5. **Days Until** (`sensor.anniversaries_next_anniversary_X_days_until`) - Days until next anniversary
6. **Image Person 1** (`sensor.anniversaries_next_anniversary_X_image_person_1`) - Picture URL of the first named spouse
7. **Image Person 2** (`sensor.anniversaries_next_anniversary_X_image_person_2`) - Picture URL of the second named spouse
8. **Link** (`sensor.anniversaries_next_anniversary_X_link`) - Link to the family in Gramps Web

### Photos

Each slot also has an image entity with the person's photo, e.g. `image.birthdays_next_birthday_X_photo`, `image.deathdays_next_deathday_X_photo` and `image.anniversaries_next_anniversary_X_photo_person_1` / `_photo_person_2`. Use them in picture cards. Photos are loaded with the Gramps login and served through Home Assistant's login; they are no longer saved to `www/` (older versions did, and those files are deleted on setup).

**Disabled by default (new installs):** the Image and Link sensors and `sensor.gramps_ha_all_upcoming_birthdays`. Enable them under "Settings → Devices & Services → Entities" if needed.

### Privacy

Every Home Assistant user can read entity states and notifications; Home Assistant has no per-user permissions for them. The sensors show names and dates of your family tree, so only add this integration where all users may see them. The `birthdays` attribute of the all-birthdays sensor is not written to the history database.

## Notifications

The day before an event, the integration shows a Home Assistant notification (in the language Home Assistant is set to). Two settings, also changeable later via **Reconfigure**:

- **Notify the day before**: birthdays, birthdays of the deceased, deathdays and/or anniversaries. Default: birthdays. Leave it empty to turn notifications off.
- **Notification lifetime**: *Until dismissed* (default), or *Until the day is over*, which removes it automatically after the event day.

The check runs daily just after midnight, independent of the update interval. Events on the same day share one notification.

## Dashboard Configuration

Example templates (Grid and Markdown) with the new separate sensors can be found in [EXAMPLES.md](EXAMPLES.md).

### Custom Button Card (requires custom:button-card)

```yaml
type: custom:button-card
entity: sensor.birthdays_next_birthday_1_name
name: |
  [[[
    return states['sensor.birthdays_next_birthday_1_name'].state;
  ]]]
label: |
  [[[
    const days = states['sensor.birthdays_next_birthday_1_name'].attributes.days_until;
    const age = states['sensor.birthdays_next_birthday_1_name'].attributes.age;
    return `In ${days} days turns ${age} years old`;
  ]]]
show_label: true
icon: mdi:cake-variant
styles:
  card:
    - background: |
        [[[
          const days = states['sensor.birthdays_next_birthday_1_name'].attributes.days_until;
          if (days <= 7) return 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
          return 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)';
        ]]]
```

## Gramps Web API

This integration uses the Gramps Web API. Make sure that:

1. Your Gramps Web instance is reachable
2. The API is enabled
3. Authentication is configured correctly if needed

## Troubleshooting

### Connection Errors

- Check the URL of your Gramps Web instance
- Make sure Home Assistant can reach the instance
- Verify username and password

### No Birthdays Displayed

- Ensure that birth dates are present in your Gramps database
- Check the logs in Home Assistant (`Settings` → `System` → `Logs`)

### Enable Logs

Add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.gramps_ha: debug
```

## Development

This integration is under active development. Contributions are welcome!

### Planned Features

- [x] Configurable number of birthdays
- [x] Death anniversaries and memorial dates with images and links
- [x] Wedding anniversaries with images of both partners and links
- [x] Direct links to persons/families in Gramps Web
- [x] Multilingual support (DE, EN, FR, IT, BS)
- [ ] Age group filtering
- [x] Notifications for upcoming birthdays
- [ ] Support for multiple Gramps Web instances

## License

MIT License

## Support

For issues or questions, please create an issue on GitHub.

---

[🇩🇪 Deutsche Version](README_DE.md) | 🇬🇧 English Version
