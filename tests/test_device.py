# test_device.py
# Tests for the Device class in device.py

from datetime import date, timedelta

from device import Device

# timedelta(days=...) lets us make dates relative to today,
# so these tests still pass whatever day they are run
TODAY = date.today()


def test_available_device():
    device = Device("LR-0001", "PlayStation 4")
    assert device.is_checked_out() is False
    assert device.days_checked_out() == 0
    assert device.is_overdue() is False


def test_borrowed_device_counts_days():
    device = Device("LR-0001", "PlayStation 4", assigned_to=1, desk_location="Desk 1.01",
                    checked_out_date=TODAY - timedelta(days=5),
                    due_date=TODAY + timedelta(days=2))
    assert device.is_checked_out() is True
    assert device.days_checked_out() == 5
    assert device.is_overdue() is False


def test_overdue_device():
    device = Device("LR-0001", "PlayStation 4", assigned_to=1, desk_location="Desk 1.01",
                    checked_out_date=TODAY - timedelta(days=10),
                    due_date=TODAY - timedelta(days=1))
    assert device.is_overdue() is True


def test_device_due_today_is_not_overdue():
    device = Device("LR-0001", "PlayStation 4", assigned_to=1, desk_location="Desk 1.01",
                    checked_out_date=TODAY - timedelta(days=7), due_date=TODAY)
    assert device.is_overdue() is False
