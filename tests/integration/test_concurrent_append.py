import random
import signal
import time
from datetime import datetime, timedelta
from multiprocessing import Pipe, Process

import pytest
from pandas import DataFrame, DatetimeIndex, Series
from pandas.testing import assert_frame_equal

from arctic.arctic import Arctic

pytestmark = pytest.mark.filterwarnings(
    "ignore:This process .* is multi-threaded, use of fork\\(\\) may lead to deadlocks in the child.:DeprecationWarning"
)


class Appender:
    """Append sequential batches and report only successfully verified writes."""

    def __init__(self, mongo_server, library_name, progress, counter_init, runtime):
        self.mongo_server = mongo_server
        self.library_name = library_name
        self.progress = progress
        self.last = counter_init
        self.runtime = runtime

    def run(self):
        """Create the MongoDB client in the child and let failures set its exit code."""
        library = Arctic(self.mongo_server)[self.library_name]
        deadline = time.monotonic() + self.runtime
        while time.monotonic() < deadline:
            end = self.last + random.randint(2, 11)
            df = DataFrame(
                {"v": list(range(self.last, end))},
                index=[
                    datetime(2000, 1, 1) + timedelta(seconds=i)
                    for i in range(self.last, end)
                ],
            )
            df.index.name = "index"
            library.append("symbol", df)
            assert_frame_equal(library.read("symbol").data.iloc[-len(df) :], df)
            self.last = end
            self.progress.send(self.last)


def stop_writer(proc):
    """Reap every child, escalating to kill if termination does not finish."""
    if proc.is_alive():
        proc.terminate()
    proc.join(timeout=10)
    if proc.is_alive():
        proc.kill()
        proc.join(timeout=10)
    assert not proc.is_alive(), "Append child could not be stopped"


def wait_for_write(proc, progress):
    """Require a completed write or report the child's unexpected exit."""
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if progress.poll(0.1):
            try:
                return progress.recv()
            except EOFError:
                break
        if not proc.is_alive():
            break
    proc.join(timeout=0.1)
    pytest.fail(f"Append child did not report a write (exit code {proc.exitcode})")


def test_append_kill(library, mongo_host, library_name):
    df = DataFrame({"v": Series(dtype="int64")}, index=DatetimeIndex([]))
    df.index.name = "index"
    library.write("symbol", df)

    def run_append(begin, runtime):
        reader, writer = Pipe(duplex=False)
        appender = Appender(mongo_host, library_name, writer, begin, runtime)
        proc = Process(target=appender.run)
        proc.start()
        writer.close()
        return proc, reader

    def check_written(minimum):
        data = library.read("symbol").data
        assert len(data) >= minimum > 0
        assert data["v"].tolist() == list(range(len(data)))
        assert data.index.tolist() == [
            datetime(2000, 1, 1) + timedelta(seconds=i) for i in range(len(data))
        ]
        assert data.index.name == "index"
        return data

    # Establish that an uninterrupted child reaches append and exits successfully.
    proc, progress = run_append(0, 0.2)
    try:
        completed = wait_for_write(proc, progress)
        proc.join(timeout=15)
        assert not proc.is_alive(), "Initial append child timed out"
        assert proc.exitcode == 0, f"Initial append child failed: {proc.exitcode}"
        previous = check_written(completed)
    finally:
        stop_writer(proc)
        progress.close()

    for _ in range(100):
        proc, progress = run_append(len(previous), 60)
        try:
            completed = wait_for_write(proc, progress)
            time.sleep(random.uniform(0, 0.01))
            assert proc.is_alive(), f"Append child exited unexpectedly: {proc.exitcode}"
            proc.terminate()
            proc.join(timeout=10)
            assert not proc.is_alive(), "Interrupted append child timed out"
            assert (
                proc.exitcode == -signal.SIGTERM
            ), f"Expected forced termination, got exit code {proc.exitcode}"
            current = check_written(completed)
            assert_frame_equal(current.iloc[: len(previous)], previous)
            previous = current
        finally:
            stop_writer(proc)
            progress.close()
