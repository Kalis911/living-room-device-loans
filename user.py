# user.py
# This file describes ONE person who can log in and borrow devices.


class User:
    """A person who uses the device loan system"""

    def __init__(self, user_id, name, alias, role):
        # The number the database gives each user, e.g. 1
        self.user_id = user_id
        # The person's full name, e.g. "Jane Doe"
        self.name = name
        # The person's alias, e.g. "janedoe" (they log in with this)
        self.alias = alias
        # Either "admin" or "regular"
        self.role = role

    def is_admin(self):
        """Return True if this user is an admin (admins can delete records)"""
        return self.role == "admin"
