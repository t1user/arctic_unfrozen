import pickle
from datetime import date, datetime as dt, timedelta, timezone

import pandas as pd
import pytest

from arctic._compression import compress
from arctic.date import DateRange
from arctic.store._version_store_utils import checksum

import bson
import numpy as np
from mock import patch

from arctic._util import mongo_count
from arctic.arctic import Arctic


def _utcnow():
    return dt.now(timezone.utc).replace(tzinfo=None)


def test_save_read_bson(library):
    blob = {"foo": dt(2015, 1, 1), "bar": ["a", "b", ["x", "y", "z"]]}
    library.write("BLOB", blob)
    saved_blob = library.read("BLOB").data
    assert blob == saved_blob


"""
Run test at your own discretion. Takes > 60 secs
def test_save_read_MASSIVE(library):
    import pandas as pd
    df = pd.DataFrame(data={'data': [1] * 150000000})
    data = (df, df)
    library.write('BLOB', data)
    saved_blob = library.read('BLOB').data
    assert(saved_blob[0].equals(df))
    assert(saved_blob[1].equals(df))
"""


def test_save_read_big_encodable(library):
    blob = {"foo": "a" * 1024 * 1024 * 20}
    library.write("BLOB", blob)
    saved_blob = library.read("BLOB").data
    assert blob == saved_blob


def test_save_read_bson_object(library):
    blob = {"foo": dt(2015, 1, 1), "object": Arctic}
    library.write("BLOB", blob)
    saved_blob = library.read("BLOB").data
    assert blob == saved_blob


def test_get_info_bson_object(library):
    blob = {"foo": dt(2015, 1, 1), "object": Arctic}
    library.write("BLOB", blob)
    assert library.get_info("BLOB")["handler"] == "PickleStore"


def test_bson_large_object(library):
    blob = {
        "foo": dt(2015, 1, 1),
        "object": Arctic,
        "large_thing": np.random.rand(int(2.1 * 1024 * 1024)).tobytes(),
    }
    assert len(blob["large_thing"]) > 16 * 1024 * 1024
    library.write("BLOB", blob)
    saved_blob = library.read("BLOB").data
    assert blob == saved_blob


def test_bson_leak_objects_delete(library):
    blob = {"foo": dt(2015, 1, 1), "object": Arctic}
    library.write("BLOB", blob)
    assert mongo_count(library._collection) == 1
    assert mongo_count(library._collection.versions) == 1
    library.delete("BLOB")
    assert mongo_count(library._collection) == 0
    assert mongo_count(library._collection.versions) == 0


def test_bson_leak_objects_prune_previous(library):
    blob = {"foo": dt(2015, 1, 1), "object": Arctic}

    yesterday = _utcnow() - timedelta(days=1, seconds=1)
    _id = bson.ObjectId.from_datetime(yesterday)
    with patch("bson.ObjectId", return_value=_id):
        library.write("BLOB", blob)
    assert mongo_count(library._collection) == 1
    assert mongo_count(library._collection.versions) == 1

    _id = bson.ObjectId.from_datetime(_utcnow() - timedelta(minutes=130))
    with patch("bson.ObjectId", return_value=_id):
        library.write("BLOB", {}, prune_previous_version=False)
    assert mongo_count(library._collection) == 1
    assert mongo_count(library._collection.versions) == 2

    # This write should pruned the oldest version in the chunk collection
    library.write("BLOB", {})
    assert mongo_count(library._collection) == 0
    assert mongo_count(library._collection.versions) == 2


