import logging
from typing import Any, cast

import numpy as np
import pymongo
from pandas import DataFrame
from pandas.testing import assert_frame_equal

from ._config import FW_POINTERS_CONFIG_KEY, FwPointersCfg

logger = logging.getLogger(__name__)

NP_OBJECT_DTYPE = np.dtype('O')

def get_fwptr_config(version: dict[str, Any]) -> FwPointersCfg:
    return FwPointersCfg[version.get(FW_POINTERS_CONFIG_KEY, FwPointersCfg.DISABLED.name)]


def indent(s: str, num_spaces: int) -> str:
    lines = s.split('\n')
    lines = [(num_spaces * ' ') + line for line in lines]
    return '\n'.join(lines)


def are_equals(o1: Any, o2: Any, **kwargs: Any) -> bool:
    try:
        if isinstance(o1, DataFrame):
            assert_frame_equal(o1, o2, **kwargs)
            return True
        return cast(bool, o1 == o2)
    except Exception:
        return False


def enable_sharding(arctic: Any, library_name: str, hashed: bool = True, key: str = 'symbol') -> None:
    """
    Enable sharding on a library

    Parameters:
    -----------
    arctic: `arctic.Arctic` Arctic class

    library_name: `str` library name

    hashed: `bool` if True, use hashed sharding, if False, use range sharding
            See https://docs.mongodb.com/manual/core/hashed-sharding/,
            as well as https://docs.mongodb.com/manual/core/ranged-sharding/ for details.

    key: `str` key to be used for sharding. Defaults to 'symbol', applicable to
         all of Arctic's built-in stores except for BSONStore, which typically uses '_id'.
         See https://docs.mongodb.com/manual/core/sharding-shard-key/ for details.
    """
    c = arctic._conn
    lib = arctic[library_name]._arctic_lib
    dbname = lib._db.name
    library_name = lib.get_top_level_collection().name
    try:
        c.admin.command('enablesharding', dbname)
    except pymongo.errors.OperationFailure as e:
        if 'already enabled' not in str(e):
            raise
    if not hashed:
        logger.info("Range sharding '" + key + "' on: " + dbname + '.' + library_name)
        c.admin.command('shardCollection', dbname + '.' + library_name, key={key: 1})
    else:
        logger.info("Hash sharding '" + key + "' on: " + dbname + '.' + library_name)
        c.admin.command('shardCollection', dbname + '.' + library_name, key={key: 'hashed'})


def mongo_count(collection: Any, filter: dict[str, Any] | None = None, **kwargs: Any) -> int:
    """
    use with care as filters on un-indexed fields will generate COLLSCAN.
    """
    filter = {} if filter is None else filter
    if filter == {}:
        # Fast: uses collection metadata.
        return cast(int, collection.estimated_document_count(**kwargs))
    # Transactions supported, but slow for non-indexed filters.
    return cast(int, collection.count_documents(filter=filter, **kwargs))
