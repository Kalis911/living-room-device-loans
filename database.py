# database.py
# This file saves users and devices into a database and reads them back out.

# sqlite3: Python's built-in library for SQLite databases
# getpass: asks for a password without showing it on the screen
import getpass
import os
import sqlite3
from datetime import date

# Werkzeug comes with Flask. It turns a password into a "hash" (scrambled text)
# so the real password is never saved in the database.
from werkzeug.security import check_password_hash, generate_password_hash

from device import Device
from user import User

# The database is saved in this file (it is created the first time)
DATABASE_FILE = "devices.db"


def get_connection():
    """Open a connection to the database file"""
    connection = sqlite3.connect(DATABASE_FILE)
    # Row lets us use row["model_name"] instead of row[1]
    connection.row_factory = sqlite3.Row
    # SQLite only checks foreign keys if we switch this on
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_database():
    """Create the tables using the SQL in schema.sql"""
    with open("schema.sql") as file:
        sql = file.read()
    connection = get_connection()
    connection.executescript(sql)
    connection.close()


def setup_database():
    """
    Called when the web app starts. Creates the tables if they are missing.
    If there are no users yet AND a SEED_PASSWORD environment variable is set
    (it is on the live website), the 10 sample users and devices are added.
    """
    create_database()
    password = os.environ.get("SEED_PASSWORD")
    if len(get_all_users()) == 0 and password:
        add_sample_data(password)


def date_to_text(value):
    """Turn a Python date into text like "2026-11-02" so the database can store it"""
    if value is None:
        return None
    return value.isoformat()


def text_to_date(value):
    """Turn text like "2026-11-02" from the database back into a Python date"""
    if value is None:
        return None
    return date.fromisoformat(value)


# ---------- Users ----------

def add_user(name, alias, password, role):
    """Save a new user. The password is hashed before it is saved."""
    connection = get_connection()
    connection.execute(
        "INSERT INTO users (name, alias, password, role) VALUES (?, ?, ?, ?)",
        (name, alias, generate_password_hash(password), role),
    )
    connection.commit()
    connection.close()


def row_to_user(row):
    """Turn one row from the users table into a User object"""
    return User(row["id"], row["name"], row["alias"], row["role"])


def get_all_users():
    """Return a list of every User"""
    connection = get_connection()
    rows = connection.execute("SELECT * FROM users ORDER BY name").fetchall()
    connection.close()

    users = []
    for row in rows:
        users.append(row_to_user(row))
    return users


def get_user_by_alias(alias):
    """Return the User with this alias, or None if there is no such user"""
    connection = get_connection()
    row = connection.execute("SELECT * FROM users WHERE alias = ?", (alias,)).fetchone()
    connection.close()

    if row is None:
        return None
    return row_to_user(row)


def get_user_by_id(user_id):
    """Return the User with this id, or None if there is no such user"""
    connection = get_connection()
    row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    connection.close()

    if row is None:
        return None
    return row_to_user(row)


def check_login(alias, password):
    """Return the User if the alias and password are correct, otherwise None"""
    connection = get_connection()
    row = connection.execute("SELECT * FROM users WHERE alias = ?", (alias,)).fetchone()
    connection.close()

    # check_password_hash compares the typed password with the saved hash
    if row is not None and check_password_hash(row["password"], password):
        return row_to_user(row)
    return None


def set_user_role(user_id, role):
    """Change a user's role to "admin" or "regular" """
    connection = get_connection()
    connection.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
    connection.commit()
    connection.close()


def update_user_name(user_id, name):
    """Change a user's full name"""
    connection = get_connection()
    connection.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
    connection.commit()
    connection.close()


def delete_user(user_id):
    """Remove a user from the database completely"""
    connection = get_connection()
    connection.execute("DELETE FROM users WHERE id = ?", (user_id,))
    connection.commit()
    connection.close()


def count_devices_borrowed(user_id):
    """Return how many devices this user has borrowed at the moment"""
    connection = get_connection()
    # COUNT(*) counts the rows that match, instead of returning them
    count = connection.execute(
        "SELECT COUNT(*) FROM devices WHERE assigned_to = ?", (user_id,)
    ).fetchone()[0]
    connection.close()
    return count


# ---------- Devices ----------

# This SQL is used by both device functions below, so it is written once here.
# LEFT JOIN links each device to the user in assigned_to, so we also get the
# borrower's name and alias. "LEFT" means devices with nobody assigned are
# still included (their name and alias are just empty).
SELECT_DEVICES = """
    SELECT devices.*, users.name AS user_name, users.alias AS user_alias
    FROM devices
    LEFT JOIN users ON devices.assigned_to = users.id
"""


def row_to_device(row):
    """Turn one row from the database into a Device object"""
    return Device(
        asset_tag=row["asset_tag"],
        model_name=row["model_name"],
        assigned_to=row["assigned_to"],
        desk_location=row["desk_location"],
        checked_out_date=text_to_date(row["checked_out_date"]),
        due_date=text_to_date(row["due_date"]),
        assigned_to_name=row["user_name"],
        assigned_to_alias=row["user_alias"],
    )


def add_device(device):
    """Save a new Device into the database"""
    connection = get_connection()
    # The ? marks are filled in with the values in brackets.
    # This is safer than putting the values straight into the SQL text,
    # because it stops "SQL injection" attacks.
    connection.execute(
        "INSERT INTO devices (asset_tag, model_name, assigned_to, desk_location,"
        " checked_out_date, due_date) VALUES (?, ?, ?, ?, ?, ?)",
        (device.asset_tag, device.model_name, device.assigned_to, device.desk_location,
         date_to_text(device.checked_out_date), date_to_text(device.due_date)),
    )
    # commit() saves the change permanently
    connection.commit()
    connection.close()


