# test_validation.py
# Tests for the checks in validation.py.
# Each check should return None for good values and a message for bad ones.

from datetime import date, timedelta

import validation


def test_check_name():
    assert validation.check_name("Jane Doe") is None
    assert validation.check_name("") == "Please enter your name."
    assert validation.check_name("x" * 51) is not None


def test_check_alias():
    assert validation.check_alias("janedoe") is None
    assert validation.check_alias("jd") is not None          # too short
    assert validation.check_alias("JaneDoe") is not None     # capitals
    assert validation.check_alias("jane.doe") is not None    # symbol


def test_check_password():
    assert validation.check_password("Secret123", "Secret123") is None
    assert validation.check_password("Sec1", "Sec1") is not None                  # too short
    assert validation.check_password("secretpass", "secretpass") is not None      # no number
    assert validation.check_password("Secret123", "Secret124") == "The two passwords do not match."


def test_check_asset_tag():
    assert validation.check_asset_tag("LR-0011") is None
    assert validation.check_asset_tag("LR-12") is not None
    assert validation.check_asset_tag("AB-0011") is not None
    assert validation.check_asset_tag("LR-00AB") is not None


def test_check_model_name():
    assert validation.check_model_name("Xbox One") is None
    assert validation.check_model_name("") is not None
    assert validation.check_model_name("x" * 51) is not None


def test_check_desk_location():
    assert validation.check_desk_location("Desk 4.12") is None
    assert validation.check_desk_location("") is not None
    assert validation.check_desk_location("x" * 21) is not None


def test_check_due_date():
    tomorrow = str(date.today() + timedelta(days=1))
    yesterday = str(date.today() - timedelta(days=1))
    assert validation.check_due_date(tomorrow) is None
    assert validation.check_due_date(str(date.today())) is None
    assert validation.check_due_date(yesterday) == "The due date cannot be in the past."
    assert validation.check_due_date("2026-02-30") is not None   # not a real date
    assert validation.check_due_date("") is not None
