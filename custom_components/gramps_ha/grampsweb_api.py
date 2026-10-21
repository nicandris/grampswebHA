"""Gramps Web API client and the date logic built on its data.

The client is synchronous (requests) and runs in HA's executor. `fetch()`
returns events with their original dates only; `upcoming()` turns them into
next occurrences for a given day, so days and years stay right between fetches.
"""

from __future__ import annotations

import logging
from datetime import date

import requests

_LOGGER = logging.getLogger(__name__)

# Gramps Date fields (gramps/gen/lib/date.py): dateval is (day, month, year, slash, ...)
MOD_NONE = 0
CAL_GREGORIAN = 0
QUAL_NONE = 0
# sortval is a Julian day number; date.fromordinal(1) is JDN 1721426
JDN_OFFSET = 1721425

# Gramps' default for "probably alive" (Preferences > Dates)
MAX_AGE_PROBABLY_ALIVE = 110

DEATH_TYPES = {"Death", "Burial", "Cremation"}
END_OF_MARRIAGE_TYPES = {"Divorce", "Annulment"}

# kind -> (original date key, next date key, years key)
KINDS = {
    "birthdays": ("birth_date", "next_birthday", "age"),
    "deceased_birthdays": ("birth_date", "next_birthday", "age"),
    "deathdays": ("death_date", "next_deathday", "years_ago"),
    "anniversaries": ("marriage_date", "next_anniversary", "years_together"),
}


class GrampsWebError(Exception):
    """Gramps Web could not be reached or returned an error."""


class GrampsWebAuthError(GrampsWebError):
    """Gramps Web rejected the credentials."""


def parse_date(value) -> date | None:
    """Return the exact calendar date of a Gramps Date dict, else None.

    About/before/after/ranges, estimated or calculated dates and dates
    without a day or month are not exact, so they yield None.
    """
    if not isinstance(value, dict):
        return None
    if value.get("modifier", MOD_NONE) != MOD_NONE or value.get("quality", QUAL_NONE) != QUAL_NONE:
        return None
    dateval = value.get("dateval") or []
    if len(dateval) < 3 or not all(isinstance(v, int) for v in dateval[:3]):
        return None
    day, month, year = dateval[:3]
    if not day or not month or not year:
        return None
    try:
        if value.get("calendar", CAL_GREGORIAN) != CAL_GREGORIAN:
            # dateval is in another calendar; sortval is its Gregorian day
            return date.fromordinal(int(value["sortval"]) - JDN_OFFSET)
        return date(year, month, day)
    except (KeyError, TypeError, ValueError):
        return None


def _on_year(origin: date, year: int) -> date:
    """origin's day and month in year; 29 Feb falls on 28 Feb in common years."""
    try:
        return origin.replace(year=year)
    except ValueError:
        return origin.replace(year=year, day=28)


def next_occurrence(origin: date, today: date) -> date:
    """The first anniversary of origin on or after today."""
    this_year = _on_year(origin, today.year)
    return this_year if this_year >= today else _on_year(origin, today.year + 1)


def upcoming(kind: str, entries: list[dict], today: date) -> list[dict]:
    """Entries with next date, days until and years on that day, soonest first."""
    origin_key, next_key, years_key = KINDS[kind]
    result = []
    for entry in entries:
        origin = date.fromisoformat(entry[origin_key])
        nxt = next_occurrence(origin, today)
        result.append(
            {
                **entry,
                next_key: nxt.isoformat(),
                "days_until": (nxt - today).days,
                years_key: nxt.year - origin.year,
            }
        )
    result.sort(key=lambda item: (item["days_until"], item.get("person_name", "")))
    return result


def _type(obj: dict) -> str:
    value = obj.get("type", "")
    return value.get("string", "") if isinstance(value, dict) else str(value or "")


def person_name(person: dict) -> str:
    """First name and primary surname."""
    primary = person.get("primary_name") or {}
    surnames = primary.get("surname_list") or [{}]
    name = f"{primary.get('first_name', '')} {surnames[0].get('surname', '')}".strip()
    return name or "Unknown"


def _media_handle(obj: dict) -> str | None:
    media = obj.get("media_list") or []
    return media[0].get("ref") if media else None


