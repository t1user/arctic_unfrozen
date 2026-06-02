from mock import Mock, call, patch

from arctic.scripts.utils import get_db_connection


def test_get_db_connection_prefers_admin_credentials():
    admin_creds = Mock()
    user_creds = Mock()
    with (
        patch(
            "arctic.scripts.utils.get_auth",
            autospec=True,
            side_effect=[admin_creds, user_creds],
        ) as get_auth,
        patch("arctic.scripts.utils.create_client", autospec=True) as create_client,
    ):
        assert (
            get_db_connection("hostname", "arctic_user") is create_client.return_value
        )

    assert get_auth.call_args_list == [
        call("hostname", "admin", "admin"),
        call("hostname", "arctic", "arctic_user"),
    ]
    create_client.assert_called_once_with("hostname", admin_creds)


def test_get_db_connection_uses_database_credentials():
    user_creds = Mock()
    with (
        patch(
            "arctic.scripts.utils.get_auth",
            autospec=True,
            side_effect=[None, user_creds],
        ),
        patch("arctic.scripts.utils.create_client", autospec=True) as create_client,
    ):
        get_db_connection("hostname", "arctic_user")

    create_client.assert_called_once_with("hostname", user_creds)


def test_get_db_connection_supports_unauthenticated_mongo():
    with (
        patch("arctic.scripts.utils.get_auth", autospec=True, side_effect=[None, None]),
        patch("arctic.scripts.utils.create_client", autospec=True) as create_client,
    ):
        get_db_connection("hostname", "arctic_user")

    create_client.assert_called_once_with("hostname", None)
