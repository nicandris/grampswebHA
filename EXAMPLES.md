# Gramps Web Home Assistant Integration - Beispielkonfigurationen

## Lovelace Dashboard Beispiele

### Grid-Layout: 6 Geburtstage (Name/Alter/Datum getrennt)

```yaml
type: grid
title: Nächste 6 Geburtstage
columns: 2
square: false
cards:
  - type: entities
    title: 1
    entities:
      - entity: sensor.birthdays_next_birthday_1_name
        name: Name
      - entity: sensor.birthdays_next_birthday_1_age
        name: Alter
      - entity: sensor.birthdays_next_birthday_1_date
        name: Datum
  - type: entities
    title: 2
    entities:
      - entity: sensor.birthdays_next_birthday_2_name
        name: Name
      - entity: sensor.birthdays_next_birthday_2_age
        name: Alter
      - entity: sensor.birthdays_next_birthday_2_date
        name: Datum
  - type: entities
    title: 3
    entities:
      - entity: sensor.birthdays_next_birthday_3_name
        name: Name
      - entity: sensor.birthdays_next_birthday_3_age
        name: Alter
      - entity: sensor.birthdays_next_birthday_3_date
        name: Datum
  - type: entities
    title: 4
    entities:
      - entity: sensor.birthdays_next_birthday_4_name
        name: Name
      - entity: sensor.birthdays_next_birthday_4_age
        name: Alter
      - entity: sensor.birthdays_next_birthday_4_date
        name: Datum
  - type: entities
    title: 5
    entities:
      - entity: sensor.birthdays_next_birthday_5_name
        name: Name
      - entity: sensor.birthdays_next_birthday_5_age
        name: Alter
      - entity: sensor.birthdays_next_birthday_5_date
        name: Datum
  - type: entities
    title: 6
    entities:
      - entity: sensor.birthdays_next_birthday_6_name
        name: Name
      - entity: sensor.birthdays_next_birthday_6_age
        name: Alter
      - entity: sensor.birthdays_next_birthday_6_date
        name: Datum
```

### Markdown-Liste: kompakt mit Name/Alter/Datum

```yaml
type: markdown
title: Geburtstage (kommend)
content: |
  {% set items = [
    (states('sensor.birthdays_next_birthday_1_name'), states('sensor.birthdays_next_birthday_1_age'), states('sensor.birthdays_next_birthday_1_date')),
    (states('sensor.birthdays_next_birthday_2_name'), states('sensor.birthdays_next_birthday_2_age'), states('sensor.birthdays_next_birthday_2_date')),
    (states('sensor.birthdays_next_birthday_3_name'), states('sensor.birthdays_next_birthday_3_age'), states('sensor.birthdays_next_birthday_3_date')),
    (states('sensor.birthdays_next_birthday_4_name'), states('sensor.birthdays_next_birthday_4_age'), states('sensor.birthdays_next_birthday_4_date')),
    (states('sensor.birthdays_next_birthday_5_name'), states('sensor.birthdays_next_birthday_5_age'), states('sensor.birthdays_next_birthday_5_date')),
    (states('sensor.birthdays_next_birthday_6_name'), states('sensor.birthdays_next_birthday_6_age'), states('sensor.birthdays_next_birthday_6_date'))
  ] %}
  {% for n, a, d in items if n not in ['unknown','unavailable',''] %}
  - **{{ n }}** — {{ d }}{% if a not in ['unknown','unavailable',''] %} ({{ a }} Jahre){% endif %}
  {% endfor %}
```

### 1. Einfache Liste mit Entities Card

```yaml
type: entities
title: Kommende Geburtstage
entities:
  - sensor.birthdays_next_birthday_1_name
  - sensor.birthdays_next_birthday_2_name
  - sensor.birthdays_next_birthday_3_name
  - sensor.birthdays_next_birthday_4_name
  - sensor.birthdays_next_birthday_5_name
show_header_toggle: false
```

### 2. Detaillierte Ansicht mit Template

