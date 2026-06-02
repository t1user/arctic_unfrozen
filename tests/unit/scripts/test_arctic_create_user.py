from mock import ANY, call, patch

from arctic.scripts.arctic_create_user import main
from ...util import run_as_main


def test_main_minimal():
    with (
        patch("arctic.scripts.arctic_create_user.logger", autospec=True) as logger,
        patch("arctic.scripts.arctic_create_user.get_auth", autospec=True) as get_auth,
        patch(
            "arctic.scripts.arctic_create_user.create_client", autospec=True
        ) as create_client,
    ):
        run_as_main(main, "--host", "some_host", "--password", "asdf", "user")

    get_auth.assert_called_once_with("some_host", "admin", "admin")
    create_client.assert_called_once_with("some_host", get_auth.return_value)
    database = create_client.return_value.__getitem__.return_value
    assert database.command.call_args_list == [
        call(
            "createUser",
            "user",
            pwd="asdf",
            roles=[{"role": "readWrite", "db": "arctic_user"}],
        )
    ]
    assert logger.info.call_args_list == [
        call("Granted: user [WRITE] to arctic_user"),
        call("User creds: arctic_user/user/asdf"),
    ]


def test_main_with_db_read_only():
    with patch(
        "arctic.scripts.arctic_create_user.create_client", autospec=True
    ) as create_client:
        run_as_main(main, "--host", "some_host", "--db", "some_db", "jblackburn")

    database = create_client.return_value.__getitem__.return_value
    assert database.command.call_args_list == [
        call(
            "createUser",
            "jblackburn",
            pwd=ANY,
            roles=[{"role": "read", "db": "some_db"}],
        )
    ]


def test_main_with_db_write():
    with patch(
        "arctic.scripts.arctic_create_user.create_client", autospec=True
    ) as create_client:
        run_as_main(
            main, "--host", "some_host", "--db", "some_db", "--write", "jblackburn"
        )

    database = create_client.return_value.__getitem__.return_value
    assert database.command.call_args_list == [
        call(
            "createUser",
            "jblackburn",
            pwd=ANY,
            roles=[{"role": "readWrite", "db": "some_db"}],
        )
    ]
