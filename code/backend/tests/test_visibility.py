"""The pure rule for which resume recruiters see (app/services/visibility.py)."""
from datetime import datetime, timezone

from app.services.visibility import resolve_visible


def _d(day: int) -> datetime:
    return datetime(2026, 11, day, tzinfo=timezone.utc)


def test_chosen_upload_is_visible():
    assert resolve_visible(1, [(1, _d(1)), (2, _d(5))]) == 1


def test_without_a_choice_the_newest_upload_is_visible():
    assert resolve_visible(None, [(1, _d(1)), (2, _d(5)), (3, _d(3))]) == 2


def test_a_deleted_choice_falls_back_to_the_newest():
    assert resolve_visible(9, [(1, _d(1)), (2, _d(5))]) == 2


def test_no_uploads_means_nothing_visible():
    assert resolve_visible(1, []) is None