```yaml
type: markdown
title: 🎂 Geburtstage
content: |
  {% set ns = namespace(found=false) %}
  {% for i in range(1, 6) %}
    {% set entity_id = 'sensor.birthdays_next_birthday_' ~ i ~ '_name' %}
    {% if states(entity_id) not in ['unknown', 'unavailable', 'none'] %}
      {% set ns.found = true %}
      <ha-icon icon="mdi:cake-variant"></ha-icon> **{{ states(entity_id) }}**
      - 🎈 Wird {{ state_attr(entity_id, 'age') }} Jahre alt
      - 📅 {{ state_attr(entity_id, 'next_birthday') }}
      - ⏰ In {{ state_attr(entity_id, 'days_until') }} Tagen
      
    {% endif %}
  {% endfor %}
  {% if not ns.found %}
  Keine anstehenden Geburtstage gefunden.
  {% endif %}
```

### 3. Kompakte Tabellenansicht

```yaml
type: markdown
content: |
  | Name | Alter | Datum | Tage |
  |------|-------|-------|------|
  {% for i in range(1, 6) %}
  {% set e = 'sensor.birthdays_next_birthday_' ~ i ~ '_name' %}
  {% if states(e) not in ['unknown', 'unavailable'] %}
  | {{ states(e) }} | {{ state_attr(e, 'age') }} | {{ state_attr(e, 'next_birthday') }} | {{ state_attr(e, 'days_until') }} |
  {% endif %}
  {% endfor %}
```

### 4. Conditional Card - Nur anzeigen wenn Geburtstag in 7 Tagen

```yaml
type: conditional
conditions:
  - entity: sensor.birthdays_next_birthday_1_name
    state_not: unavailable
  - entity: sensor.birthdays_next_birthday_1_name
    attribute: days_until
    below: 8
card:
  type: markdown
  content: |
    # ⚠️ Geburtstag bald!
    **{{ states('sensor.birthdays_next_birthday_1_name') }}** wird in {{ state_attr('sensor.birthdays_next_birthday_1_name', 'days_until') }} Tagen {{ state_attr('sensor.birthdays_next_birthday_1_name', 'age') }} Jahre alt! 🎉
```

### 5. Glance Card für schnelle Übersicht

```yaml
type: glance
title: Nächste 5 Geburtstage
entities:
  - entity: sensor.birthdays_next_birthday_1_name
    name: 1.
  - entity: sensor.birthdays_next_birthday_2_name
    name: 2.
  - entity: sensor.birthdays_next_birthday_3_name
    name: 3.
  - entity: sensor.birthdays_next_birthday_4_name
    name: 4.
  - entity: sensor.birthdays_next_birthday_5_name
    name: 5.
show_name: true
show_icon: true
show_state: true
```

## Automatisierungen

### Benachrichtigung 7 Tage vor Geburtstag

```yaml
automation:
  - alias: "Geburtstag in 7 Tagen Erinnerung"
    trigger:
      - platform: time
        at: "09:00:00"
    condition:
      - condition: template
        value_template: >
          {% set ns = namespace(found=false) %}
          {% for i in range(1, 6) %}
            {% set entity_id = 'sensor.birthdays_next_birthday_' ~ i ~ '_name' %}
            {% if state_attr(entity_id, 'days_until') == 7 %}
              {% set ns.found = true %}
            {% endif %}
          {% endfor %}
          {{ ns.found }}
    action:
      - service: notify.notify
        data:
          title: "Geburtstag in 7 Tagen"
          message: >
            {% for i in range(1, 6) %}
              {% set entity_id = 'sensor.birthdays_next_birthday_' ~ i ~ '_name' %}
              {% if state_attr(entity_id, 'days_until') == 7 %}
                {{ states(entity_id) }} wird in 7 Tagen {{ state_attr(entity_id, 'age') }} Jahre alt!
              {% endif %}
            {% endfor %}
```

### Benachrichtigung am Geburtstag

