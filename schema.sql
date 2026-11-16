-- schema.sql
-- The tables for the device loan system.
-- IF NOT EXISTS means running this again will not delete the data already saved.

-- Table 1: people who can log in and borrow devices
CREATE TABLE IF NOT EXISTS users (
    id       INTEGER PRIMARY KEY AUTOINCREMENT, -- a number given to each user automatically
    name     TEXT NOT NULL,                     -- e.g. Jane Doe
    alias    TEXT UNIQUE NOT NULL,              -- e.g. janedoe (also used to log in)
    password TEXT NOT NULL,                     -- a hashed password, never the real one
    role     TEXT NOT NULL CHECK (role IN ('admin', 'regular'))
);

-- Table 2: the devices that can be borrowed
CREATE TABLE IF NOT EXISTS devices (
    asset_tag        TEXT PRIMARY KEY,  -- unique ID on the device's label, e.g. LR-0001
    model_name       TEXT NOT NULL,     -- e.g. PlayStation 4
    assigned_to      INTEGER,           -- the id of the user who has it (empty if available)
    desk_location    TEXT,              -- e.g. Desk 4.12
    checked_out_date DATE,              -- the day it was borrowed
    due_date         DATE,              -- the day it must be returned
    -- Foreign key: assigned_to must be the id of a user that really exists
    FOREIGN KEY (assigned_to) REFERENCES users (id)
);

-- The borrower's name and alias are no longer stored in devices.
-- They are looked up from the users table using assigned_to, so each
-- person's details are only stored once.
--
-- "How long they have had it" is not stored either. It is worked out from
-- checked_out_date each time (see days_checked_out() in device.py).
