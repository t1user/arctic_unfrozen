import pytest
from mock import patch

from arctic.scripts import arctic_init_library as mil
from arctic.scripts.arctic_init_library import Arctic as ar
from ...util import run_as_main


def test_init_library():
    with patch("arctic.scripts.arctic_init_library.logger", autospec=True) as logger, \
         patch("arctic.scripts.arctic_init_library.Arctic", spec=ar) as arctic, \
         patch("arctic.scripts.arctic_init_library.get_db_connection", autospec=True) as get_db_connection:
        run_as_main(mil.main, "--host", "hostname", "--library", "arctic_user.library", "--type", "VersionStore")

    get_db_connection.assert_called_once_with("hostname", "arctic_user")
    arctic.assert_called_once_with(get_db_connection.return_value)
    arctic.return_value.initialize_library.assert_called_once_with("arctic_user.library", "VersionStore", hashed=False)
    assert logger.warn.call_count == 0


def test_init_library_hashed():
    with patch("arctic.scripts.arctic_init_library.Arctic", spec=ar) as arctic, \
         patch("arctic.scripts.arctic_init_library.get_db_connection", autospec=True) as get_db_connection:
        run_as_main(
            mil.main,
            "--host",
            "hostname",
            "--library",
            "arctic_user.library",
            "--type",
            "VersionStore",
            "--hashed",
        )

    arctic.assert_called_once_with(get_db_connection.return_value)
    arctic.return_value.initialize_library.assert_called_once_with("arctic_user.library", "VersionStore", hashed=True)


def test_bad_library_name():
    with pytest.raises(Exception):
        with patch("argparse.ArgumentParser.error", side_effect=Exception) as error:
            run_as_main(mil.main, "--library", "arctic_jblackburn")
    error.assert_called_once_with("Must specify the full path of the library e.g. user.library!")

    with pytest.raises(Exception):
        with patch("argparse.ArgumentParser.error", side_effect=Exception) as error:
            run_as_main(mil.main)
    error.assert_called_once_with("Must specify the full path of the library e.g. user.library!")
