# validation.py
# Functions that check what the user typed.
# Each one returns an error message if something is wrong, or None if it is fine.

from datetime import date


def check_name(name):
    """Name must be filled in and no longer than 50 characters"""
    if name == "":
        return "Please enter your name."
    if len(name) > 50:
        return "Name must be 50 characters or fewer."
    return None


def check_alias(alias):
    """Alias must be 3-20 characters, using only lowercase letters and numbers"""
    if len(alias) < 3 or len(alias) > 20:
        return "Alias must be between 3 and 20 characters."
    # isalnum() is True if every character is a letter or a number
    if not alias.isalnum() or alias != alias.lower():
        return "Alias can only use lowercase letters and numbers, e.g. janedoe."
    return None


def check_asset_tag(asset_tag):
    """Asset tag must look like LR-0001: "LR-" followed by exactly 4 numbers"""
    if len(asset_tag) != 7 or not asset_tag.startswith("LR-") or not asset_tag[3:].isdigit():
        return "Asset tag must be LR- followed by 4 numbers, e.g. LR-0011."
    return None


def check_model_name(model_name):
    """Model name must be filled in and no longer than 50 characters"""
    if model_name == "":
        return "Please enter the model name."
    if len(model_name) > 50:
        return "Model name must be 50 characters or fewer."
    return None


def check_desk_location(desk_location):
    """Desk location must be filled in and no longer than 20 characters"""
    if desk_location == "":
        return "Please enter the desk location."
    if len(desk_location) > 20:
        return "Desk location must be 20 characters or fewer."
    return None


def check_due_date(due_date_text):
    """Due date must be a real date (YYYY-MM-DD) and not in the past"""
    try:
        due_date = date.fromisoformat(due_date_text)
    except ValueError:
        # fromisoformat() raises a ValueError if the text is not a real date
        return "Please choose a valid due date."
    if due_date < date.today():
        return "The due date cannot be in the past."
    return None


def check_password(password, confirm):
    """Password must be at least 8 characters, with a letter and a number, typed twice the same"""
    if len(password) < 8:
        return "Password must be at least 8 characters."

    has_letter = False
    has_number = False
    for character in password:
        if character.isalpha():
            has_letter = True
        if character.isdigit():
            has_number = True
    if not has_letter or not has_number:
        return "Password must contain at least one letter and one number."

    if password != confirm:
        return "The two passwords do not match."
    return None