```yaml
automation:
  - alias: "Geburtstag heute!"
    trigger:
      - platform: time
        at: "08:00:00"
    condition:
      - condition: template
        value_template: >
          {% set ns = namespace(found=false) %}
          {% for i in range(1, 6) %}
            {% set entity_id = 'sensor.birthdays_next_birthday_' ~ i ~ '_name' %}
            {% if state_attr(entity_id, 'days_until') == 0 %}
              {% set ns.found = true %}
            {% endif %}
          {% endfor %}
          {{ ns.found }}
    action:
      - service: notify.notify
        data:
          title: "🎉 Geburtstag heute!"
          message: >
            {% for i in range(1, 6) %}
              {% set entity_id = 'sensor.birthdays_next_birthday_' ~ i ~ '_name' %}
              {% if state_attr(entity_id, 'days_until') == 0 %}
                Heute wird {{ states(entity_id) }} {{ state_attr(entity_id, 'age') }} Jahre alt! 🎂
              {% endif %}
            {% endfor %}
```

## Template Sensoren

### Anzahl Geburtstage in den nächsten 30 Tagen

```yaml
template:
  - sensor:
      - name: "Geburtstage nächste 30 Tage"
        state: >
          {% set ns = namespace(count=0) %}
          {% for i in range(1, 6) %}
            {% set entity_id = 'sensor.birthdays_next_birthday_' ~ i ~ '_name' %}
            {% if state_attr(entity_id, 'days_until') is not none and state_attr(entity_id, 'days_until') <= 30 %}
              {% set ns.count = ns.count + 1 %}
            {% endif %}
          {% endfor %}
          {{ ns.count }}
        icon: mdi:calendar-clock
```

### Nächster Geburtstag als einzelner Sensor

```yaml
template:
  - sensor:
      - name: "Nächster Geburtstag"
        state: >
          {{ states('sensor.birthdays_next_birthday_1_name') }}
        attributes:
          person: >
            {{ states('sensor.birthdays_next_birthday_1_name') }}
          days: >
            {{ state_attr('sensor.birthdays_next_birthday_1_name', 'days_until') }}
          age: >
            {{ state_attr('sensor.birthdays_next_birthday_1_name', 'age') }}
          date: >
            {{ state_attr('sensor.birthdays_next_birthday_1_name', 'next_birthday') }}
        icon: mdi:cake-variant
```

## Scripts

### Script zum Versenden einer Geburtstagserinnerung

```yaml
script:
  send_birthday_reminder:
    alias: "Geburtstagserinnerung versenden"
    sequence:
      - service: notify.mobile_app
        data:
          title: "Anstehende Geburtstage"
          message: |
            {% for i in range(1, 6) %}
              {% set e = 'sensor.birthdays_next_birthday_' ~ i ~ '_name' %}
              {% if states(e) not in ['unknown', 'unavailable'] and state_attr(e, 'days_until') <= 14 %}
                • {{ states(e) }} - in {{ state_attr(e, 'days_until') }} Tagen ({{ state_attr(e, 'age') }} Jahre)
              {% endif %}
            {% endfor %}
```

## Node-RED Flow Beispiel

```json
[
    {
        "id": "birthday_notification",
        "type": "server-state-changed",
        "name": "Geburtstag Check",
        "server": "home_assistant",
        "version": 4,
        "entityidfilter": "sensor.birthdays_next_birthday_1_name",
        "entityidfiltertype": "exact",
        "outputinitially": false,
        "state_type": "str",
        "ifstate": "",
        "isstateconfig": "",
        "outputonlystatechange": true,
        "for": "0",
        "forType": "num",
        "forUnits": "minutes",
        "x": 150,
        "y": 100,
        "wires": [["check_days"]]
    },
    {
        "id": "check_days",
        "type": "function",
        "name": "Prüfe Tage bis Geburtstag",
        "func": "const daysUntil = msg.data.attributes.days_until;\nif (daysUntil <= 7) {\n    msg.payload = `${msg.data.state} wird in ${daysUntil} Tagen ${msg.data.attributes.age} Jahre alt!`;\n    return msg;\n}\nreturn null;",
        "outputs": 1,
        "x": 400,
        "y": 100,
        "wires": [["send_notification"]]
    },
    {
        "id": "send_notification",
        "type": "api-call-service",
        "name": "Benachrichtigung senden",
        "server": "home_assistant",
        "version": 5,
        "service_domain": "notify",
        "service": "notify",
        "data": "{\"message\":\"{{payload}}\",\"title\":\"Geburtstag bald!\"}",
        "x": 650,
        "y": 100,
        "wires": [[]]
    }
]
```
