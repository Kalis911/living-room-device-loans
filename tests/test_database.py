# test_database.py
# Tests for the functions in database.py

import sqlite3
from datetime import date, timedelta

import pytest

import database
from conftest import TEST_PASSWORD
from device import Device


def test_sample_data_has_ten_of_each():
    assert len(database.get_all_users()) == 10
    assert len(database.get_all_devices()) == 10


def test_sample_data_has_two_admins():
    admins = []
    for user in database.get_all_users():
        if user.is_admin():
            admins.append(user.alias)
    assert sorted(admins) == ["ginat", "tbom"]


def test_device_shows_borrower_from_users_table():
    device = database.get_device("LR-0001")
    assert device.assigned_to_name == "Jane Doe"
    assert device.assigned_to_alias == "janedoe"


def test_add_and_get_device():
    database.add_device(Device("LR-0011", "Xbox One"))
    device = database.get_device("LR-0011")
    assert device.model_name == "Xbox One"
    assert device.is_checked_out() is False


def test_missing_device_returns_none():
    assert database.get_device("LR-9999") is None


def test_duplicate_asset_tag_is_rejected():
    with pytest.raises(sqlite3.IntegrityError):
        database.add_device(Device("LR-0001", "Xbox One"))


def test_device_must_belong_to_a_real_user():
    # Foreign key: there is no user with id 999
    with pytest.raises(sqlite3.IntegrityError):
        database.add_device(Device("LR-0011", "Xbox One", assigned_to=999))


def test_check_out_and_return():
    bob = database.get_user_by_alias("bstone")
    due = date.today() + timedelta(days=7)

    database.check_out_device("LR-0002", bob.user_id, "Desk 2.10", due)
    device = database.get_device("LR-0002")
    assert device.assigned_to_alias == "bstone"
    assert device.desk_location == "Desk 2.10"
    assert device.checked_out_date == date.today()
    assert device.due_date == due

    database.return_device("LR-0002")
    assert database.get_device("LR-0002").is_checked_out() is False


def test_delete_device():
    database.delete_device("LR-0002")
    assert database.get_device("LR-0002") is None
    assert len(database.get_all_devices()) == 9


def test_passwords_are_hashed():
    connection = database.get_connection()
    saved = connection.execute("SELECT password FROM users WHERE alias = 'janedoe'").fetchone()[0]
    connection.close()
    assert saved != TEST_PASSWORD


def test_check_login():
    assert database.check_login("janedoe", TEST_PASSWORD).alias == "janedoe"
    assert database.check_login("janedoe", "wrong") is None
    assert database.check_login("nobody", TEST_PASSWORD) is None


def test_count_devices_borrowed():
    jane = database.get_user_by_alias("janedoe")
    bob = database.get_user_by_alias("bstone")
    assert database.count_devices_borrowed(jane.user_id) == 1
    assert database.count_devices_borrowed(bob.user_id) == 0
