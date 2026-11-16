# app.py
# The web application. Run it with:  python app.py
# Then open http://127.0.0.1:5000 in a web browser.

import functools
import logging
import os
import secrets
from datetime import date

# Flask: the web framework
# render_template: shows an HTML page from the templates folder
# request: the data the user sent (e.g. what they typed in a form)
# redirect / url_for: send the user to a different page
# session: remembers who is logged in (stored in a signed cookie)
# flash: shows a one-off message on the next page, e.g. "Logged out"
from flask import Flask, flash, redirect, render_template, request, session, url_for

import database
import validation
from device import Device

app = Flask(__name__)

# Render (the hosting website) sets an environment variable called RENDER,
# so this is True on the live website and False on your own computer
ON_RENDER = os.environ.get("RENDER") is not None

# The secret key signs the session cookie so it cannot be faked.
# On the live website it MUST be set as an environment variable, so the app
# refuses to start without one. On your own computer a random one is made
# each time the app starts.
if ON_RENDER and not os.environ.get("SECRET_KEY"):
    raise RuntimeError("SECRET_KEY must be set on the live website.")
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(16)

# Stops other websites from sending forms using the user's login cookie
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# On the live website (which uses https), only send the login cookie over https
app.config["SESSION_COOKIE_SECURE"] = ON_RENDER

# Error logging: important events and errors are saved to app.log,
# with the date and time, so problems can be looked into later.
# (Level 4 only printed errors to the screen, so they were lost.)
log_file = logging.FileHandler("app.log")
log_file.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
app.logger.addHandler(log_file)
app.logger.setLevel(logging.INFO)

# Make sure the database tables exist (and add the sample data on the live
# website the first time it starts). This runs however the app is started.
database.setup_database()


def get_logged_in_user():
    """Return the User who is logged in, or None if nobody is"""
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return database.get_user_by_id(user_id)


def login_required(page_function):
    """
    A "decorator": write @login_required above a page function and this
    check runs first. If nobody is logged in they are sent to the login page,
    otherwise the page runs as normal.
    This replaces the same 4 lines that used to be copied into every page.
    """
    # functools.wraps keeps the page function's name, which Flask needs
    @functools.wraps(page_function)
    def check_then_show_page(**kwargs):
        if get_logged_in_user() is None:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return page_function(**kwargs)
    return check_then_show_page


def admin_required(page_function):
    """
    Like @login_required, but the user must also be an admin.
    Write @admin_required above pages that only admins may use.
    """
    @functools.wraps(page_function)
    def check_then_show_page(**kwargs):
        user = get_logged_in_user()
        if user is None:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        if not user.is_admin():
            app.logger.warning("%s tried to use an admin-only action: %s",
                               user.alias, request.path)
            flash("Only admins can do that.", "error")
            return redirect(url_for("devices"))
        return page_function(**kwargs)
    return check_then_show_page


@app.route("/")
@login_required
def home():
    """Home page"""
    user = get_logged_in_user()
    return render_template("home.html", user=user)


@app.route("/devices")
@login_required
def devices():
    """List every device"""
    user = get_logged_in_user()
    all_devices = database.get_all_devices()
    return render_template("devices.html", user=user, devices=all_devices)


@app.route("/devices/add", methods=["GET", "POST"])
@login_required
def add_device():
    """Show the add device form (GET), or save the new device (POST)"""
    user = get_logged_in_user()

    if request.method == "POST":
        # upper() means "lr-0011" is saved as "LR-0011"
        asset_tag = request.form.get("asset_tag", "").strip().upper()
        model_name = request.form.get("model_name", "").strip()

        errors = []
        for error in [validation.check_asset_tag(asset_tag),
                      validation.check_model_name(model_name)]:
            if error is not None:
                errors.append(error)
        if database.get_device(asset_tag) is not None:
            errors.append(f"A device with asset tag {asset_tag} already exists.")

        if len(errors) > 0:
            for error in errors:
                flash(error, "error")
            return render_template("add_device.html", user=user,
                                   asset_tag=asset_tag, model_name=model_name)

        # A new device starts as available (on the shelf). Lending it to
        # someone is a separate step, like checking out a library book.
        database.add_device(Device(asset_tag, model_name))
        app.logger.info("%s added device %s", user.alias, asset_tag)
        flash(f"{model_name} ({asset_tag}) has been added.", "success")
        return redirect(url_for("devices"))

    return render_template("add_device.html", user=user, asset_tag="", model_name="")