def check_out_device(asset_tag, user_id, desk_location, due_date):
    """Lend a device to a user: save who has it, where, and when it is due back"""
    connection = get_connection()
    # UPDATE changes an existing row. WHERE picks which row to change.
    connection.execute(
        "UPDATE devices SET assigned_to = ?, desk_location = ?, checked_out_date = ?,"
        " due_date = ? WHERE asset_tag = ?",
        (user_id, desk_location, date_to_text(date.today()), date_to_text(due_date), asset_tag),
    )
    connection.commit()
    connection.close()


def update_device(asset_tag, model_name, desk_location, due_date):
    """Save changes to a device's model name, desk location and due date"""
    connection = get_connection()
    connection.execute(
        "UPDATE devices SET model_name = ?, desk_location = ?, due_date = ? WHERE asset_tag = ?",
        (model_name, desk_location, date_to_text(due_date), asset_tag),
    )
    connection.commit()
    connection.close()


def delete_device(asset_tag):
    """Remove a device from the database completely"""
    connection = get_connection()
    connection.execute("DELETE FROM devices WHERE asset_tag = ?", (asset_tag,))
    connection.commit()
    connection.close()


def return_device(asset_tag):
    """Mark a device as returned: clear who has it, so it is available again"""
    connection = get_connection()
    # NULL means "empty" in SQL
    connection.execute(
        "UPDATE devices SET assigned_to = NULL, desk_location = NULL,"
        " checked_out_date = NULL, due_date = NULL WHERE asset_tag = ?",
        (asset_tag,),
    )
    connection.commit()
    connection.close()


def get_all_devices():
    """Return a list of every Device in the database"""
    connection = get_connection()
    rows = connection.execute(SELECT_DEVICES + " ORDER BY devices.asset_tag").fetchall()
    connection.close()

    devices = []
    for row in rows:
        devices.append(row_to_device(row))
    return devices


def get_device(asset_tag):
    """Return the Device with this asset tag, or None if it does not exist"""
    connection = get_connection()
    row = connection.execute(
        SELECT_DEVICES + " WHERE devices.asset_tag = ?", (asset_tag,)
    ).fetchone()
    connection.close()

    if row is None:
        return None
    return row_to_device(row)


# ---------- Sample data ----------

def add_sample_data(password):
    """Add 10 users and 10 devices (the brief asks for 10 records in each table)"""
    # 2 admins and 8 regular users. They all start with the same password.
    sample_users = [
        ("Tom Bombadil", "tbom", "admin"),
        ("Gina Torres", "ginat", "admin"),
        ("Jane Doe", "janedoe", "regular"),
        ("John Smith", "jsmith", "regular"),
        ("Alice Johnson", "alicej", "regular"),
        ("Daniel Wu", "danielw", "regular"),
        ("Eva Green", "evagreen", "regular"),
        ("Bob Stone", "bstone", "regular"),
        ("Claire Redfield", "clairer", "regular"),
        ("Frank Castle", "frankc", "regular"),
    ]
    for name, alias, role in sample_users:
        add_user(name, alias, password, role)

    # Borrowed devices are linked to a user by that user's id
    jane = get_user_by_alias("janedoe").user_id
    john = get_user_by_alias("jsmith").user_id
    alice = get_user_by_alias("alicej").user_id
    daniel = get_user_by_alias("danielw").user_id
    eva = get_user_by_alias("evagreen").user_id

    sample_devices = [
        Device("LR-0001", "PlayStation 4", jane, "Desk 4.12",
               date(2026, 11, 2), date(2026, 11, 9)),
        Device("LR-0002", "Fire TV Stick 4K"),
        Device("LR-0003", "Xbox Series X", john, "Desk 2.03",
               date(2026, 11, 10), date(2026, 11, 24)),
        Device("LR-0004", "Apple TV 4K"),
        Device("LR-0005", "Sky Q Box", alice, "Desk 3.07",
               date(2026, 10, 20), date(2026, 11, 3)),
        Device("LR-0006", "Roku Ultra"),
        Device("LR-0007", "PlayStation 5", daniel, "Desk 1.15",
               date(2026, 11, 12), date(2026, 11, 26)),
        Device("LR-0008", "Nintendo Switch"),
        Device("LR-0009", "Virgin Media TV 360", eva, "Desk 4.02",
               date(2026, 11, 1), date(2026, 11, 15)),
        Device("LR-0010", "Chromecast with Google TV"),
    ]
    for device in sample_devices:
        add_device(device)


# This code only runs when you run this file directly: python database.py
if __name__ == "__main__":
    create_database()

    # Only add the sample data if there are no users yet,
    # otherwise running this twice would try to add everything again
    if len(get_all_users()) == 0:
        # The password is typed in, not written in the code, because
        # anyone who can read the code would otherwise know it
        password = getpass.getpass("Choose a password for the sample users: ")
        add_sample_data(password)
        print("Added 10 sample users and 10 sample devices.")

    print("\nAll users:")
    for user in get_all_users():
        print(f"{user.alias:<10} {user.name:<16} {user.role}")

    print("\nAll devices:")
    for device in get_all_devices():
        if device.is_checked_out():
            status = (f"borrowed by {device.assigned_to_name} ({device.assigned_to_alias}),"
                      f" due {device.due_date}")
            if device.is_overdue():
                status += " (OVERDUE)"
        else:
            status = "available"
        print(f"{device.asset_tag}  {device.model_name:<26} {status}")
