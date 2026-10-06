"""Read-only filtering regressions for the legacy pickle storage layouts."""

import pickle
from datetime import date, datetime, timezone

import pandas as pd
import pytest
from bson.binary import Binary
from mock import Mock

from arctic._compression import compress
from arctic.date import DateRange, OPEN_OPEN, OPEN_CLOSED, CLOSED_OPEN
from arctic.store._pickle_store import PickleStore


@pytest.fixture
def daily_data():
    """Include unordered observations and duplicates to detect index coercion."""
    frame = pd.DataFrame(
        {"v": [30, 10, 20, 21]},
        index=pd.Index(
            [date(2020, 1, 3), date(2020, 1, 1), date(2020, 1, 2), date(2020, 1, 2)],
            dtype=object,
            name="day",
        ),
    )
    frame.attrs = {"source": "daily"}
    return frame


@pytest.fixture(params=["inline", "__chunked__", "__chunked__V2", "data"])
def legacy_reader(request):
    """Build old inline, V1 and V2 documents without using today's writer."""

    def read(item, date_range):
        library = Mock()
        version = {"_id": "legacy-version"}
        payload = pickle.dumps(item, protocol=2)
        if request.param == "data":
            version["data"] = item
        elif request.param == "inline":
            version["blob"] = Binary(compress(payload))
        else:
            version["blob"] = request.param
            if request.param == "__chunked__":
                payload = compress(payload)
                chunks = [payload[:17], payload[17:]]
            else:
                chunks = [compress(payload[:17]), compress(payload[17:])]
            library.get_top_level_collection.return_value.find.return_value = [
                {"segment": i, "data": Binary(chunk)}
                for i, chunk in reversed(list(enumerate(chunks)))
            ]
        return PickleStore().read(library, version, "daily", date_range=date_range)

    return read


@pytest.mark.parametrize("as_series", [False, True])
@pytest.mark.parametrize(
    "bounds,positions",
    [
        (DateRange(date(2020, 1, 2), date(2020, 1, 3)), [0, 2, 3]),
        (DateRange(datetime(2020, 1, 2), datetime(2020, 1, 3)), [0, 2, 3]),
        (DateRange(datetime(2020, 1, 2, 12), datetime(2020, 1, 3, 12)), [0]),
        (DateRange(datetime(2020, 1, 2, 12), datetime(2020, 1, 2, 23)), []),
        (DateRange(date(2020, 1, 2), date(2020, 1, 2)), [2, 3]),
        (DateRange(start=date(2020, 1, 2)), [0, 2, 3]),
        (DateRange(end=date(2020, 1, 2)), [1, 2, 3]),
        (DateRange(), [0, 1, 2, 3]),
        (DateRange(end=date(2019, 1, 1)), []),
        (DateRange(start=date(2021, 1, 1)), []),
        (DateRange(date(2020, 1, 1), date(2020, 1, 3), OPEN_OPEN), [2, 3]),
        (DateRange(date(2020, 1, 1), date(2020, 1, 3), OPEN_CLOSED), [0, 2, 3]),
        (DateRange(date(2020, 1, 1), date(2020, 1, 3), CLOSED_OPEN), [1, 2, 3]),
    ],
)
def test_legacy_daily_range(legacy_reader, daily_data, bounds, positions, as_series):
    item = daily_data["v"] if as_series else daily_data
    result = legacy_reader(item, bounds)
    assert_equal = (
        pd.testing.assert_series_equal if as_series else pd.testing.assert_frame_equal
    )
    assert_equal(result, item.iloc[positions])
    assert result.attrs == item.attrs
    assert all(type(value) is date for value in result.index)


def test_empty_date_index(legacy_reader, daily_data):
    item = daily_data.iloc[:0]
    pd.testing.assert_frame_equal(
        legacy_reader(item, DateRange(start=date(2020, 1, 2))), item
    )


@pytest.mark.parametrize(
    "index",
    [
        ["2020-01-01", "2020-01-02"],
        [1, 2],
        [date(2020, 1, 1), "2020-01-02"],
    ],
)
def test_arbitrary_objects_are_not_dates(legacy_reader, index):
    item = pd.DataFrame({"v": [1, 2]}, index=pd.Index(index, dtype=object))
    pd.testing.assert_frame_equal(
        legacy_reader(item, DateRange(start=date(2020, 1, 2))), item
    )


def test_object_datetime_index(legacy_reader):
    item = pd.DataFrame(
        {"v": [1, 2, 3]},
        index=pd.Index(
            [datetime(2020, 1, 1), datetime(2020, 1, 1, 12), date(2020, 1, 2)],
            dtype=object,
            name="observed",
        ),
    )
    result = legacy_reader(
        item, DateRange(datetime(2020, 1, 1, 12), datetime(2020, 1, 2))
    )
    pd.testing.assert_frame_equal(result, item.iloc[1:])


@pytest.mark.parametrize("side", ["start", "end"])
def test_aware_bounds_rejected(legacy_reader, daily_data, side):
    bounds = DateRange(**{side: datetime(2020, 1, 2, tzinfo=timezone.utc)})
    with pytest.raises(ValueError, match="DateRange with timezone not supported"):
        legacy_reader(daily_data, bounds)
