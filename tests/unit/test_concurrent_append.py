"""Parent-side regressions for the crash-during-append workload."""

from multiprocessing import get_context
from unittest.mock import Mock

import pytest

from tests.integration.test_concurrent_append import stop_writer, wait_for_write


def fail_writer():
    """Represent an unintended child failure before the first completed append."""
    raise RuntimeError("Append failed before writing")


def test_unexpected_writer_failure_is_reported():
    context = get_context("spawn")
    reader, writer = context.Pipe(duplex=False)
    proc = context.Process(target=fail_writer)
    proc.start()
    writer.close()
    try:
        proc.join(timeout=10)
        assert proc.exitcode == 1
        with pytest.raises(pytest.fail.Exception, match="exit code 1"):
            wait_for_write(proc, reader)
    finally:
        stop_writer(proc)
        reader.close()


def test_stop_writer_escalates_and_joins():
    proc = Mock()
    proc.is_alive.side_effect = [True, True, False]
    stop_writer(proc)
    proc.terminate.assert_called_once_with()
    proc.kill.assert_called_once_with()
    assert proc.join.call_count == 2
    assert all(call.kwargs == {"timeout": 10} for call in proc.join.call_args_list)