class GrampsWebAPI:
    """Talks to one Gramps Web instance."""

    def __init__(self, url: str, username: str | None = None, password: str | None = None) -> None:
        self.url = url.strip().rstrip("/")
        self.username = username
        self.password = password
        self.token: str | None = None
        self._session = requests.Session()

    def _authenticate(self) -> None:
        self._session.headers.pop("Authorization", None)
        self.token = None
        if not self.username:
            return
        try:
            response = self._session.post(
                f"{self.url}/api/token/",
                json={"username": self.username, "password": self.password},
                timeout=10,
            )
        except requests.RequestException as err:
            raise GrampsWebError(f"Cannot reach Gramps Web: {err}") from err
        if response.status_code in (401, 403):
            raise GrampsWebAuthError("Gramps Web rejected the username or password")
        if not response.ok:
            raise GrampsWebError(f"Gramps Web login failed: HTTP {response.status_code}")
        token = response.json().get("access_token")
        if not token:
            raise GrampsWebAuthError("Gramps Web returned no access token")
        self.token = token
        self._session.headers["Authorization"] = f"Bearer {token}"

    def _request(self, path: str, params: dict | None = None, timeout: int = 60) -> requests.Response:
        """GET path, logging in first and once more if the token expired."""
        if self.username and not self.token:
            self._authenticate()
        url = f"{self.url}/api/{path.lstrip('/')}"
        try:
            response = self._session.get(url, params=params, timeout=timeout)
            if response.status_code == 401 and self.username:
                self._authenticate()
                response = self._session.get(url, params=params, timeout=timeout)
        except requests.RequestException as err:
            raise GrampsWebError(f"Cannot reach Gramps Web: {err}") from err
        if response.status_code in (401, 403):
            raise GrampsWebAuthError(f"Gramps Web denied access to {path}")
        if not response.ok:
            raise GrampsWebError(f"Gramps Web returned HTTP {response.status_code} for {path}")
        return response

    def _get(self, path: str, params: dict | None = None):
        try:
            return self._request(path, params).json()
        except ValueError as err:
            raise GrampsWebError(f"Gramps Web returned invalid JSON for {path}") from err

    def test_connection(self) -> None:
        """Raise GrampsWebAuthError/GrampsWebError unless the tree can be read."""
        self._get("people/", {"page": 1, "pagesize": 1})

    def get_thumbnail(self, media_handle: str) -> bytes:
        """A person's photo thumbnail."""
        return self._request(f"media/{media_handle}/thumbnail/200", timeout=10).content

    def thumbnail_url(self, media_handle: str | None) -> str | None:
        """Gramps Web URL of a thumbnail (needs a Gramps login to open)."""
        return f"{self.url}/api/media/{media_handle}/thumbnail/200" if media_handle else None

    def fetch(self, today: date) -> dict[str, list[dict]]:
        """All events with their original dates, per kind.

        Three requests per refresh: list endpoints return every object when no
        page is given, so nothing is fetched per person.
        """
        # ponytail: whole tree per refresh; page or use `dates=` filters if trees get huge
        people = self._get("people/")
        events = self._get("events/")
        families = self._get("families/")
        if not all(isinstance(items, list) for items in (people, events, families)):
            raise GrampsWebError("Unexpected response from Gramps Web")
        events = {event.get("handle"): event for event in events}

        def ref_event(person: dict, index_key: str, types: set[str]) -> dict | None:
            refs = person.get("event_ref_list") or []
            index = person.get(index_key, -1)
            if 0 <= index < len(refs):
                return events.get(refs[index].get("ref"))
            for ref in refs:  # no index set: a Primary event of that type
                event = events.get(ref.get("ref"))
                if event and ref.get("role", "Primary") == "Primary" and _type(event) in types:
                    return event
            return None

        result: dict[str, list[dict]] = {kind: [] for kind in KINDS}
        info: dict[str, dict] = {}
        for person in people:
            handle = person.get("handle")
            birth_event = ref_event(person, "birth_ref_index", {"Birth"})
            death_event = ref_event(person, "death_ref_index", DEATH_TYPES)
            birth = parse_date(birth_event.get("date")) if birth_event else None
            death = parse_date(death_event.get("date")) if death_event else None
            deceased = bool(death_event) or bool(
                birth and today.year - birth.year > MAX_AGE_PROBABLY_ALIVE
            )
            media = _media_handle(person)
            base = {
                "person_name": person_name(person),
                "person_handle": handle,
                "media_handle": media,
                "image_url": self.thumbnail_url(media),
            }
            info[handle] = {**base, "deceased": deceased}
            if birth:
                kind = "deceased_birthdays" if deceased else "birthdays"
                result[kind].append({**base, "birth_date": birth.isoformat()})
            if death and _type(death_event) == "Death":
                result["deathdays"].append({**base, "death_date": death.isoformat()})

        for family in families:
            partners = [info[h] for h in (family.get("father_handle"), family.get("mother_handle")) if h in info]
            family_events = [events.get(ref.get("ref")) for ref in family.get("event_ref_list") or []]
            family_events = [event for event in family_events if event]
            if not partners or any(partner["deceased"] for partner in partners):
                continue
            if any(_type(event) in END_OF_MARRIAGE_TYPES for event in family_events):
                continue
            marriage = next(
                (
                    parsed
                    for event in family_events
                    if _type(event) == "Marriage" and (parsed := parse_date(event.get("date")))
                ),
                None,
            )
            if not marriage:
                continue
            entry = {
                "person_name": " & ".join(partner["person_name"] for partner in partners),
                "marriage_date": marriage.isoformat(),
                "family_handle": family.get("handle"),
            }
            # names and photos in the same (father, mother) order
            for number, partner in enumerate(partners, 1):
                entry[f"media_handle_person{number}"] = partner["media_handle"]
                entry[f"image_url_person{number}"] = partner["image_url"]
            result["anniversaries"].append(entry)

        _LOGGER.debug("Fetched %s", {kind: len(items) for kind, items in result.items()})
        return result
