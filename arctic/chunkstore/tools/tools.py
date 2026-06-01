from itertools import groupby
from collections.abc import Iterable
from typing import Any, Protocol

import pymongo

from arctic.chunkstore.chunkstore import SYMBOL, SEGMENT, START


class _ChunkCollection(Protocol):
    def find(self, *args: Any, **kwargs: Any) -> Iterable[dict[str, Any]]:
        ...

    def delete_many(self, *args: Any, **kwargs: Any) -> Any:
        ...

    def insert_many(self, documents: list[dict[str, Any]]) -> Any:
        ...


class _ChunkLibrary(Protocol):
    _collection: _ChunkCollection

    def list_symbols(self) -> list[str]:
        ...


def segment_id_repair(library: _ChunkLibrary, symbol: str | list[str] | None = None) -> list[str]:
    """
    Ensure that symbol(s) have contiguous segment ids

    Parameters
    ----------
    library: arctic library
    symbol: None, str, list of str
        None: all symbols
        str: single symbol
        list: list of symbols

    Returns
    -------
    list of str - Symbols 'fixed'
    """
    ret: list[str] = []

    if symbol is None:
        symbols = library.list_symbols()
    elif not isinstance(symbol, list):
        symbols = [symbol]
    else:
        symbols = symbol

    by_segment = [(START, pymongo.ASCENDING),
                  (SEGMENT, pymongo.ASCENDING)]

    for sym in symbols:
        cursor = library._collection.find({SYMBOL: sym}, sort=by_segment)
        # group by chunk
        for _, segment_iter in groupby(cursor, key=lambda x: (x[START], x[SYMBOL])):
            segments = list(segment_iter)
            # if the start segment is not 0, we need to fix this symbol
            if segments[0][SEGMENT] == -1:
                # since the segment is part of the index, we have to clean up first
                library._collection.delete_many({SYMBOL: sym, START: segments[0][START]})
                # map each segment in the interval to the correct segment
                for index, seg in enumerate(segments):
                    seg[SEGMENT] = index
                library._collection.insert_many(segments)
                ret.append(sym)

    return ret