@app.route("/devices/<asset_tag>/checkout", methods=["GET", "POST"])
@login_required
def check_out(asset_tag):
    """Lend a device to someone. <asset_tag> in the web address says which device."""
    user = get_logged_in_user()
    device = database.get_device(asset_tag)

    # Stop if the device does not exist or someone already has it
    if device is None:
        flash(f"There is no device with asset tag {asset_tag}.", "error")
        return redirect(url_for("devices"))
    if device.is_checked_out():
        flash(f"{device.model_name} is already borrowed by {device.assigned_to_name}.", "error")
        return redirect(url_for("devices"))

    # The list of people the device can be lent to (for the drop-down menu)
    all_users = database.get_all_users()

    if request.method == "POST":
        borrower_id = request.form.get("borrower_id", "")
        desk_location = request.form.get("desk_location", "").strip()
        due_date_text = request.form.get("due_date", "")

        errors = []
        # The borrower must be one of the real users, not something made up
        borrower = None
        if borrower_id.isdigit():
            borrower = database.get_user_by_id(int(borrower_id))
        if borrower is None:
            errors.append("Please choose who is borrowing the device.")
        for error in [validation.check_desk_location(desk_location),
                      validation.check_due_date(due_date_text)]:
            if error is not None:
                errors.append(error)

        if len(errors) > 0:
            for error in errors:
                flash(error, "error")
            return render_template("check_out.html", user=user, device=device,
                                   all_users=all_users, borrower_id=borrower_id,
                                   desk_location=desk_location, due_date=due_date_text)

        database.check_out_device(asset_tag, borrower.user_id, desk_location,
                                  date.fromisoformat(due_date_text))
        app.logger.info("%s lent device %s to %s", user.alias, asset_tag, borrower.alias)
        flash(f"{device.model_name} ({asset_tag}) has been lent to {borrower.name}.", "success")
        return redirect(url_for("devices"))

    # First visit: the logged-in user is picked in the drop-down to start with
    return render_template("check_out.html", user=user, device=device,
                           all_users=all_users, borrower_id=str(user.user_id),
                           desk_location="", due_date="")


@app.route("/devices/<asset_tag>/edit", methods=["GET", "POST"])
@login_required
def edit_device(asset_tag):
    """
    Change a device's details.
    Everyone can change the model name. Only admins can change the loan
    details (desk and due date), just like only admins can return devices.
    """
    user = get_logged_in_user()
    device = database.get_device(asset_tag)
    if device is None:
        flash(f"There is no device with asset tag {asset_tag}.", "error")
        return redirect(url_for("devices"))

    if request.method == "POST":
        model_name = request.form.get("model_name", "").strip()

        errors = []
        error = validation.check_model_name(model_name)
        if error is not None:
            errors.append(error)

        # Desk and due date can only be changed by an admin, and only while the
        # device is on loan. For anyone else the current values are kept, even
        # if extra values are sent in the form.
        desk_location = device.desk_location
        due_date = device.due_date
        if device.is_checked_out() and user.is_admin():
            desk_location = request.form.get("desk_location", "").strip()
            due_date_text = request.form.get("due_date", "")

            error = validation.check_desk_location(desk_location)
            if error is not None:
                errors.append(error)

            # Only check the due date if it was changed. An overdue device
            # already has a date in the past, and that should not stop
            # someone fixing a typo in the model name.
            if due_date_text != str(device.due_date):
                error = validation.check_due_date(due_date_text)
                if error is not None:
                    errors.append(error)
                else:
                    due_date = date.fromisoformat(due_date_text)

        if len(errors) > 0:
            for error in errors:
                flash(error, "error")
            return render_template("edit_device.html", user=user, device=device,
                                   model_name=model_name, desk_location=desk_location,
                                   due_date=request.form.get("due_date", ""))

        database.update_device(asset_tag, model_name, desk_location, due_date)
        app.logger.info("%s edited device %s", user.alias, asset_tag)
        flash(f"{model_name} ({asset_tag}) has been updated.", "success")
        return redirect(url_for("devices"))

    # First visit: fill the form with the device's current details
    return render_template("edit_device.html", user=user, device=device,
                           model_name=device.model_name,
                           desk_location=device.desk_location or "",
                           due_date=str(device.due_date or ""))


