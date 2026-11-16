# test_app.py
# Tests for the web pages in app.py, using a pretend web browser ("client").
# b"..." means bytes: web pages come back as bytes, not normal text.

from datetime import date, timedelta

import database
from conftest import log_in


# ---------- Logging in ----------

def test_pages_need_login(client):
    for page in ["/", "/devices", "/devices/add", "/users", "/account"]:
        response = client.get(page)
        assert response.status_code == 302           # 302 = sent somewhere else
        assert "/login" in response.headers["Location"]


def test_login_and_logout(client):
    response = log_in(client, "janedoe")
    assert b"Welcome, Jane Doe!" in response.data

    response = client.post("/logout", follow_redirects=True)
    assert b"You have been logged out." in response.data
    assert client.get("/").status_code == 302


def test_wrong_password(client):
    response = client.post("/login", data={"alias": "janedoe", "password": "wrong"})
    assert b"Incorrect alias or password." in response.data


# ---------- Registering ----------

def test_register_makes_regular_user(client):
    form = {"name": "Sam Lee", "alias": "samlee", "password": "Secret123",
            "confirm": "Secret123", "role": "admin"}   # "role" is a sneaky extra field
    response = client.post("/register", data=form, follow_redirects=True)
    assert b"Account created!" in response.data
    assert database.get_user_by_alias("samlee").role == "regular"


def test_register_rejects_taken_alias(client):
    form = {"name": "Another Jane", "alias": "janedoe", "password": "Secret123",
            "confirm": "Secret123"}
    response = client.post("/register", data=form)
    assert b"That alias is already registered." in response.data


# ---------- Devices ----------

def test_devices_page_lists_devices(client):
    log_in(client, "janedoe")
    response = client.get("/devices")
    assert b"LR-0001" in response.data
    assert b"Overdue" in response.data or b"On loan" in response.data


def test_regular_user_can_add_device(client):
    log_in(client, "janedoe")
    response = client.post("/devices/add", data={"asset_tag": "lr-0011", "model_name": "Xbox One"},
                           follow_redirects=True)
    assert b"Xbox One (LR-0011) has been added." in response.data
    assert database.get_device("LR-0011") is not None


def test_add_device_shows_errors(client):
    log_in(client, "janedoe")
    response = client.post("/devices/add", data={"asset_tag": "LR-0001", "model_name": ""})
    assert b"already exists" in response.data
    assert b"Please enter the model name." in response.data


def test_check_out_device(client):
    log_in(client, "janedoe")
    bob = database.get_user_by_alias("bstone")
    due = str(date.today() + timedelta(days=7))
    response = client.post("/devices/LR-0002/checkout", follow_redirects=True,
                           data={"borrower_id": bob.user_id, "desk_location": "Desk 2.10",
                                 "due_date": due})
    assert b"has been lent to Bob Stone" in response.data
    assert database.get_device("LR-0002").assigned_to == bob.user_id


def test_regular_user_cannot_change_due_date(client):
    log_in(client, "janedoe")
    before = database.get_device("LR-0003")
    later = str(date.today() + timedelta(days=60))
    client.post("/devices/LR-0003/edit",
                data={"model_name": "Xbox Series S", "desk_location": "Desk 9.99",
                      "due_date": later})
    after = database.get_device("LR-0003")
    assert after.model_name == "Xbox Series S"            # allowed
    assert after.due_date == before.due_date              # not allowed, so unchanged
    assert after.desk_location == before.desk_location    # not allowed, so unchanged


# ---------- Admin-only actions ----------

def test_regular_user_cannot_return_or_delete(client):
    log_in(client, "janedoe")
    for action in ["/devices/LR-0001/return", "/devices/LR-0002/delete"]:
        response = client.post(action, follow_redirects=True)
        assert b"Only admins can do that." in response.data
    assert database.get_device("LR-0001").is_checked_out() is True
    assert database.get_device("LR-0002") is not None


def test_admin_can_return_and_delete(client):
    log_in(client, "tbom")
    response = client.post("/devices/LR-0001/return", follow_redirects=True)
    assert b"is now available" in response.data
    response = client.post("/devices/LR-0001/delete", follow_redirects=True)
    assert b"has been deleted" in response.data
    assert database.get_device("LR-0001") is None


def test_borrowed_device_cannot_be_deleted(client):
    log_in(client, "tbom")
    response = client.post("/devices/LR-0001/delete", follow_redirects=True)
    assert b"must be returned before it can be deleted" in response.data


# ---------- Users ----------

def test_admin_can_change_role(client):
    log_in(client, "tbom")
    jane = database.get_user_by_alias("janedoe")
    response = client.post(f"/users/{jane.user_id}/role", follow_redirects=True)
    assert b"Jane Doe is now admin." in response.data


def test_admin_cannot_change_own_role(client):
    log_in(client, "tbom")
    tom = database.get_user_by_alias("tbom")
    response = client.post(f"/users/{tom.user_id}/role", follow_redirects=True)
    assert b"You cannot change your own role." in response.data


def test_user_with_devices_cannot_be_deleted(client):
    log_in(client, "tbom")
    jane = database.get_user_by_alias("janedoe")
    response = client.post(f"/users/{jane.user_id}/delete", follow_redirects=True)
    assert b"still has borrowed devices" in response.data
    assert database.get_user_by_alias("janedoe") is not None


def test_change_own_name(client):
    log_in(client, "janedoe")
    response = client.post("/account", data={"name": "Jane Doe-Smith"}, follow_redirects=True)
    assert b"Your name has been updated." in response.data
    assert database.get_user_by_alias("janedoe").name == "Jane Doe-Smith"


# ---------- Error pages ----------

def test_missing_page_shows_friendly_error(client):
    response = client.get("/no-such-page")
    assert response.status_code == 404
    assert b"Sorry, that page does not exist." in response.data
