"""Date logic and error handling of the Gramps Web client (no HA needed)."""
from datetime import date

import pytest
import requests

from custom_components.gramps_ha.grampsweb_api import (
    GrampsWebAPI,
    GrampsWebAuthError,
    GrampsWebError,
    next_occurrence,
    parse_date,
    upcoming,
)

URL = "https://gramps.example"
TODAY = date(2026, 10, 21)


def gdate(day, month, year, modifier=0, quality=0, calendar=0, sortval=0):
    return {"dateval": [day, month, year, False], "modifier": modifier, "quality": quality,
            "calendar": calendar, "sortval": sortval}


# --- parse_date -------------------------------------------------------------

def test_parse_exact_date():
    assert parse_date(gdate(15, 1, 1990)) == date(1990, 1, 15)


@pytest.mark.parametrize("modifier", [1, 2, 3, 4, 5, 6, 7, 8])  # before, after, about, range, span, text, from, to
def test_inexact_modifiers_are_not_dates(modifier):
    assert parse_date(gdate(15, 1, 1990, modifier=modifier)) is None


@pytest.mark.parametrize("quality", [1, 2])  # estimated, calculated
def test_estimated_or_calculated_are_not_dates(quality):
    assert parse_date(gdate(15, 1, 1990, quality=quality)) is None


@pytest.mark.parametrize("dateval", [[0, 1, 1990], [15, 0, 1990], [0, 0, 1990], [31, 2, 1990], []])
def test_incomplete_or_invalid_dates(dateval):
    assert parse_date({"dateval": dateval, "modifier": 0, "quality": 0, "calendar": 0}) is None


def test_julian_calendar_uses_gregorian_sortval():
    # 1 Jan 1700 Julian is 12 Jan 1700 Gregorian, JDN 2341984
    assert parse_date(gdate(1, 1, 1700, calendar=1, sortval=2341984)) == date(1700, 1, 12)


def test_non_dict_is_not_a_date():
    assert parse_date(None) is None
    assert parse_date([15, 1, 1990]) is None


# --- next_occurrence / upcoming --------------------------------------------

def test_feb_29_in_a_common_year_is_feb_28():
    assert next_occurrence(date(2000, 2, 29), date(2027, 1, 10)) == date(2027, 2, 28)


def test_feb_29_in_a_leap_year_stays():
    assert next_occurrence(date(2000, 2, 29), date(2028, 1, 10)) == date(2028, 2, 29)


def test_feb_29_after_feb_28_of_a_common_year_goes_to_next_year():
    assert next_occurrence(date(2000, 2, 29), date(2027, 3, 1)) == date(2028, 2, 29)


def test_today_is_zero_days_until():
    (entry,) = upcoming("birthdays", [{"person_name": "A", "birth_date": "1990-10-21"}], TODAY)
    assert entry["days_until"] == 0 and entry["next_birthday"] == "2026-10-21" and entry["age"] == 36


def test_yesterday_is_next_year():
    (entry,) = upcoming("birthdays", [{"person_name": "A", "birth_date": "1990-10-20"}], TODAY)
    assert entry["next_birthday"] == "2027-10-20" and entry["days_until"] == 364 and entry["age"] == 37


def test_anniversary_next_year_counts_years_to_that_day():
    (entry,) = upcoming("anniversaries", [{"person_name": "A & B", "marriage_date": "2000-01-05"}], TODAY)
    assert entry["next_anniversary"] == "2027-01-05" and entry["years_together"] == 27


def test_deathday_years_ago_counted_to_the_day():
    (entry,) = upcoming("deathdays", [{"person_name": "A", "death_date": "2000-03-01"}], TODAY)
    assert entry["years_ago"] == 27


def test_sorted_soonest_first():
    entries = [{"person_name": n, "birth_date": d} for n, d in [("late", "1990-10-20"), ("soon", "1990-10-22")]]
    assert [e["person_name"] for e in upcoming("birthdays", entries, TODAY)] == ["soon", "late"]


# --- fetch ------------------------------------------------------------------

def person(handle, first, birth=None, death=None, media=None, extra_events=()):
    refs, events = [], []
    for kind, value in (("Birth", birth), ("Death", death), *extra_events):
        if value is not None:
            refs.append({"ref": f"{handle}-{kind}", "role": "Primary"})
            events.append({"handle": f"{handle}-{kind}", "type": kind, "date": value})
    names = [r["ref"].split("-")[1] for r in refs]
    return ({"handle": handle, "primary_name": {"first_name": first, "surname_list": [{"surname": "X"}]},
             "event_ref_list": refs,
             "birth_ref_index": names.index("Birth") if "Birth" in names else -1,
             "death_ref_index": names.index("Death") if "Death" in names else -1,
             "media_list": [{"ref": media}] if media else []}, events)