def test_prune_previous_doesnt_kill_other_objects(library):
    blob = {"foo": dt(2015, 1, 1), "object": Arctic}

    yesterday = _utcnow() - timedelta(days=1, seconds=1)
    _id = bson.ObjectId.from_datetime(yesterday)
    with patch("bson.ObjectId", return_value=_id):
        library.write("BLOB", blob, prune_previous_version=False)
    assert mongo_count(library._collection) == 1
    assert mongo_count(library._collection.versions) == 1

    _id = bson.ObjectId.from_datetime(_utcnow() - timedelta(hours=10))
    with patch("bson.ObjectId", return_value=_id):
        library.write("BLOB", blob, prune_previous_version=False)
    assert mongo_count(library._collection) == 1
    assert mongo_count(library._collection.versions) == 2

    # This write should pruned the oldest version in the chunk collection
    library.write("BLOB", {})
    assert mongo_count(library._collection) == 1
    assert mongo_count(library._collection.versions) == 2

    library._delete_version("BLOB", 2)
    assert mongo_count(library._collection) == 0
    assert mongo_count(library._collection.versions) == 1


def test_write_metadata(library):
    blob = {"foo": dt(2015, 1, 1), "object": Arctic}
    library.write(symbol="symX", data=blob, metadata={"key1": "value1"})
    library.write_metadata(symbol="symX", metadata={"key2": "value2"})
    v = library.read("symX")
    assert v.data == blob
    assert v.metadata == {"key2": "value2"}


@pytest.mark.parametrize(
    "layout", ["current", "inline", "__chunked__", "__chunked__V2"]
)
@pytest.mark.parametrize(
    "bounds,positions",
    [
        (DateRange(date(2020, 1, 2), date(2020, 1, 3)), [1, 2]),
        (DateRange(dt(2020, 1, 2), dt(2020, 1, 3)), [1, 2]),
        (DateRange(dt(2020, 1, 2, 12), dt(2020, 1, 3, 12)), [2]),
        (DateRange(start=date(2020, 1, 2)), [1, 2]),
        (DateRange(end=date(2020, 1, 2)), [0, 1]),
        (DateRange(date(2020, 1, 2), date(2020, 1, 2)), [1]),
        (DateRange(start=date(2021, 1, 1)), []),
        (DateRange(end=date(2019, 1, 1)), []),
    ],
)
def test_daily_date_range_legacy_storage(library, layout, bounds, positions):
    """Read legacy document layouts on the disposable MongoDB fixture only."""
    frame = pd.DataFrame(
        {"v": [1, 2, 3]},
        index=pd.Index(
            [date(2020, 1, day) for day in (1, 2, 3)], dtype=object, name="day"
        ),
    )
    frame.attrs = {"source": "daily"}
    metadata = {"frequency": "daily"}
    library.write("daily", frame, metadata=metadata)
    assert library.get_info("daily")["handler"] == "PickleStore"
    if layout != "current":
        # Construct historical storage envelopes directly, rather than calling
        # the current serializer/writer to generate the fixture under test.
        versions = library._collection.versions
        version = versions.find_one({"symbol": "daily"})
        parent = version.get("base_version_id", version["_id"])
        library._collection.delete_many({"symbol": "daily"})
        payload = pickle.dumps(frame, protocol=2)
        if layout == "inline":
            blob = bson.Binary(compress(payload))
        else:
            blob = layout
            if layout == "__chunked__":
                payload = compress(payload)
                chunks = [payload[:17], payload[17:]]
            else:
                chunks = [compress(payload[:17]), compress(payload[17:])]
            library._collection.insert_many(
                [
                    {
                        "symbol": "daily",
                        "parent": [parent],
                        "segment": i,
                        "data": bson.Binary(chunk),
                        "sha": checksum(
                            "daily", {"segment": i, "data": bson.Binary(chunk)}
                        ),
                    }
                    for i, chunk in enumerate(chunks)
                ]
            )
        versions.update_one({"_id": version["_id"]}, {"$set": {"blob": blob}})
    before = list(library._collection.versions.find({"symbol": "daily"}))
    segments = list(library._collection.find({"symbol": "daily"}))
    result = library.read("daily", date_range=bounds)
    pd.testing.assert_frame_equal(result.data, frame.iloc[positions])
    assert result.data.attrs == frame.attrs
    assert result.metadata == metadata
    pd.testing.assert_frame_equal(library.read("daily").data, frame)
    assert list(library._collection.versions.find({"symbol": "daily"})) == before
    assert list(library._collection.find({"symbol": "daily"})) == segments