@app.route("/devices/<asset_tag>/return", methods=["POST"])
@admin_required
def return_device(asset_tag):
    """Mark a borrowed device as returned (admins only, after they confirm)"""
    user = get_logged_in_user()
    device = database.get_device(asset_tag)

    if device is None:
        flash(f"There is no device with asset tag {asset_tag}.", "error")
    elif not device.is_checked_out():
        flash(f"{device.model_name} ({asset_tag}) is not currently borrowed.", "error")
    else:
        database.return_device(asset_tag)
        app.logger.info("%s marked device %s as returned", user.alias, asset_tag)
        flash(f"{device.model_name} ({asset_tag}) has been returned by "
              f"{device.assigned_to_name} and is now available.", "success")
    return redirect(url_for("devices"))


@app.route("/devices/<asset_tag>/delete", methods=["POST"])
@admin_required
def delete_device(asset_tag):
    """Delete a device (admins only, after they confirm)"""
    user = get_logged_in_user()
    device = database.get_device(asset_tag)

    if device is None:
        flash(f"There is no device with asset tag {asset_tag}.", "error")
    elif device.is_checked_out():
        # Deleting a device someone still has would lose track of it
        flash(f"{device.model_name} ({asset_tag}) is borrowed by {device.assigned_to_name}. "
              "It must be returned before it can be deleted.", "error")
    else:
        database.delete_device(asset_tag)
        app.logger.info("%s deleted device %s", user.alias, asset_tag)
        flash(f"{device.model_name} ({asset_tag}) has been deleted.", "success")
    return redirect(url_for("devices"))


@app.route("/users")
@login_required
def users():
    """List every user, and how many devices each one has borrowed"""
    user = get_logged_in_user()
    all_users = database.get_all_users()

    # A dictionary linking each user's id to their number of borrowed devices,
    # e.g. {1: 0, 3: 1}
    borrowed_counts = {}
    for person in all_users:
        borrowed_counts[person.user_id] = database.count_devices_borrowed(person.user_id)

    return render_template("users.html", user=user, all_users=all_users,
                           borrowed_counts=borrowed_counts)


@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    """Let the logged-in user change their own name"""
    user = get_logged_in_user()

    if request.method == "POST":
        name = request.form.get("name", "").strip()

        error = validation.check_name(name)
        if error is not None:
            flash(error, "error")
            return render_template("account.html", user=user, name=name)

        # Only the logged-in user's own record is changed: the id comes from
        # their session, not from the form, so nobody can edit someone else
        database.update_user_name(user.user_id, name)
        app.logger.info("%s changed their name", user.alias)
        flash("Your name has been updated.", "success")
        return redirect(url_for("account"))

    return render_template("account.html", user=user, name=user.name)


@app.route("/users/<int:user_id>/role", methods=["POST"])
@admin_required
def change_role(user_id):
    """Switch a user between admin and regular (admins only, after they confirm)"""
    user = get_logged_in_user()
    person = database.get_user_by_id(user_id)

    if person is None:
        flash("That user does not exist.", "error")
    elif person.user_id == user.user_id:
        # Stops an admin removing their own admin rights by mistake
        flash("You cannot change your own role.", "error")
    else:
        if person.is_admin():
            new_role = "regular"
        else:
            new_role = "admin"
        database.set_user_role(person.user_id, new_role)
        app.logger.info("%s changed %s's role to %s", user.alias, person.alias, new_role)
        flash(f"{person.name} is now {new_role}.", "success")
    return redirect(url_for("users"))