def family(handle, father, mother, *events):
    return ({"handle": handle, "father_handle": father, "mother_handle": mother,
             "event_ref_list": [{"ref": e["handle"]} for e in events]}, list(events))


def event(handle, kind, value):
    return {"handle": handle, "type": kind, "date": value}


def serve(requests_mock, people, families):
    events = [e for _, evs in people + families for e in evs]
    requests_mock.post(f"{URL}/api/token/", json={"access_token": "t"})
    requests_mock.get(f"{URL}/api/people/", json=[p for p, _ in people])
    requests_mock.get(f"{URL}/api/events/", json=events)
    requests_mock.get(f"{URL}/api/families/", json=[f for f, _ in families])
    return GrampsWebAPI(URL, "u", "p")


def test_fetch_sorts_people_into_kinds(requests_mock):
    people = [
        person("p1", "Living", birth=gdate(1, 2, 1990)),
        person("p2", "Dead", birth=gdate(1, 3, 1930), death=gdate(5, 6, 2000)),
        person("p3", "Old", birth=gdate(1, 4, 1850)),  # no death recorded, 176 years old
        person("p4", "Buried", birth=gdate(1, 5, 1950), extra_events=[("Burial", gdate(1, 1, 2001))]),
        person("p5", "About", birth=gdate(1, 6, 1990, modifier=3)),
    ]
    data = serve(requests_mock, people, []).fetch(TODAY)
    assert [e["person_name"] for e in data["birthdays"]] == ["Living X"]
    assert sorted(e["person_name"] for e in data["deceased_birthdays"]) == ["Buried X", "Dead X", "Old X"]
    assert [(e["person_name"], e["death_date"]) for e in data["deathdays"]] == [("Dead X", "2000-06-05")]
    assert requests_mock.call_count == 4  # token + 3 lists, nothing per person


def test_fetch_anniversaries_use_family_partners(requests_mock):
    people = [person("f", "Father", media="mf"), person("m", "Mother", media="mm"),
              person("w", "Widow"), person("d", "Dead", death=gdate(1, 1, 2010)),
              person("a", "Ex"), person("b", "Ex2")]
    families = [
        family("F1", "f", "m", event("e1", "Marriage", gdate(10, 5, 2000)), event("e1b", "Marriage Banns", gdate(1, 4, 2000))),
        family("F2", "w", "d", event("e2", "Marriage", gdate(10, 5, 1990))),
        family("F3", "a", "b", event("e3", "Marriage", gdate(10, 5, 1980)), event("e4", "Divorce", gdate(1, 1, 1990))),
        family("F4", "a", "w", event("e5", "Engagement", gdate(1, 1, 2020))),
    ]
    (entry,) = serve(requests_mock, people, families).fetch(TODAY)["anniversaries"]
    assert entry["person_name"] == "Father X & Mother X"
    assert entry["marriage_date"] == "2000-05-10" and entry["family_handle"] == "F1"
    assert entry["image_url_person1"].endswith("/media/mf/thumbnail/200")
    assert entry["image_url_person2"].endswith("/media/mm/thumbnail/200")


# --- errors propagate --------------------------------------------------------

def test_wrong_password_raises_auth_error(requests_mock):
    requests_mock.post(f"{URL}/api/token/", status_code=403)
    with pytest.raises(GrampsWebAuthError):
        GrampsWebAPI(URL, "u", "bad").fetch(TODAY)


def test_expired_token_is_refreshed_once(requests_mock):
    requests_mock.post(f"{URL}/api/token/", json={"access_token": "t"})
    requests_mock.get(f"{URL}/api/people/", [{"status_code": 401}, {"json": []}])
    api = GrampsWebAPI(URL, "u", "p")
    api.token = "old"
    api.test_connection()
    assert requests_mock.call_count == 3


def test_still_401_after_refresh_is_auth_error(requests_mock):
    requests_mock.post(f"{URL}/api/token/", json={"access_token": "t"})
    requests_mock.get(f"{URL}/api/people/", status_code=401)
    with pytest.raises(GrampsWebAuthError):
        GrampsWebAPI(URL, "u", "p").test_connection()


@pytest.mark.parametrize("kwargs", [{"status_code": 500}, {"exc": requests.ConnectionError}, {"text": "not json"}])
def test_server_errors_raise(requests_mock, kwargs):
    requests_mock.post(f"{URL}/api/token/", json={"access_token": "t"})
    requests_mock.get(f"{URL}/api/people/", **kwargs)
    with pytest.raises(GrampsWebError) as err:
        GrampsWebAPI(URL, "u", "p").fetch(TODAY)
    assert not isinstance(err.value, GrampsWebAuthError)
