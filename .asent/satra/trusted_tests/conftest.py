"""Fixtures for the SATRA trusted tests of AUTHZ.ADMIN.001 (POST /users/reset_password/<id> is Admin-only).

The tests drive the real application (main.py) through Flask's test client and its real /login
form, so the session, the user loader and the route's own check are all exercised. Nothing in the
application is mocked or changed.

Offline and isolated: the application's database is redirected to an in-memory SQLite database.
`__init__.py` builds the SQLAlchemy engine as soon as it is imported (`SQLAlchemy(app)`), from a
URI fixed in that file, so the only way to choose the database without editing the application is
to set it on the app object at the moment Flask-SQLAlchemy's public `init_app` receives it. The
wrapper below does exactly that, once, before `main` is imported. Every test starts from an empty
schema with three known accounts.
"""
import os
import sys
from pathlib import Path

import flask_sqlalchemy
import pytest
from sqlalchemy.pool import StaticPool

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# No real database, API key or credential is used, whatever the environment says.
for name in ("DB_ENDPOINT", "DB_USERNAME", "DB_PASSWORD", "GITHUB_TOKEN", "GEMINI_API_KEY", "GROQ_API_KEY"):
    os.environ.pop(name, None)

_original_init_app = flask_sqlalchemy.SQLAlchemy.init_app


def _in_memory_init_app(self, app):
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    app.config["SQLALCHEMY_BINDS"] = {}
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"poolclass": StaticPool, "connect_args": {"check_same_thread": False}}
    app.config["TESTING"] = True
    return _original_init_app(self, app)


flask_sqlalchemy.SQLAlchemy.init_app = _in_memory_init_app

ORIGINAL_PASSWORD = "Target-Original-9x!"
ACTOR_PASSWORD = "Actor-Password-7q!"


@pytest.fixture(scope="session")
def application():
    import main  # the real application, with every blueprint registered

    from __init__ import db
    with main.app.app_context():
        assert str(db.engine.url) == "sqlite://", "the trusted tests must never touch a real database"
    return main.app


@pytest.fixture()
def accounts(application):
    """An Admin, a normal User (the attacker) and a normal User whose password is the target."""
    from __init__ import db
    from model import account_types
    from model.user import User

    with application.app_context():
        db.drop_all()
        db.create_all()
        made = {}
        for key, uid, role, password in (("admin", "asent_admin", account_types.admin_role(), ACTOR_PASSWORD),
                                         ("user", "asent_user", "User", ACTOR_PASSWORD),
                                         ("target", "asent_target", "User", ORIGINAL_PASSWORD)):
            account = User(name=key, uid=uid, password=password, role=role)
            assert account.create() is not None
            account.activate()
            made[key] = {"id": account.id, "uid": uid, "token_version": account.token_version}
        # Check the stored roles, not User.is_admin: that is the function under test (the
        # counterfactual target), and a fixture must not decide whether a mutant is caught.
        assert db.session.get(User, made["admin"]["id"]).role == account_types.admin_role()
        assert db.session.get(User, made["user"]["id"]).role != account_types.admin_role()
    yield made
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def login(application):
    """Log a fresh client in through the application's own /login form."""
    def _login(uid, password=ACTOR_PASSWORD):
        client = application.test_client()
        response = client.post("/login", data={"username": uid, "password": password, "next": ""})
        assert response.status_code == 302, f"login of {uid} failed: {response.status_code}"
        return client
    return _login


@pytest.fixture()
def target_state(application):
    """(password still the original?, token_version) of an account, read from the database."""
    from __init__ import db
    from model.user import User

    def _state(user_id):
        with application.app_context():
            db.session.expire_all()
            account = db.session.get(User, user_id)
            return account.is_password(ORIGINAL_PASSWORD), account.token_version
    return _state
