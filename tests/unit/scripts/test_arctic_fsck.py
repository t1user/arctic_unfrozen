from mock import call, patch, sentinel

from arctic.scripts.arctic_fsck import main
from ...util import run_as_main


def test_main():
    with patch("arctic.scripts.arctic_fsck.Arctic") as arctic:
        run_as_main(main, "--host", f"{sentinel.host}:{sentinel.port}", "-v", "--library", "sentinel.library", "lib2", "-f")

    arctic.assert_called_once_with("sentinel.host:sentinel.port")
    assert arctic.return_value.__getitem__.return_value._fsck.call_args_list == [call(False), call(False)]


def test_main_dry_run():
    with patch("arctic.scripts.arctic_fsck.Arctic") as arctic:
        run_as_main(main, "--host", f"{sentinel.host}:{sentinel.port}", "-v", "--library", "sentinel.library", "sentinel.lib2")

    arctic.assert_called_once_with("sentinel.host:sentinel.port")
    assert arctic.return_value.__getitem__.return_value._fsck.call_args_list == [call(True), call(True)]
