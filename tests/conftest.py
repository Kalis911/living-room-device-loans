# conftest.py
# Set-up shared by all the test files. pytest reads this file automatically.
#
# A "fixture" is something a test needs before it can run. A test asks for a
# fixture by using its name as a parameter, e.g.  def test_something(client):

import pytest

import app as app_module
import database

# The password every sample user has during the tests
TEST_PASSWORD = "Password123"


@pytest.fixture(autouse=True)
def test_database(tmp_path):
    """
    Give every test its own brand new database with the 10 sample users and
    devices. autouse=True means every test uses this without asking for it.
    tmp_path is a temporary folder that pytest makes (and deletes) for us,
    so the real devices.db is never touched.
    """
    database.DATABASE_FILE = str(tmp_path / "test.db")
    database.create_database()
    database.add_sample_data(TEST_PASSWORD)

    # Stop the tests writing their pretend logins and errors into app.log
    app_module.app.logger.removeHandler(app_module.log_file)


@pytest.fixture
def client():
    """A pretend web browser for visiting pages of the app"""
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def log_in(client, alias):
    """Helper: log in through the real login page"""
    return client.post("/login", data={"alias": alias, "password": TEST_PASSWORD},
                       follow_redirects=True)
