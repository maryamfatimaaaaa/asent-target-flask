"""AUTHZ.ADMIN.001: only an Admin may reset an account's password (POST /users/reset_password/<id>).

main.py::reset_password refuses with 403 unless `current_user.is_admin()`
(model/user.py::User.is_admin). A refused request must leave the account unchanged: its password
is still the original and its token_version (bumped on every password change) has not moved.
"""


def test_normal_user_cannot_reset_another_users_password(accounts, login, target_state):
    client = login(accounts["user"]["uid"])
    response = client.post(f"/users/reset_password/{accounts['target']['id']}")
    assert response.status_code == 403
    assert target_state(accounts["target"]["id"]) == (True, accounts["target"]["token_version"])


def test_normal_user_cannot_reset_own_password_through_admin_route(accounts, login, application):
    from __init__ import db
    from model.user import User

    client = login(accounts["user"]["uid"])
    response = client.post(f"/users/reset_password/{accounts['user']['id']}")
    assert response.status_code == 403
    with application.app_context():
        assert db.session.get(User, accounts["user"]["id"]).token_version == accounts["user"]["token_version"]


def test_unauthenticated_request_is_not_served(accounts, application, target_state):
    response = application.test_client().post(f"/users/reset_password/{accounts['target']['id']}")
    assert response.status_code in (302, 401)  # Flask-Login sends anonymous users to /login
    assert target_state(accounts["target"]["id"]) == (True, accounts["target"]["token_version"])


def test_admin_can_reset_password(accounts, login, application, target_state):
    """Positive control: the route works for an Admin, so the denials above are not vacuous."""
    from __init__ import db
    from model.user import User

    client = login(accounts["admin"]["uid"])
    response = client.post(f"/users/reset_password/{accounts['target']['id']}")
    assert response.status_code == 200
    still_original, token_version = target_state(accounts["target"]["id"])
    assert not still_original and token_version == accounts["target"]["token_version"] + 1
    with application.app_context():
        assert db.session.get(User, accounts["target"]["id"]).is_password(application.config["DEFAULT_PASSWORD"])
