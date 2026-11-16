# device.py
# This file describes ONE living room device that staff can borrow,
# like a book in a library.

# date: lets us work with calendar dates (e.g. 2026-11-16)
from datetime import date


class Device:
    """A living room device (set top box, console, etc.) that can be borrowed"""

    def __init__(self, asset_tag, model_name, assigned_to=None,
                 desk_location=None, checked_out_date=None, due_date=None,
                 assigned_to_name=None, assigned_to_alias=None):
        # The asset tag is the device's unique ID, e.g. "LR-0001"
        self.asset_tag = asset_tag
        # The model name, e.g. "PlayStation 4"
        self.model_name = model_name
        # The id of the user who has the device (None when it is not borrowed)
        self.assigned_to = assigned_to
        # The borrower's name and alias. These are not saved in the devices
        # table; they are filled in from the users table when a device is read.
        self.assigned_to_name = assigned_to_name
        self.assigned_to_alias = assigned_to_alias
        # Where the device is in the office, e.g. "Desk 4.12"
        self.desk_location = desk_location
        # When it was borrowed and when it must be returned
        self.checked_out_date = checked_out_date
        self.due_date = due_date

    def is_checked_out(self):
        """Return True if someone currently has this device"""
        return self.assigned_to is not None

    def days_checked_out(self):
        """Return how many days the person has had the device (0 if not borrowed)"""
        if self.checked_out_date is None:
            return 0
        # Taking one date away from another gives the gap in days
        return (date.today() - self.checked_out_date).days

    def is_overdue(self):
        """Return True if the device should already have been returned"""
        if self.due_date is None:
            return False
        return date.today() > self.due_date


# This code only runs when you run this file directly: python device.py
# It creates two example devices so you can see the class working.
if __name__ == "__main__":
    borrowed = Device(
        asset_tag="LR-0001",
        model_name="PlayStation 4",
        assigned_to=1,
        desk_location="Desk 4.12",
        checked_out_date=date(2026, 11, 2),
        due_date=date(2026, 11, 9),
        assigned_to_name="Jane Doe",
        assigned_to_alias="janedoe",
    )
    available = Device(asset_tag="LR-0002", model_name="Fire TV Stick 4K")

    for device in (borrowed, available):
        print("=" * 30)
        print(f"Asset tag:     {device.asset_tag}")
        print(f"Model:         {device.model_name}")
        print(f"Checked out:   {device.is_checked_out()}")
        print(f"Assigned to:   {device.assigned_to_name} ({device.assigned_to_alias})")
        print(f"Desk:          {device.desk_location}")
        print(f"Days borrowed: {device.days_checked_out()}")
        print(f"Due back:      {device.due_date}")
        print(f"Overdue:       {device.is_overdue()}")
