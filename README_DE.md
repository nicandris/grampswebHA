# Gramps HA Integration für Home Assistant

> **Experimenteller Fork** von [greewoo/grampswebHA](https://github.com/greewoo/grampswebHA), ursprünglich [EdgarM73/grampswebHA](https://github.com/EdgarM73/grampswebHA).

Diese Custom Integration ermöglicht es, Daten von einer Gramps Web Instanz in Home Assistant zu integrieren und anstehende Geburtstage auf dem Dashboard anzuzeigen.
Ich kam darauf, da ich grampsweb bisher zwar nutze, aber erst jetzt gesehen habe, dass es grampsweb auch als addon gibt : https://github.com/alexbelgium/hassio-addons/tree/master , danke dafür.

und wenn man schon einen Stammbaum hat, kann man auch die Familien Geburtstage anzeigen.

!Achtung !  Der größte Teil dieser Integration ist KI generiert, sonst hätte ich aktuell gar nicht die Zeit gehabt.



## Features

- 🎂 Zeigt die nächsten 6 (konfigurierbar) Geburtstage an
- 📅 Tage bis zum Ereignis, täglich heruntergezählt (auch zwischen den Abrufen)
- 🎉 Zeigt das Alter der Person am kommenden Geburtstag
- 🧩 Pro Geburtstag 7 Sensoren: Name, Alter, Datum, Nächstes Datum, Tage verbleibend, Bild, Link
- 🖼️ Profilbilder aus Gramps Web als Bild-Entitäten, hinter der Home-Assistant-Anmeldung
- 🔗 Direkt-Links zu Personen und Familien in Gramps Web
- 🔄 Ruft standardmäßig einmal pro Woche neue Daten ab (einstellbar)
- 🕯️ Geburtstage verstorbener Personen (abschaltbar)
- 🪦 **Optional:** die nächsten Gedenktage/Todestage
- 💍 **Optional:** die nächsten Hochzeitstage (mit Fotos beider Partner und Link zur Familie)
- 🔔 Benachrichtigung am Vortag
- 🌍 Mehrsprachig: Deutsch, Englisch, Französisch, Italienisch, Bosnisch

Es zählen nur genaue Daten: Daten mit *um*, *vor*, *nach*, Zeiträume sowie geschätzte oder berechnete Daten werden übersprungen. Geburtstage am 29. Februar fallen in Nicht-Schaltjahren auf den 28. Februar. Personen ohne erfassten Tod, die über 110 wären, gelten als verstorben.

## Installation

### HACS (empfohlen)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=nicandris&repository=grampswebHA&category=Integration)

1. Öffnen Sie HACS in Home Assistant
2. Klicken Sie auf die drei Punkte (⋮) oben rechts
3. Wählen Sie **Benutzerdefinierte Repositorys**
4. Fügen Sie die Repository-URL hinzu: `https://github.com/nicandris/grampswebHA`
5. Wählen Sie Kategorie: **Integration**
6. Klicken Sie auf **Hinzufügen**
7. Suchen Sie nach "Gramps HA" und installieren Sie es
8. Starten Sie Home Assistant neu

### Manuelle Installation

1. Laden Sie die neueste Version von [GitHub](https://github.com/nicandris/grampswebHA) herunter
2. Entpacken Sie das Archiv
3. Kopieren Sie den Ordner `custom_components/gramps_ha` in Ihr `<config>/custom_components/` Verzeichnis
4. Starten Sie Home Assistant neu

#### Oder via Git:

```bash
cd /config/custom_components
git clone https://github.com/nicandris/grampswebHA.git temp
mv temp/custom_components/gramps_ha ./
rm -rf temp
```

## Konfiguration

1. Gehen Sie zu **Einstellungen** → **Geräte & Dienste**
2. Klicken Sie auf **+ Integration hinzufügen**
3. Suchen Sie nach "Gramps HA"
4. Geben Sie folgende Informationen ein:
   - **URL**: Die URL Ihrer Gramps Web Instanz (z.B. `https://my-gramps.example.com`). Unverschlüsseltes `http://` wird nur für lokale Adressen akzeptiert, weil es das Passwort im Klartext sendet.
   - **Benutzername** und **Passwort** (Pflicht): ein Gramps-Web-Benutzer. Ein Nur-Lese-Konto mit der Rolle Member genügt. Die Anmeldung wird bei der Einrichtung geprüft.
   - **Anzahl Geburtstage**: (Standard: 6) Anzahl der Geburtstage/Todestage/Hochzeitstage mit eigenen Sensoren
   - **Geburtstage Verstorbener anzeigen**: (Standard: Ja)
   - **Gedenktage anzeigen**: (Standard: Nein) Zeigt die nächsten Todestage/Gedenktage an
   - **Hochzeitstage anzeigen**: (Standard: Nein) Zeigt die nächsten Hochzeitstage an
   - **Aktualisierungsintervall (Stunden)**: (Standard: 168, einmal pro Woche) Wie oft Daten aus Gramps Web geholt werden. Ein fehlgeschlagener Abruf wird nach 15 Minuten wiederholt.
   - **Entitätsnamen**: (Standard: Englisch) Englisch oder die in Home Assistant eingestellte Sprache. Eine Änderung benennt Sensoren und Geräte um; Entitäts-IDs bleiben gleich.

Um die Einstellungen später zu ändern, öffnen Sie die Integration und wählen Sie im ⋮-Menü **Neu konfigurieren** (Passwort leer lassen, um es zu behalten). Lehnt Gramps Web die gespeicherte Anmeldung ab, fordert Home Assistant zur erneuten Anmeldung auf.

## Sensoren

Für jeden Platz (1 bis zur eingestellten Anzahl) wird ein Satz Sensoren angelegt, auch wenn es weniger Ereignisse gibt; Sensoren ohne Daten sind `unknown`. Die Entitäts-IDs unten gelten für eine englische Einrichtung; `X` ist die Nummer des Platzes.

### Nächste Geburtstage

1. **Name** (`sensor.birthdays_next_birthday_X_name`) - Name der Person; die Attribute enthalten Alter, verbleibende Tage, Daten und Bild-URL
2. **Alter** (`sensor.birthdays_next_birthday_X_age`) - Alter am nächsten Geburtstag
3. **Datum** (`sensor.birthdays_next_birthday_X_date`) - Geburtsdatum (Datumtyp)
4. **Nächstes Datum** (`sensor.birthdays_next_birthday_X_upcoming_date`) - Datum des nächsten Geburtstags (Datumtyp)
5. **Tage verbleibend** (`sensor.birthdays_next_birthday_X_days_until`) - Tage bis zum Geburtstag, `0` am Tag selbst
6. **Bild** (`sensor.birthdays_next_birthday_X_image`) - Gramps-Web-URL des Profilbilds (öffnen erfordert eine Gramps-Anmeldung); das Entitätsbild ist das Foto der passenden Bild-Entität
7. **Link** (`sensor.birthdays_next_birthday_X_link`) - Link zur Person in Gramps Web

`sensor.gramps_ha_all_upcoming_birthdays` zählt die anstehenden Geburtstage; das Attribut `birthdays` listet bis zu 50 davon.

### Geburtstage Verstorbener

Dieselben 7 Sensoren mit dem Präfix `sensor.deceased_birthdays_next_deceased_birthday_X_`, für Personen mit erfasstem Tod (oder über 110). In den Einstellungen abschaltbar.

### Nächste Gedenktage (optional aktivierbar)

Wenn "Gedenktage anzeigen" aktiviert ist, 7 Sensoren pro Platz:

1. **Name** (`sensor.deathdays_next_deathday_X_name`) - Name der verstorbenen Person
2. **Datum** (`sensor.deathdays_next_deathday_X_date`) - Todesdatum (Datumtyp)
3. **Nächstes Datum** (`sensor.deathdays_next_deathday_X_upcoming_date`) - Datum des nächsten Gedenktags (Datumtyp)
4. **Jahre her** (`sensor.deathdays_next_deathday_X_years_ago`) - Jahre seit dem Tod, an diesem Tag
5. **Tage verbleibend** (`sensor.deathdays_next_deathday_X_days_until`) - Tage bis zum Gedenktag
6. **Bild** (`sensor.deathdays_next_deathday_X_image`) - Gramps-Web-URL des Profilbilds
7. **Link** (`sensor.deathdays_next_deathday_X_link`) - Link zur Person in Gramps Web

### Nächste Hochzeitstage (optional aktivierbar)

Wenn "Hochzeitstage anzeigen" aktiviert ist, 8 Sensoren pro Platz. Nur *Hochzeit*-Ereignisse zählen; Paare mit *Scheidung* oder *Annullierung* oder mit einem verstorbenen Partner werden ausgelassen.

1. **Name** (`sensor.anniversaries_next_anniversary_X_name`) - Namen der Ehepartner
2. **Jahre zusammen** (`sensor.anniversaries_next_anniversary_X_years_together`) - Ehejahre, an diesem Tag
3. **Datum** (`sensor.anniversaries_next_anniversary_X_date`) - Hochzeitsdatum (Datumtyp)
4. **Nächstes Datum** (`sensor.anniversaries_next_anniversary_X_upcoming_date`) - Datum des nächsten Jahrestags (Datumtyp)
5. **Tage verbleibend** (`sensor.anniversaries_next_anniversary_X_days_until`) - Tage bis zum nächsten Jahrestag
6. **Bild Person 1** (`sensor.anniversaries_next_anniversary_X_image_person_1`) - Bild-URL des zuerst genannten Partners
7. **Bild Person 2** (`sensor.anniversaries_next_anniversary_X_image_person_2`) - Bild-URL des zweiten Partners
8. **Link** (`sensor.anniversaries_next_anniversary_X_link`) - Link zur Familie in Gramps Web

### Fotos

Jeder Platz hat außerdem eine Bild-Entität mit dem Foto der Person, z.B. `image.birthdays_next_birthday_X_photo`, `image.deathdays_next_deathday_X_photo` und `image.anniversaries_next_anniversary_X_photo_person_1` / `_photo_person_2`. Sie eignen sich für Bild-Karten. Die Fotos werden mit der Gramps-Anmeldung geladen und über die Home-Assistant-Anmeldung ausgeliefert; sie werden nicht mehr in `www/` gespeichert (ältere Versionen taten das, diese Dateien werden bei der Einrichtung gelöscht).

**Standardmäßig deaktiviert (Neuinstallationen):** die Bild- und Link-Sensoren sowie `sensor.gramps_ha_all_upcoming_birthdays`. Bei Bedarf unter "Einstellungen → Geräte & Dienste → Entitäten" aktivieren.

### Datenschutz

Jeder Home-Assistant-Benutzer kann Entitätszustände und Benachrichtigungen lesen; Home Assistant kennt dafür keine Rechte pro Benutzer. Die Sensoren zeigen Namen und Daten aus Ihrem Stammbaum, richten Sie die Integration also nur ein, wo alle Benutzer sie sehen dürfen. Das Attribut `birthdays` des Sensors aller Geburtstage wird nicht in die Verlaufsdatenbank geschrieben.

## Benachrichtigungen

Am Vortag eines Ereignisses zeigt die Integration eine Home-Assistant-Benachrichtigung (in der Sprache von Home Assistant). Zwei Einstellungen, später auch über **Neu konfigurieren** änderbar:

- **Benachrichtigung am Vortag**: Geburtstage, Geburtstage Verstorbener, Gedenktage und/oder Hochzeitstage. Standard: Geburtstage. Leer lassen, um Benachrichtigungen auszuschalten.
- **Dauer der Benachrichtigung**: *Bis geschlossen* (Standard) oder *Bis der Tag vorbei ist*; dann wird sie nach dem Ereignistag automatisch entfernt.

Die Prüfung läuft täglich kurz nach Mitternacht, unabhängig vom Aktualisierungsintervall. Ereignisse am selben Tag teilen sich eine Benachrichtigung.

## Dashboard Konfiguration

Beispiel-Vorlagen (Grid und Markdown) mit den neuen, getrennten Sensoren finden Sie in [EXAMPLES.md](EXAMPLES.md).

### Custom Button Card (erfordert custom:button-card)

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
    return `In ${days} Tagen wird ${age} Jahre alt`;
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

Diese Integration nutzt die Gramps Web API. Stellen Sie sicher, dass:

1. Ihre Gramps Web Instanz erreichbar ist
2. Die API aktiviert ist
3. Bei Bedarf die Authentifizierung korrekt konfiguriert ist

## Fehlerbehebung

### Verbindungsfehler

- Überprüfen Sie die URL Ihrer Gramps Web Instanz
- Stellen Sie sicher, dass Home Assistant die Instanz erreichen kann
- Prüfen Sie Benutzername und Passwort

### Keine Geburtstage werden angezeigt

- Stellen Sie sicher, dass in Ihrer Gramps-Datenbank Geburtsdaten vorhanden sind
- Überprüfen Sie die Logs in Home Assistant (`Einstellungen` → `System` → `Protokolle`)

### Logs aktivieren

Fügen Sie dies zu Ihrer `configuration.yaml` hinzu:

```yaml
logger:
  default: info
  logs:
    custom_components.gramps_ha: debug
```

## Entwicklung

Diese Integration befindet sich in aktiver Entwicklung. Beiträge sind willkommen!

### Geplante Features

- [x] Konfigurierbare Anzahl von Geburtstagen
- [x] Todestage und Gedenktage mit Bildern und Links
- [x] Hochzeitstage mit Bildern beider Partner und Links
- [x] Direkt-Links zu Personen/Familien in Gramps Web
- [x] Mehrsprachigkeit (DE, EN, FR, IT, BS)
- [ ] Filterung nach Altersgruppen
- [x] Benachrichtigungen für anstehende Geburtstage
- [ ] Unterstützung für mehrere Gramps Web Instanzen

## Lizenz

MIT License

## Support

Bei Problemen oder Fragen erstellen Sie bitte ein Issue auf GitHub.

---

🇩🇪 Deutsche Version | [🇬🇧 English Version](README.md)
