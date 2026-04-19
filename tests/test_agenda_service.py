"""
Tests unitaires du service agenda.

Couvrent :
  - create_event (succes)
  - get_event (succes + 404)
  - list_events (tous / par date / par semaine)
  - update_event (partiel + 404)
  - delete_event (succes + 404)
"""
from datetime import date, timedelta

import pytest

from src.models.schemas import EventCreate, EventUpdate
from src.services import agenda_service
from src.services.agenda_service import EventNotFoundError


def _sample_payload(**overrides) -> EventCreate:
    """Helper : payload EventCreate avec valeurs par defaut."""
    base = {
        "title": "Reunion test",
        "date": "2026-04-20",
        "time": "10:00",
        "participants": "Alice, Bob",
        "notes": "Notes de test",
    }
    base.update(overrides)
    return EventCreate(**base)


# --- create_event -------------------------------------------
def test_create_event_returns_event_with_id(db):
    event = agenda_service.create_event(db, _sample_payload())
    assert event.id is not None
    assert event.title == "Reunion test"
    assert event.date == "2026-04-20"
    assert event.created_at is not None


# --- get_event ----------------------------------------------
def test_get_event_returns_event_when_exists(db):
    created = agenda_service.create_event(db, _sample_payload())
    fetched = agenda_service.get_event(db, created.id)
    assert fetched.id == created.id
    assert fetched.title == "Reunion test"


def test_get_event_raises_when_not_found(db):
    with pytest.raises(EventNotFoundError) as exc_info:
        agenda_service.get_event(db, 9999)
    assert exc_info.value.event_id == 9999


# --- list_events --------------------------------------------
def test_list_events_empty_by_default(db):
    assert agenda_service.list_events(db) == []


def test_list_events_returns_all_sorted_by_date_and_time(db):
    agenda_service.create_event(db, _sample_payload(date="2026-04-22", time="14:00"))
    agenda_service.create_event(db, _sample_payload(date="2026-04-20", time="09:00"))
    agenda_service.create_event(db, _sample_payload(date="2026-04-20", time="14:00"))

    events = agenda_service.list_events(db)
    assert len(events) == 3
    # Tri : date croissante puis heure croissante
    assert events[0].date == "2026-04-20" and events[0].time == "09:00"
    assert events[1].date == "2026-04-20" and events[1].time == "14:00"
    assert events[2].date == "2026-04-22"


def test_list_events_with_date_filter_returns_matching_only(db):
    agenda_service.create_event(db, _sample_payload(date="2026-04-20"))
    agenda_service.create_event(db, _sample_payload(date="2026-04-21"))

    filtered = agenda_service.list_events(db, date_filter="2026-04-21")
    assert len(filtered) == 1
    assert filtered[0].date == "2026-04-21"


def test_list_events_with_range_week_returns_seven_days(db):
    today = date.today()
    # Dans la plage
    agenda_service.create_event(
        db, _sample_payload(date=today.isoformat(), title="Aujourd'hui")
    )
    agenda_service.create_event(
        db, _sample_payload(date=(today + timedelta(days=3)).isoformat(), title="J+3")
    )
    # Hors plage
    agenda_service.create_event(
        db, _sample_payload(date=(today + timedelta(days=30)).isoformat(), title="J+30")
    )

    events = agenda_service.list_events(db, range_filter="week")
    titles = [e.title for e in events]
    assert "Aujourd'hui" in titles
    assert "J+3" in titles
    assert "J+30" not in titles


def test_list_events_date_filter_has_priority_over_range(db):
    agenda_service.create_event(db, _sample_payload(date="2026-04-20"))
    # date_filter est prioritaire sur range_filter
    events = agenda_service.list_events(
        db, date_filter="2026-04-20", range_filter="week"
    )
    assert len(events) == 1
    assert events[0].date == "2026-04-20"


# --- update_event -------------------------------------------
def test_update_event_applies_only_provided_fields(db):
    created = agenda_service.create_event(db, _sample_payload())
    updated = agenda_service.update_event(
        db, created.id, EventUpdate(time="15:30")
    )
    assert updated.time == "15:30"
    # Les autres champs sont preserves
    assert updated.title == "Reunion test"
    assert updated.date == "2026-04-20"


def test_update_event_raises_when_not_found(db):
    with pytest.raises(EventNotFoundError):
        agenda_service.update_event(db, 9999, EventUpdate(time="15:00"))


# --- delete_event -------------------------------------------
def test_delete_event_removes_it(db):
    created = agenda_service.create_event(db, _sample_payload())
    agenda_service.delete_event(db, created.id)
    with pytest.raises(EventNotFoundError):
        agenda_service.get_event(db, created.id)


def test_delete_event_raises_when_not_found(db):
    with pytest.raises(EventNotFoundError):
        agenda_service.delete_event(db, 9999)
