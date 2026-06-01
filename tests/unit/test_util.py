from mock import MagicMock, ANY, patch
import pandas as pd

from arctic._util import are_equals, enable_sharding, mongo_count
from arctic.arctic import Arctic
import arctic._util


def test_are_equals_not_df():
    assert(are_equals(1.0, 2.0) is False)
    assert(are_equals([1, 2, 3], [1, 2, 3]))
    assert(are_equals("Hello", "World") is False)


def test_are_equals_dataframe_kwargs():
    left = pd.DataFrame({"col": [1]})
    right = pd.DataFrame({"col": [1.0]})

    assert are_equals(left, right) is False
    assert are_equals(left, right, check_dtype=False)


def test_enable_sharding_hashed():
    m = MagicMock(Arctic, autospec=True)
    enable_sharding(m, "test", hashed=True)
    m._conn.admin.command.assert_called_with('shardCollection', ANY, key={'symbol': 'hashed'})


def test_mongo_count():
    coll = MagicMock()
    mongo_count(coll, filter="_id:1")
    mongo_count(coll, filter={})
    mongo_count(coll)
    assert coll.estimated_document_count.call_count == 2
    assert coll.count_documents.call_count == 1
