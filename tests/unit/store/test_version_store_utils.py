import binascii

import numpy as np
import pytest
from mock import sentinel

from arctic.store._version_store_utils import (
    _split_arrs,
    checksum,
    fast_is_corrupted,
    is_corrupted,
    is_safe_to_append,
    version_base_or_id,
)


class _FakeCollection:
    def __init__(self):
        self.count_filters = []

    def count_documents(self, filter, **kwargs):
        self.count_filters.append(filter)
        return 0

    def count(self, filter, **kwargs):
        self.count_filters.append(filter)
        return 0

    def find_one(self, *args, **kwargs):
        return None


class _FakeVersions:
    def __init__(self, version):
        self.version = version

    def find_one(self, *args, **kwargs):
        return self.version


class _FakeVersionStore:
    def __init__(self, collection, versions):
        self._collection = collection
        self._versions = versions

    def read(self, symbol, as_of=None):
        return None


def test_split_arrs_empty():
    split = _split_arrs(np.empty(0), [])
    assert np.all(split == np.empty(0, dtype=object))


def test_split_arrs():
    to_split = np.ones(10)
    split = _split_arrs(to_split, [3])
    assert len(split) == 2
    assert np.all(split[0] == np.ones(3))
    assert np.all(split[1] == np.ones(7))


def test_checksum():
    digest = checksum("test_my_market_data_$ymB0l", {})
    expected = b"""4OZ*3DO'$>XV['VW1MT4I^+7-3H,"""
    assert binascii.b2a_uu(digest).strip() == expected


def test_checksum_handles_p3strs_and_binary():
    digest = checksum(
        "test_my_market_data_$ymB0l", {"key1": "unicode", "key2": b"binary_data"}
    )
    expected = b"4O11 ;<A@C1.0W(JRB1.?D[ZEN!8"
    assert binascii.b2a_uu(digest).strip() == expected


def test_version_base_or_id():
    with pytest.raises(KeyError):
        version_base_or_id({})
    assert version_base_or_id({"_id": sentinel._id}) == sentinel._id
    assert (
        version_base_or_id(
            {"_id": sentinel._id, "base_version_id": sentinel.base_version_id}
        )
        == sentinel.base_version_id
    )


def test_is_safe_to_append_resolves_integer_version():
    version = {"_id": sentinel.version_id, "version": 7, "segment_count": 0, "up_to": 0}
    collection = _FakeCollection()
    store = _FakeVersionStore(collection, _FakeVersions(version))

    assert is_safe_to_append(store, "sym", 7)
    assert collection.count_filters == [
        {"symbol": "sym", "parent": sentinel.version_id}
    ]


def test_corruption_helpers_handle_missing_integer_version():
    store = _FakeVersionStore(_FakeCollection(), _FakeVersions(None))

    assert is_safe_to_append(store, "sym", 7)
    assert not fast_is_corrupted(store, "sym", 7)
    assert is_corrupted(store, "sym", 7)