@app.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    """Delete a user (admins only, after they confirm)"""
    user = get_logged_in_user()
    person = database.get_user_by_id(user_id)

    if person is None:
        flash("That user does not exist.", "error")
    elif person.user_id == user.user_id:
        flash("You cannot delete your own account.", "error")
    elif database.count_devices_borrowed(person.user_id) > 0:
        # Same rule as devices: we must not lose track of borrowed devices
        flash(f"{person.name} still has borrowed devices. "
              "They must be returned before the user can be deleted.", "error")
    else:
        database.delete_user(person.user_id)
        app.logger.info("%s deleted user %s", user.alias, person.alias)
        flash(f"{person.name} ({person.alias}) has been deleted.", "success")
    return redirect(url_for("users"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Show the login form (GET), or check the alias and password (POST)"""
    if request.method == "POST":
        # .get(..., "") gives an empty value instead of an error if a field is missing
        alias = request.form.get("alias", "").strip()
        password = request.form.get("password", "")

        user = database.check_login(alias, password)
        if user is None:
            # Same message whether the alias or the password was wrong,
            # so nobody can use this page to find out which aliases exist
            # The password is never written to the log
            app.logger.warning("Failed login attempt for alias: %s", alias)
            flash("Incorrect alias or password.", "error")
            return render_template("login.html", alias=alias)

        # Remember who is logged in
        session.clear()
        session["user_id"] = user.user_id
        app.logger.info("%s logged in", user.alias)
        flash(f"Welcome, {user.name}!", "success")
        return redirect(url_for("home"))

    return render_template("login.html", alias="")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Show the register form (GET), or create a new account (POST)"""
    # Someone who is already logged in does not need to register
    if get_logged_in_user() is not None:
        return redirect(url_for("home"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        alias = request.form.get("alias", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        # Check everything first, and collect all the problems in a list
        # so the user can fix them all at once
        errors = []
        for error in [validation.check_name(name),
                      validation.check_alias(alias),
                      validation.check_password(password, confirm)]:
            if error is not None:
                errors.append(error)
        if database.get_user_by_alias(alias) is not None:
            errors.append("That alias is already registered.")

        if len(errors) > 0:
            for error in errors:
                flash(error, "error")
            # Show the form again, keeping what they typed (except passwords)
            return render_template("register.html", name=name, alias=alias)

        # New accounts are ALWAYS regular. There is no way to choose "admin"
        # here, otherwise anyone could give themselves delete rights.
        database.add_user(name, alias, password, "regular")
        app.logger.info("New user registered: %s", alias)
        flash("Account created! You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", name="", alias="")


@app.route("/logout", methods=["POST"])
def logout():
    """Log the user out (the page asks them to confirm first)"""
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ---------- Error pages ----------
# Instead of Flask's plain error pages, show a friendly message in the
# same style as the rest of the site, with a link back to safety.

@app.errorhandler(404)
def page_not_found(error):
    """The web address does not exist"""
    return render_template("error.html", user=get_logged_in_user(),
                           message="Sorry, that page does not exist."), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """e.g. typing the address of a button-only action, like /logout"""
    message = "That action can only be done using the buttons on the site."
    return render_template("error.html", user=get_logged_in_user(), message=message), 405


@app.errorhandler(500)
def server_error(error):
    """Something unexpected went wrong in our code"""
    # Flask has already saved the full details of the error in app.log,
    # so this just adds a short note saying which page it happened on
    app.logger.error("Showed the error page for %s", request.path)
    return render_template("error.html", user=None,
                           message="Something went wrong. Please try again later."), 500


# This only runs on your own computer (python app.py). The live website
# starts the app with gunicorn instead, which never uses debug mode.
if __name__ == "__main__":
    # 127.0.0.1 means only this computer can open the app
    app.run(host="127.0.0.1", port=5000, debug=True)
